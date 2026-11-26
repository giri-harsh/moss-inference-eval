"""Turn logs/*.jsonl into results/*.csv, charts and Markdown tables (results/tables.md). No network.

Grades come from core/grade.py; hand corrections live in core/overrides.csv (label,correct,reason) and
tasks/manual_checks.csv (case,correct,note) and are applied here, so every changed grade is visible.
"""

import csv
import json
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import common
from core.grade import grade, view

ARMS = {"moss_full": ("A: Moss, full KB in prompt", "#2a78d6"), "moss_rag": ("B: Moss + index retrieval", "#eb6834"),
        "groq": ("C: Groq gpt-oss-20b, trimmed KB", "#1baf7a")}
KB_TOKENS = {0: 9_100, 1: 15_300, 2: 60_000, 3: 150_000, 4: 432_000}  # prompt characters / 4
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def pct(values, q):
    values = [v for v in values if v is not None]
    return round(float(np.percentile(values, q)), 1) if values else None


def mean(values, digits=1):
    values = [v for v in values if v is not None]
    return round(float(np.mean(values)), digits) if values else None


def share(rows, key):
    rows = [r for r in rows if r[key] is not None]
    return f"{sum(bool(r[key]) for r in rows)}/{len(rows)}" if rows else ""


def read_overrides(path, key):
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {row[key]: row for row in csv.DictReader(f)}


def core_calls():
    questions = {q["id"]: q for q in common.read_jsonl(common.ROOT / "core" / "eval_set.jsonl")}
    fixed = read_overrides(common.ROOT / "core" / "overrides.csv", "label")
    calls = []
    for path in sorted(common.LOGS.glob("core_L*.jsonl")):
        for r in common.read_jsonl(path):
            if "arm" not in r or r.get("warmup"):
                continue
            if r["arm"] == "groq" and r["status"] != 200:
                continue  # daily-quota refusal: not run, not a wrong answer
            q = view(questions[r["qid"]], r["level"])
            g = grade(q, r["text"] or "")
            if r["label"] in fixed:
                value = fixed[r["label"]]["correct"] == "1"
                g.update(correct=value, override=fixed[r["label"]]["reason"])
                for key in ("correct_refusal", "urgent_ok"):
                    if g[key] is not None:
                        g[key] = value
            calls.append({"label": r["label"], "level": r["level"], "arm": r["arm"], "qid": r["qid"], "category": r["category"],
                          "answerable": q["answerable"], "rep": r.get("rep"), "status": r["status"], "ok": r["ok"],
                          "retries": r["retries"], "ttft_ms": r["ttft_ms"] if r["ok"] else None,
                          "spoken_ms": r["spoken_ms"] if r["ok"] else None, "total_ms": r["total_ms"] if r["ok"] else None,
                          "retrieve_ms": r["retrieve_ms"] if r["arm"] == "moss_rag" else None,
                          "prompt_tokens": r.get("prompt_tokens"), "cached_tokens": r.get("cached_tokens"),
                          "completion_tokens": r.get("completion_tokens"), "cost_usd": r["cost_usd"], **g,
                          "error": json.dumps(r["error"]) if r["error"] else ""})
    # The scale run was stopped on purpose: keep only complete Moss passes (every question, both arms).
    full = 2 * len(questions)
    size = {}
    for c in calls:
        if c["arm"] != "groq":
            size[c["level"], c["rep"]] = size.get((c["level"], c["rep"]), 0) + 1
    return [c for c in calls if c["arm"] == "groq" or size[c["level"], c["rep"]] == full]


def summarise(calls):
    out = []
    for level, arm in sorted({(c["level"], c["arm"]) for c in calls}):
        rows = [c for c in calls if (c["level"], c["arm"]) == (level, arm)]
        ok = [c for c in rows if c["ok"]]
        answerable = [c for c in rows if c["answerable"] and c["category"] != "urgent"]
        refusal = [c for c in rows if not c["answerable"] and c["category"] != "urgent"]
        urgent = [c for c in rows if c["category"] == "urgent"]
        tokens = sum(c["prompt_tokens"] or 0 for c in ok)
        s = {"level": level, "kb_tokens_est": KB_TOKENS[level], "arm": arm, "calls": len(rows), "ok": len(ok),
             "questions": len({c["qid"] for c in rows})}
        for key in ("ttft_ms", "spoken_ms", "total_ms", "retrieve_ms"):
            s[f"{key[:-3]}_p50_ms"], s[f"{key[:-3]}_p95_ms"] = pct([c[key] for c in rows], 50), pct([c[key] for c in rows], 95)
        s.update(prompt_tokens_mean=mean([c["prompt_tokens"] for c in ok], 0),
                 completion_tokens_mean=mean([c["completion_tokens"] for c in ok], 0),
                 cached_share=round(sum(c["cached_tokens"] or 0 for c in ok) / tokens, 3) if tokens else None,
                 usd_per_1k_calls=round(1000 * sum(c["cost_usd"] for c in ok) / len(ok), 4) if ok else None,
                 usd_total=round(sum(c["cost_usd"] for c in rows), 5),
                 answer_correct=share(answerable, "correct"), correct_refusal=share(refusal, "correct_refusal"),
                 urgent_recognised=share(urgent, "urgent_ok"), false_refusal=share(answerable, "false_refusal"),
                 format_failures=sum(not c["format_ok"] for c in ok), overall_correct=share(rows, "correct"),
                 rate_limit_retries=sum(c["retries"] for c in rows))
        out.append(s)
    return out


