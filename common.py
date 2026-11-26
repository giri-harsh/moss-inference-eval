"""Shared plumbing: credentials, redacted JSONL logging, spend guard, timed streaming chat calls."""

import asyncio
import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).parent
DATA, LOGS, RESULTS = ROOT / "data", ROOT / "logs", ROOT / "results"
MOSS_BASE = "https://inference.moss.dev/v1"
INDEX = os.environ.get("MOSS_INDEX", "akgec-helpdesk")
HARD_STOP = float(os.environ.get("EVAL_BUDGET_USD", "8.00"))  # of $10 credits; $2 stays in reserve
PHASE_CAPS = {"core": 3.00, "tasks": 3.00, "combos": 2.00}
LEDGER = LOGS / "spend_ledger.jsonl"


def secret(name):
    """Process environment first, then the dotenv file named by EVAL_ENV_FILE."""
    if os.environ.get(name):
        return os.environ[name]
    path = os.environ.get("EVAL_ENV_FILE")
    if path and Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
            key, sep, value = line.strip().removeprefix("export ").partition("=")
            if sep and key.strip() == name:
                return value.strip().strip("\"'")
    return ""


SECRETS = {name: secret(name) for name in ("MOSS_PROJECT_ID", "MOSS_PROJECT_KEY", "GROQ_API_KEY")}

# USD per token. Neither API returns a cost, so spend is computed from usage at published prices.
PROVIDERS = {
    "groq": {"base": "https://api.groq.com/openai/v1", "model": "openai/gpt-oss-120b",
             "in": 0.15e-6, "cached": 0.075e-6, "out": 0.60e-6, "retrieval": 0.0},
    "moss": {"base": MOSS_BASE, "model": "moss/fastlane-1",
             "in": 0.25e-6, "cached": 0.03e-6, "out": 1.75e-6, "retrieval": 0.50e-3},
}


class BudgetExceeded(RuntimeError):
    pass


def require(*names):
    missing = [n for n in names if not SECRETS.get(n)]
    if missing:
        sys.exit(f"Missing credentials: {', '.join(missing)} (set them, or point EVAL_ENV_FILE at a dotenv file).")


def moss_auth():
    return f"Bearer {SECRETS['MOSS_PROJECT_ID']}:{SECRETS['MOSS_PROJECT_KEY']}"


def auth_header(provider):
    return moss_auth() if provider == "moss" else f"Bearer {SECRETS['GROQ_API_KEY']}"


def redact(text):
    """Strip credentials, account identifiers and signed URL parameters from anything written to disk."""
    for name, value in SECRETS.items():
        if value:
            text = text.replace(value, f"<{name}>")
    text = re.sub(r"\b(moss|gsk)_[A-Za-z0-9_\-]{16,}", r"<\1_TOKEN>", text)
    text = re.sub(r"Bearer\s+[^\s\"'\\]+", "Bearer <REDACTED>", text)
    text = re.sub(r"\borg_[A-Za-z0-9]{12,}", "org_<ID>", text)
    text = re.sub(r"\b[6-9]\d{9}\b", "<PHONE>", text)
    text = re.sub(r"[\w.+-]+@[\w-]+(\.\w+)+", "<EMAIL>", text)
    text = re.sub(r"(?i)(project )[0-9a-f]{6,}[0-9a-f-]*", r"\1<ID>", text)
    return re.sub(r"(https?://[^\s\"'\\?]+)\?[^\s\"'\\]*(?:sig|token|key|X-Amz)[^\s\"'\\]*", r"\1?<SIGNED>", text, flags=re.I)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Log:
    """One JSONL file per test, truncated at the start of each run."""

    def __init__(self, name):
        LOGS.mkdir(exist_ok=True)
        self.path = LOGS / f"{name}.jsonl"
        self.path.write_text("", encoding="utf-8")

    def write(self, record):
        with self.path.open("a", encoding="utf-8") as f:
            f.write(redact(json.dumps({"ts": now(), **record}, ensure_ascii=False, default=str)) + "\n")


def read_jsonl(path):
    if not Path(path).exists():
        return []
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(name, rows):
    RESULTS.mkdir(exist_ok=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (RESULTS / name).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        writer.writerows({k: redact(v) if isinstance(v, str) else v for k, v in r.items()} for r in rows)


def spent(phase=None):
    return sum(r["usd"] for r in read_jsonl(LEDGER) if phase in (None, r["phase"]))


def guard(worst_case_usd, phase):
    """Refuse to start anything that could push spend past the hard stop or the phase allocation."""
    for label, used, cap in (("total", spent(), HARD_STOP), (phase, spent(phase), PHASE_CAPS[phase])):
        if used + worst_case_usd > cap:
            raise BudgetExceeded(f"{label}: spent ${used:.4f} + worst case ${worst_case_usd:.4f} > ${cap:.2f}")


def charge(what, usd, phase, provider="moss"):
    LOGS.mkdir(exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now(), "phase": phase, "provider": provider, "what": what, "usd": usd}) + "\n")


