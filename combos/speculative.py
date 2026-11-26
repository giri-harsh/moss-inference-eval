"""Speculative retrieval: query on growing word prefixes (simulated interim ASR) and compare top-1 with the full query."""

import asyncio
import math

import common
from core import retrieval
from core.run_core import load_questions

FRACTIONS = (0.4, 0.7, 1.0)


def prefix(text, fraction):
    words = text.split()
    return " ".join(words[:max(1, math.ceil(len(words) * fraction))])


async def main():
    assert prefix("a b c d e f g h i j", 0.4) == "a b c d" and prefix("a b", 1.0) == "a b" and prefix("a", 0.4) == "a"
    before, log = common.spent(), common.Log("speculative")
    local = await retrieval.load()
    for q in load_questions():
        steps = {str(f): await retrieval.search(local, prefix(q["question"], f), "combos") for f in FRACTIONS}
        log.write({"qid": q["id"], "category": q["category"], "gold_ids": q["gold_ids"], "steps": steps})
    common.report_spend("speculative", before)


if __name__ == "__main__":
    asyncio.run(main())