def retrieval_rows():
    rows = []
    for path in sorted(common.LOGS.glob("retrieval_L*.jsonl")):
        for r in common.read_jsonl(path):
            ids = [c["id"] for c in r["chunks"]]
            row = {"level": r["level"], "qid": r["qid"], "gold": " ".join(r["gold_ids"]), "top_ids": " ".join(ids),
                   "scores": " ".join(str(c["score"]) for c in r["chunks"]), "local_wall_ms": r["wall_ms"]}
            for k in (1, 3, 5):
                row[f"hit@{k}"] = int(bool(set(ids[:k]) & set(r["gold_ids"]))) if r["gold_ids"] else None
            rows.append(row)
    return rows


def retrieval_summary(rows, summary):
    out = []
    for level in sorted({r["level"] for r in rows}):
        scored = [r for r in rows if r["level"] == level and r["hit@1"] is not None]
        server = next((s for s in summary if s["level"] == level and s["arm"] == "moss_rag"), {})
        out.append({"level": level, "kb_tokens_est": KB_TOKENS[level], "questions_with_gold": len(scored),
                    **{f"hit@{k}": f"{sum(r[f'hit@{k}'] for r in scored)}/{len(scored)}" for k in (1, 3, 5)},
                    "local_query_p50_ms": pct([r["local_wall_ms"] for r in rows if r["level"] == level], 50),
                    "server_retrieve_p50_ms": server.get("retrieve_p50_ms"), "server_retrieve_p95_ms": server.get("retrieve_p95_ms")})
    return out


def rewrite_results():
    rows = [r for r in common.read_jsonl(common.LOGS / "rewrite.jsonl") if r.get("result")]
    detail = []
    for r in rows:
        row = {"qid": r["qid"], "raw_query": r["raw"]["query"], "rewritten_query": r["rewritten"]["query"],
               "rewrite_ok": r["rewrite_ok"], "rewrite_ms": r["rewrite_ms"]}
        for name in ("raw", "rewritten"):
            ids = [c["id"] for c in r[name]["chunks"]]
            for k in (1, 3, 5):
                row[f"{name}_hit@{k}"] = int(bool(set(ids[:k]) & set(r["gold_ids"])))
        detail.append(row)
    summary = [{"query": name, "n": len(detail),
                **{f"hit@{k}": f"{sum(d[f'{name}_hit@{k}'] for d in detail)}/{len(detail)}" for k in (1, 3, 5)},
                "added_latency_p50_ms": 0 if name == "raw" else pct([d["rewrite_ms"] for d in detail], 50),
                "added_latency_p95_ms": 0 if name == "raw" else pct([d["rewrite_ms"] for d in detail], 95)}
               for name in ("raw", "rewritten")] if detail else []
    return detail, summary


def speculative_results():
    rows = common.read_jsonl(common.LOGS / "speculative.jsonl")
    if not rows:
        return [], []
    detail = []
    for r in rows:
        top = {f: (s["chunks"][0]["id"] if s["chunks"] else None) for f, s in r["steps"].items()}
        row = {"qid": r["qid"], "category": r["category"], "gold": " ".join(r["gold_ids"])}
        for f, s in r["steps"].items():
            pc = int(float(f) * 100)
            row.update({f"query_{pc}": s["query"], f"top1_{pc}": top[f], f"ms_{pc}": s["wall_ms"]})
        row.update({"match_40": int(top["0.4"] == top["1.0"]), "match_70": int(top["0.7"] == top["1.0"])})
        detail.append(row)
    summary = []
    for group in ["all", *dict.fromkeys(d["category"] for d in detail)]:
        g = [d for d in detail if group in ("all", d["category"])]
        gold = [d for d in g if d["gold"]]
        summary.append({"group": group, "n": len(g),
                        "prefix40_gives_final_top1": f"{sum(d['match_40'] for d in g)}/{len(g)}",
                        "prefix70_gives_final_top1": f"{sum(d['match_70'] for d in g)}/{len(g)}",
                        **{f"gold_top1_at_{p}": f"{sum(d[f'top1_{p}'] in d['gold'].split() for d in gold)}/{len(gold)}"
                           for p in (40, 70, 100)}})
    return detail, summary


