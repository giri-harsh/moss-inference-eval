"""Which entries does the server-side search actually put in the prompt? Ask the model to echo the ids it was given.

python -m combos.server_context <level> <qid> [<qid> ...]   (the level's index must exist)
Also records the deeper local ranking (MossClient.query, top 10) for the same query.
"""

import asyncio
import re
import sys

import common
from core import retrieval
from core.corpus import index_name
from core.grade import view
from core.run_core import load_questions

PROMPT = ("This is a retrieval debugging request. Do NOT answer the user's message. Instead, copy out every identifier "
          "written in square brackets, such as [ABC-123] or [WEB-0001], that appears anywhere in the reference material "
          "you were given, in order, separated by spaces. Output only those identifiers.")


async def main(level, qids):
    common.require("MOSS_PROJECT_ID", "MOSS_PROJECT_KEY")
    name, log, before = index_name(level), common.Log(f"server_context_L{level}"), common.spent()
    questions = {q["id"]: view(q, level) for q in load_questions()}
    local = await retrieval.load(name)
    async with common.http_client() as client:
        for qid in qids:
            q = questions[qid]
            deep = await retrieval.search(local, q["question"], "core", top_k=10, index=name)
            r = await common.chat(client, "moss", [{"role": "system", "content": PROMPT}, {"role": "user", "content": q["question"]}],
                                  log, f"server_context_{qid}", temperature=0, max_tokens=200,
                                  headers={"X-Moss-Indexes": name, "X-Moss-Cache": "off", "X-Moss-System-Prompt": "off"})
            ids = re.findall(r"\b(?:[A-Z]{3}-\d{3}|WEB-\d{4})\b", r["text"])
            log.write({"result": True, "qid": qid, "level": level, "gold_ids": q["gold_ids"], "local_top10": deep["chunks"],
                       "server_ids_echoed": ids, "server_reply": r["text"], "retrieve_ms": r["retrieve_ms"],
                       "prompt_tokens": r.get("prompt_tokens")})
            print(level, qid, q["gold_ids"], "echoed:", ids or r["text"][:160], "| local10:", [(c["id"], c["score"]) for c in deep["chunks"]])
    common.report_spend(f"server_context_L{level}", before)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]), sys.argv[2:]))
