"""Does rewriting Hinglish to English with a fast Groq call improve top-k retrieval? Baseline: the raw query."""

import asyncio

import common
from core import retrieval
from core.run_core import GROQ_PRICES, load_questions

MODEL = "openai/gpt-oss-120b"  # separate daily quota from the reference run's model; fine for short prompts
PROMPT = ("Rewrite the caller's question, which may be in Hinglish, as one short English search query for a college "
          "helpdesk knowledge base. Keep every name and number. Output only the query.")


async def main():
    common.require("MOSS_PROJECT_ID", "MOSS_PROJECT_KEY", "GROQ_API_KEY")
    common.PROVIDERS["groq"].update(model=MODEL, **dict(zip(("in", "cached", "out"), GROQ_PRICES[MODEL])))
    before, log = common.spent(), common.Log("rewrite")
    subset = [q for q in load_questions() if q["lang"] == "hinglish" and q["gold_ids"]]
    local = await retrieval.load()
    async with common.http_client() as client:
        for q in subset:
            r = await common.chat(client, "groq", [{"role": "system", "content": PROMPT}, {"role": "user", "content": q["question"]}],
                                  log, f"rewrite_{q['id']}", phase="combos", temperature=0, extra={"reasoning_effort": "low"})
            rewritten = r["text"].strip().strip('"') or q["question"]  # a failed rewrite falls back to the raw query
            log.write({"result": True, "qid": q["id"], "gold_ids": q["gold_ids"], "rewrite_ms": r["total_ms"],
                       "rewrite_ok": r["ok"], "raw": await retrieval.search(local, q["question"], "combos"),
                       "rewritten": await retrieval.search(local, rewritten, "combos")})
            print(q["id"], r["status"], r["total_ms"], rewritten, flush=True)
    common.report_spend("rewrite", before)


if __name__ == "__main__":
    asyncio.run(main())