def task_results():
    checks = read_overrides(common.ROOT / "tasks" / "manual_checks.csv", "case")
    out = {}
    for path in sorted(common.LOGS.glob("tasks*.jsonl"), key=lambda p: p.stat().st_mtime):
        for r in common.read_jsonl(path):
            if not r.get("summary"):
                continue
            task = r.get("task") or {}
            usage, limits = task.get("usage") or {}, task.get("limits") or {}
            cost = usage.get("cost") or {}
            runtime = None
            if task.get("started_at") and task.get("finished_at"):
                stamp = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
                runtime = round((stamp(task["finished_at"]) - stamp(task["started_at"])).total_seconds(), 1)
            error = task.get("error") or (r.get("error") or {})
            if isinstance(error, dict) and "error" in error:
                error = error["error"]
            check = checks.get(r["case"], {})
            out[r["case"]] = {
                "case": r["case"], "http_create": r.get("create_status", 202), "status": task.get("status", ""),
                "error_code": error.get("code") or error.get("type", "") if isinstance(error, dict) else str(error),
                "error_message": error.get("message", "") if isinstance(error, dict) else "",
                "schema_passed": (task.get("verification") or {}).get("passed"), "correct": check.get("correct", ""),
                "check_note": check.get("note", ""), "output": json.dumps((task.get("result") or {}).get("output"), ensure_ascii=False),
                "answer_text": ((task.get("result") or {}).get("output_text") or "")[:300],
                "cap_usd": limits.get("max_cost_usd"), "cap_s": limits.get("max_runtime_seconds"),
                "cost_usd": cost.get("total_usd", usage.get("cost_usd")), "model_usd": cost.get("model_usd"),
                "browser_usd": cost.get("browser_usd"), "traffic_usd": cost.get("traffic_usd"), "runtime_s": runtime,
                "steps": usage.get("steps"), "model_calls": usage.get("model_calls"), "input_tokens": usage.get("input_tokens"),
                "cached_input_tokens": usage.get("cached_input_tokens"), "output_tokens": usage.get("output_tokens"),
                "cancel_to_cancelled_s": r.get("cancel_to_cancelled_s")}
    return list(out.values())


def wrong_escalation_chunks(calls, found):
    """Chunks and scores (MossClient.query, top 5) behind the two questions retrieval mode wrongly escalated."""
    out = []
    for r in found:
        if r["qid"] not in ("D01", "H03"):
            continue
        rag = [c for c in calls if (c["arm"], c["level"], c["qid"]) == ("moss_rag", r["level"], r["qid"])]
        wrong = sum(not c["correct"] for c in rag)
        gold = r["gold"].split()
        for rank, (cid, score) in enumerate(zip(r["top_ids"].split(), r["scores"].split()), 1):
            out.append({"level": r["level"], "qid": r["qid"], "rag_wrong": f"{wrong}/{len(rag)}", "rank": rank, "chunk_id": cid,
                        "score": score, "is_gold": int(cid in gold)})
    return out


def md(rows, columns):
    if not rows:
        return "_not run_\n"
    head = "| " + " | ".join(columns.values()) + " |\n|" + "---|" * len(columns) + "\n"
    body = "".join("| " + " | ".join("" if r.get(k) is None else str(r.get(k)).replace("|", "/") for k in columns) + " |\n" for r in rows)
    return head + body