def report_spend(test, before):
    """Append the running total after a test to results/spend_log.csv and print it."""
    total = spent()
    row = {"ts": now(), "test": test, "test_usd": round(total - before, 6), "running_total_usd": round(total, 6),
           "moss_total_usd": round(sum(r["usd"] for r in read_jsonl(LEDGER) if r["provider"] == "moss"), 6)}
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / "spend_log.csv"
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, list(row))
        if new:
            writer.writeheader()
        writer.writerow(row)
    print(f"[spend] {test}: ${row['test_usd']:.4f}, running total ${total:.4f} (Moss ${row['moss_total_usd']:.4f})")


def token_cost(provider, input_tokens, cached_tokens, output_tokens, retrievals=0):
    p = PROVIDERS[provider]
    fresh = max(input_tokens - cached_tokens, 0)
    return fresh * p["in"] + cached_tokens * p["cached"] + output_tokens * p["out"] + retrievals * p["retrieval"]


def shorten(messages):
    """Large system prompts are logged as length + hash; the text itself is in data/."""
    return [m if len(m["content"]) < 1500 else
            {**m, "content": f"<{len(m['content'])} chars sha256:{hashlib.sha256(m['content'].encode()).hexdigest()[:12]}>"}
            for m in messages]


async def chat(client, provider, messages, log, label, *, phase="core", headers=None, max_tokens=300,
               temperature=0.2, extra=None, meta=None):
    """Stream one chat completion, time it, log it, charge it. Retries only on 429/503, and records each one."""
    p = PROVIDERS[provider]
    body = {"model": p["model"], "messages": messages, "temperature": temperature, "max_tokens": max_tokens,
            "stream": True, "stream_options": {"include_usage": True}, **(extra or {})}
    sent = {"Authorization": auth_header(provider), "Content-Type": "application/json", **(headers or {})}
    worst = token_cost(provider, sum(len(m["content"]) for m in messages) // 3 + 4000, 0, max_tokens, 1)
    retries = []
    for attempt in range(5):
        guard(worst, phase)
        rec = {"label": label, "provider": provider, **(meta or {}), "status": None, "text": "", "reasoning_chars": 0,
               "ttft_ms": None, "content_ms": None, "spoken_ms": None, "total_ms": None, "retrieve_ms": None,
               "usage": None, "finish": None, "error": None, "cost_usd": 0.0,
               "request": {"url": p["base"] + "/chat/completions", "body": {**body, "messages": shorten(messages)},
                           "headers": {k: v for k, v in sent.items() if k != "Authorization"}}}
        start = time.perf_counter()
        ms = lambda: round((time.perf_counter() - start) * 1000, 1)
        wait = None
        try:
            async with client.stream("POST", p["base"] + "/chat/completions", headers=sent, json=body) as r:
                rec["status"] = r.status_code
                rec["response_headers"] = {k: v for k, v in r.headers.items()
                                           if k.startswith(("x-moss", "x-ratelimit", "retry-after", "x-request"))}
                if r.headers.get("x-moss-retrieve-ms"):
                    rec["retrieve_ms"] = float(r.headers["x-moss-retrieve-ms"])
                if r.status_code != 200:
                    rec["error"] = (await r.aread()).decode(errors="replace")[:1500]
                    if r.status_code in (429, 503):
                        wait = min(float(r.headers.get("retry-after") or 5), 65)
                else:
                    async for line in r.aiter_lines():
                        if not line.startswith("data:") or line[5:].strip() == "[DONE]":
                            continue
                        chunk = json.loads(line[5:])
                        rec["usage"] = chunk.get("usage") or (chunk.get("x_groq") or {}).get("usage") or rec["usage"]
                        if chunk.get("error"):
                            rec["error"] = chunk["error"]
                        for choice in chunk.get("choices") or []:
                            delta = choice.get("delta") or {}
                            thought, piece = delta.get("reasoning") or delta.get("reasoning_content"), delta.get("content")
                            if (thought or piece) and rec["ttft_ms"] is None:
                                rec["ttft_ms"] = ms()
                            rec["reasoning_chars"] += len(thought or "")
                            if piece:
                                rec["content_ms"] = rec["content_ms"] or ms()
                                rec["text"] += piece
                                # First words a TTS engine could speak: text after the <meta> header.
                                tail = rec["text"].partition("</meta>")[2]
                                if rec["spoken_ms"] is None and tail.strip():
                                    rec["spoken_ms"] = ms()
                            rec["finish"] = choice.get("finish_reason") or rec["finish"]
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            rec["error"] = f"{type(e).__name__}: {e}"
        rec["total_ms"] = ms()
        if wait is None:
            break
        retries.append({"status": rec["status"], "wait_s": wait, "error": rec["error"]})
        log.write({"label": label, "retrying_after": retries[-1]})
        await asyncio.sleep(wait + 0.5)

    rec["retries"] = len(retries)
    usage = rec["usage"]
    if usage:
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        searched = "X-Moss-Indexes" in sent and usage.get("prompt_tokens", 0) > 0
        rec["prompt_tokens"], rec["cached_tokens"] = usage.get("prompt_tokens", 0), cached
        rec["completion_tokens"] = usage.get("completion_tokens", 0)
        rec["cost_usd"] = token_cost(provider, rec["prompt_tokens"], cached, rec["completion_tokens"], int(searched))
    elif rec["status"] == 200:
        rec["cost_usd"] = worst  # billed amount unknown, so assume the worst
    if rec["cost_usd"]:
        charge(label, rec["cost_usd"], phase, provider)
    rec["ok"] = rec["status"] == 200 and not rec["error"] and bool(rec["text"])
    log.write(rec)
    return rec


def http_client():
    return httpx.AsyncClient(timeout=httpx.Timeout(60, connect=15),
                             limits=httpx.Limits(max_connections=10, max_keepalive_connections=10, keepalive_expiry=120))


if __name__ == "__main__":  # offline self-check
    import tempfile

    SECRETS.update(MOSS_PROJECT_ID="pid-1234", MOSS_PROJECT_KEY="moss_" + "k" * 32, GROQ_API_KEY="gsk_" + "g" * 40)
    dirty = f"Authorization: {moss_auth()} {SECRETS['GROQ_API_KEY']} org_01abcdefghijklmn project 1a2b3c4d https://x.io/a.png?X-Amz-Signature=abc 9812345678 someone@example.edu"
    clean = redact(dirty)
    for leak in (*SECRETS.values(), "1a2b3c4d", "01abcdefghijklmn", "=abc", "9812345678", "someone@example.edu"):
        assert leak not in clean, (leak, clean)
    assert abs(token_cost("moss", 1_000_000, 0, 0) - 0.25) < 1e-9
    assert abs(token_cost("groq", 1_000_000, 1_000_000, 1_000_000) - 0.675) < 1e-9
    LOGS = Path(tempfile.mkdtemp())
    LEDGER = LOGS / "ledger.jsonl"
    charge("x", 2.99, "core")
    guard(0.001, "combos")
    for worst, phase in ((0.02, "core"), (5.02, "tasks")):
        try:
            guard(worst, phase)
            raise AssertionError(f"guard allowed {worst} in {phase}")
        except BudgetExceeded:
            pass

    sse = "".join(f"data: {json.dumps(c)}\n\n" for c in (
        {"choices": [{"delta": {"content": "<meta>{}</meta>\n"}}]}, {"choices": [{"delta": {"content": "Hi"}, "finish_reason": "stop"}]},
        {"choices": [], "usage": {"prompt_tokens": 1000, "completion_tokens": 100}})) + "data: [DONE]\n\n"

    async def offline():
        transport = httpx.MockTransport(lambda req: httpx.Response(200, headers={"x-moss-retrieve-ms": "7"}, content=sse.encode()))
        async with httpx.AsyncClient(transport=transport) as client:
            log = Log("selfcheck")
            r = await chat(client, "moss", [{"role": "user", "content": "q"}], log, "m", headers={"X-Moss-Indexes": "i"})
            assert r["ok"] and r["retrieve_ms"] == 7 and r["spoken_ms"] >= r["content_ms"], r
            assert abs(r["cost_usd"] - (1000 * 0.25e-6 + 100 * 1.75e-6 + 0.0005)) < 1e-9, r["cost_usd"]
            assert SECRETS["MOSS_PROJECT_KEY"] not in log.path.read_text(encoding="utf-8")

    asyncio.run(offline())
    print("common.py self-check ok")
