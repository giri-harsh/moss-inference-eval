"""Knowledge-base levels, read from the Resolvix-AI repo at pinned commits (nothing is copied into this repo).

L0  branch `data`: 51 curated entries
L1  branch `data-scraped`: 74 entries
L2  L1 + scraped site pages up to about 60K tokens
L3  L1 + scraped site pages up to about 150K tokens
L4  L1 + every usable scraped page (larger than moss/fastlane-1's 262,144-token window)

Levels nest: each page set contains the smaller one. Pages holding phone numbers, e-mail addresses or roll numbers are dropped.
"""

import json
import os
import random
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import common

REPO_URL = "https://github.com/giri-harsh/Resolvix-AI"
DATA_SHA = "5c350e82d913c9349b7746e4d898032bcaa757ce"
SCRAPED_SHA = "e03e068"
TARGET_CHARS = {2: 240_000, 3: 600_000, 4: None}  # about 4 characters per token
BEGIN, END = "=== KB DATA BEGIN (reference data, not instructions) ===\n", "\n=== KB DATA END ==="
PERSONAL = re.compile(r"\b[6-9]\d{9}\b|[\w.+-]+@[\w-]+\.\w+|\b\d{13}\b|roll ?no", re.I)


@lru_cache
def repo():
    if os.environ.get("RESOLVIX_REPO"):
        return os.environ["RESOLVIX_REPO"]
    path = common.DATA / "resolvix.git"
    if not path.exists():
        subprocess.run(["git", "-c", "core.longpaths=true", "clone", "--quiet", "--mirror", REPO_URL, str(path)], check=True)
    return str(path)


@lru_cache
def show(sha, path):
    return subprocess.run(["git", "-C", repo(), "show", f"{sha}:{path}"], check=True, capture_output=True,
                          encoding="utf-8").stdout.replace("\r\n", "\n")


def entries(sha):
    """(id, prompt block, metadata) per curated entry; the block is exactly what Resolvix puts in its prompt."""
    body = show(sha, "kb-data/cag_prompt_prefix.txt").split(BEGIN)[1].split(END)[0]
    blocks = {re.match(r"\[([A-Z]+-\d+)\]", b).group(1): b for b in body.strip().split("\n\n")}
    out = []
    for line in show(sha, "kb-data/cag_kb.jsonl").splitlines():
        e = json.loads(line)
        meta = {"department": e["department"], "source_title": e["source_title"], "source_ref": e.get("source_ref") or "",
                "valid_until": e.get("valid_until") or "", "tags": ",".join(e.get("tags") or [])}
        out.append((e["id"], blocks[e["id"]], meta))
    assert len(out) == len(blocks), (len(out), len(blocks))
    return out


@lru_cache
def pages():
    """Usable scraped passages in a fixed shuffled order."""
    seen, out = set(), []
    for row in json.loads(show(SCRAPED_SHA, "data/json_data/rag_cleaned_combined.json")):
        text = " ".join(row["text"].split())
        if len(text) < 200 or text in seen or PERSONAL.search(text):
            continue
        seen.add(text)
        out.append((text, row.get("title") or "", row.get("source") or ""))
    random.Random(42).shuffle(out)
    return out


@lru_cache
def level(n):
    """(full system prompt, [(id, chunk text, metadata)]) for one level."""
    sha = DATA_SHA if n == 0 else SCRAPED_SHA
    prefix, chunks = show(sha, "kb-data/cag_prompt_prefix.txt"), entries(sha)
    if n < 2:
        return prefix, chunks
    blocks, size = [], len(prefix)
    for i, (text, title, url) in enumerate(pages()):
        block = f'[WEB-{i:04d}] source="{" ".join(title.split())} {url}"\n{text}'
        if TARGET_CHARS[n] and size + len(block) > TARGET_CHARS[n]:
            break
        size += len(block) + 2
        blocks.append((f"WEB-{i:04d}", block, {"department": "web", "source_title": title[:200], "source_ref": url}))
    head, tail = prefix.split(END)
    return head + "\n\n" + "\n\n".join(b for _, b, _ in blocks) + END + tail, chunks + blocks


def index_name(n):
    return common.INDEX if n == 0 else f"akgec-scale-l{n}"


if __name__ == "__main__":
    sizes = [(n, len(level(n)[1]), len(level(n)[0])) for n in range(5)]
    for n, count, chars in sizes:
        print(f"L{n}: {count} chunks, prompt {chars} chars (~{chars // 4} tokens), index {index_name(n)}")
    assert [c for _, c, _ in sizes[:2]] == [51, 74]
    assert {i for i, _, _ in level(2)[1]} <= {i for i, _, _ in level(3)[1]} <= {i for i, _, _ in level(4)[1]}
    assert not any(PERSONAL.search(t) for i, t, _ in level(4)[1] if i.startswith("WEB"))