def style(ax, title, ylabel):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, color=INK, fontsize=11, loc="left")
    ax.set_ylabel(ylabel, color=MUTED)
    ax.tick_params(colors=MUTED, labelsize=8.5, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side, spine in ax.spines.items():
        spine.set_visible(side == "bottom")
        spine.set_color(GRID)


def chart(summary):
    """Time to first token against knowledge-base size, full prompt vs retrieval."""
    fig, ax = plt.subplots(figsize=(8, 4.4))
    style(ax, "Time to first token vs knowledge-base size (p50 line, shaded to p95)", "ms")
    for arm in ("moss_full", "moss_rag"):
        pts = [s for s in summary if s["arm"] == arm and s["ttft_p50_ms"] is not None]
        label, colour = ARMS[arm]
        x = [s["kb_tokens_est"] for s in pts]
        y = [s["ttft_p50_ms"] for s in pts]
        ax.plot(x, y, color=colour, linewidth=2, marker="o", markersize=7, markeredgecolor=SURFACE, label=label)
        ax.fill_between(x, y, [s["ttft_p95_ms"] for s in pts], color=colour, alpha=0.13, linewidth=0)
        for xi, yi in zip(x, y):
            above = arm == "moss_full"
            ax.annotate(f"{yi:,.0f}", (xi, yi), textcoords="offset points", xytext=(0, 8 if above else -14),
                        ha="center", fontsize=8.5, color=INK)
    levels = sorted({s["kb_tokens_est"] for s in summary if s["arm"] != "groq"})
    ax.set_xscale("log")
    ax.set_xticks(levels, [f"{v / 1000:.0f}K" for v in levels])
    ax.minorticks_off()
    ax.set_xlabel("knowledge-base size (estimated tokens, log scale)", color=MUTED)
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK, loc="upper left")
    common.RESULTS.mkdir(exist_ok=True)
    fig.savefig(common.RESULTS / "ttft_vs_kb.png", dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def main():
    calls = core_calls()
    summary = summarise(calls)
    found = retrieval_rows()
    found_summary = retrieval_summary(found, summary)
    rewrite, rewrite_summary = rewrite_results()
    speculative, speculative_summary = speculative_results()
    tasks = task_results()
    categories = [{"level": lv, "arm": a, "category": c,
                   "correct": share([x for x in calls if (x["level"], x["arm"], x["category"]) == (lv, a, c)], "correct")}
                  for lv, a, c in sorted({(x["level"], x["arm"], x["category"]) for x in calls})]
    for name, rows in (("core_calls", calls), ("summary", summary), ("by_category", categories), ("retrieval", found),
                       ("retrieval_summary", found_summary), ("rewrite", rewrite), ("rewrite_summary", rewrite_summary),
                       ("speculative", speculative), ("speculative_summary", speculative_summary), ("tasks", tasks),
                       ("d01_h03_chunks", wrong_escalation_chunks(calls, found))):
        if rows:
            common.write_csv(f"{name}.csv", rows)
    chart(summary)
    names = {"level": "Level", "arm": "Arm"}
    sections = [
        ("Latency (ms)", md(summary, {**names, "ok": "ok", "calls": "calls", "ttft_p50_ms": "TTFT p50", "ttft_p95_ms": "TTFT p95",
                                      "spoken_p50_ms": "Spoken p50", "spoken_p95_ms": "Spoken p95", "total_p50_ms": "Total p50",
                                      "total_p95_ms": "Total p95", "retrieve_p50_ms": "Retrieval p50", "retrieve_p95_ms": "Retrieval p95"})),
        ("Quality, tokens and cost", md(summary, {**names, "overall_correct": "Overall", "answer_correct": "Answerable",
                                                  "correct_refusal": "Correct refusal", "urgent_recognised": "Urgent",
                                                  "false_refusal": "False refusal", "format_failures": "Bad format",
                                                  "prompt_tokens_mean": "Prompt tok", "cached_share": "Cached share",
                                                  "usd_per_1k_calls": "$ / 1k turns"})),
        ("By category", md(categories, {**names, "category": "Category", "correct": "Correct"})),
        ("Retrieval (MossClient.query)", md(found_summary, {k: k for k in (found_summary[0] if found_summary else {})})),
        ("Hinglish rewrite", md(rewrite_summary, {k: k for k in (rewrite_summary[0] if rewrite_summary else {})})),
        ("Speculative retrieval", md(speculative_summary, {k: k for k in (speculative_summary[0] if speculative_summary else {})})),
        ("Tasks", md(tasks, {"case": "Case", "status": "Status", "http_create": "HTTP", "error_code": "Error", "correct": "Correct",
                             "schema_passed": "Schema ok", "cost_usd": "Cost $", "cap_usd": "Cap $", "runtime_s": "Run s",
                             "cap_s": "Cap s", "steps": "Steps", "input_tokens": "In tok", "output_tokens": "Out tok"})),
    ]
    (common.RESULTS / "tables.md").write_text("".join(f"## {t}\n\n{b}\n" for t, b in sections), encoding="utf-8")
    print((common.RESULTS / "tables.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
