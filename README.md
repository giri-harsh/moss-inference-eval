# Moss Inference evaluation: full-prompt vs retrieval for a voice helpdesk

Question: for Resolvix (a campus helpdesk voice agent that puts its whole knowledge base in the prompt), what does
retrieval on Moss change, and where does the full-prompt approach stop working? Run on 26 November 2026, one client location.

| Arm | What it is |
|---|---|
| A | `moss/fastlane-1`, whole knowledge base in the prompt |
| B | `moss/fastlane-1`, same persona, Moss index retrieval (`X-Moss-Indexes`) |
| C | Reference only: Groq `gpt-oss-20b`, prompt trimmed of question variants, one pass |

40 questions (11 English, 11 Hinglish, 8 disfluent, 6 unanswerable, 4 urgent), streamed, reply cache off. Knowledge base
grows from the Resolvix `data` branch (51 entries) to `data-scraped` (74) plus scraped college web pages.

## Results

| KB size (est. tokens) | Arm | Calls | TTFT p50 / p95 ms | First speakable word p50 / p95 ms | Total p50 ms | Correct | Prompt tokens | $ per 1k turns |
|---|---|---|---|---|---|---|---|---|
| 9K | A | 120 | 152 / 170 | 600 / 650 | 779 | 120/120 | 10,243 | 0.63 |
| 9K | B | 120 | **143** / 209 | 588 / 655 | 769 | 117/120 | 2,889 | 0.92 |
| 9K | C | 31 | 677 / 906 | 814 / 1011 | 817 | 29/31 | 7,601 | 0.53 |
| 15K | A | 120 | 172 / 184 | 624 / 696 | 815 | 120/120 | 17,437 | 0.85 |
| 15K | B | 120 | **146** / 208 | 591 / 662 | 798 | 117/120 | 3,031 | 0.96 |
| 60K | A | 120 | 308 / 334 | 775 / 836 | 993 | 120/120 | 66,002 | 2.26 |
| 60K | B | 120 | **145** / 175 | 592 / 640 | 771 | 117/120 | 3,047 | **0.92** |
| 150K | A | 80 | 629 / 737 | 1134 / 1247 | 1361 | 80/80 | 160,145 | 5.03 |
| 150K | B | 80 | **150** / 188 | 595 / 647 | 771 | 76/80 | 3,039 | **0.91** |

![Time to first token vs knowledge-base size](results/ttft_vs_kb.png)

Server-side retrieval took 9.8–10.5 ms p50 (14–19 ms p95) at every size. Network round trip to Moss: 38 ms median.

Local `MossClient.query` ranking of the expected entry:

| KB | hit@1 | hit@3 | hit@5 |
|---|---|---|---|
| 9K | 25/34 | 32/34 | 33/34 |
| 15K | 30/39 | 36/39 | 38/39 |
| 60K | 30/39 | 36/39 | 38/39 |
| 150K | 29/39 | 37/39 | 39/39 |

## The only retrieval-arm errors: D01 and H03

All 13 wrong answers in B are these two questions, each escalated although the answer was in the index.
Chunks and scores below are from `MossClient.query` (top 5, in returned order); full list in
[results/d01_h03_chunks.csv](results/d01_h03_chunks.csv). **Expected entry in bold.**

| Question | KB | B wrong | Local top 5 (id score) |
|---|---|---|---|
| H03 "college ka address kya hai?" | 9K | 3/3 | GEN-102 .621, FEE-102 .632, TRN-101 .574, GEN-106 .547, **GEN-104 .517** |
| H03 | 15K, 60K | 0/6 | **GEN-104 .575**, ADM-109 .569, EXM-101 .651, GEN-119 .610, TRN-102 .610 |
| H03 | 150K | 2/2 | **GEN-104 .575**, ADM-109 .569, WEB-0238 .683, EXM-101 .651, GEN-119 .610 |
| D01 disfluent "how do I um pay the fees online?" | 9K | 0/3 | **FEE-101 .412**, FEE-108 .332, FEE-107 .258, TRN-102 .204, FEE-102 .225 |
| D01 | 15K, 60K | 6/6 | FEE-111 .401, FEE-102 .350, FEE-113 .243, **FEE-103 .214**, EXM-104 .148 |
| D01 | 150K | 2/2 | FEE-111 .401, FEE-102 .350, FEE-113 .243, WEB-0355 .222, **FEE-103 .214** |

- D01 failed whenever the expected entry ranked 4th or 5th and passed when it ranked 1st.
- H03 does not fully fit that pattern: at 150K it ranks 1st locally and still failed twice. The inference API does not
  return the chunks it used, so the server's ranking cannot be checked against the local one.

## Tasks (4 runs on akgec.ac.in, `moss-balanced`, 180 s cap)

| Case | Status | Correct? | Cost / cap | Time, steps | What happened |
|---|---|---|---|---|---|
| B.Tech first-year fee, JSON schema | completed | yes | $0.096 / $0.20 | 52 s, 7 | Rs 142156 with the right URL; the figure sits in an embedded PDF |
| Impossible: stock ticker and share price | completed, schema failed | yes, nothing invented | $0.111 / $0.20 | 121 s, 9 | Returned nulls; went to an outside search engine |
| Required field with no data: hostel Wi-Fi password | completed, **schema passed** | **no** | $0.196 / $0.20 | 113 s, 17 | Put "Not found on the website pages searched" in the required string |
| $0.01 spend cap | failed, `budget_exceeded` | cap enforced late | **$0.024 / $0.01** | 8 s, 1 | Overshot 2.4x |

Browser traffic cost was still unreported (`traffic_usd: null`) after the run.

## Findings

| Severity | Finding |
|---|---|
| High | Full-prompt time to first token grows with KB size (152 ms at 9K, 629 ms at 150K, even with 99.9% of input cached). Retrieval stays near 145 ms. |
| High | Cold starts, one observation each: the first call with a new, mostly uncached full prompt reached first token after 1.3 s (15K), 4.3 s (60K) and 15.9 s (150K). The first search on a new index took 2.2–2.5 s. Both can exceed Resolvix's 3 s first-token timeout. |
| High | A schema `required` field can be satisfied by a placeholder sentence, with `verification.passed: true`. |
| High (Resolvix) | The unmodified 51-entry prompt is rejected by this Groq on-demand key (HTTP 413, 8,000 tokens per minute), and 120b returned empty replies on a trimmed prompt (3 logged calls). C stopped at the 200,000-token daily quota. |
| Medium | Retrieval lost 3 of 120 answers at up to 60K and 4 of 80 at 150K that the full prompt got right. |
| Medium | Pre-model retrieval returns only `X-Moss-Retrieve-Ms`: no chunk ids or scores, so misses are hard to debug. `MossClient.query` runs a local embedding model and is not guaranteed to match. |
| Medium | `max_cost_usd` overshot at $0.01. The docs say it covers model calls only and lets running calls finish. |
| Medium | Below about 15K tokens the full prompt is cheaper than retrieval ($0.50 per 1k searches plus less prefix caching). By 60K retrieval is about 2.5x cheaper. |
| Low | An impossible task ends `completed`; callers must check `verification.passed`. |
| Info | First token is under 200 ms at p50 for grounded calls, as documented; p95 was 175–209 ms. |
| Info | About 450 ms passes between the first token and the first speakable word because Resolvix's reply format puts a JSON header first. Moving the header after the sentence should remove most of that wait (not tested). |
| Info | Urgent detection: A and B 100%; C missed 2 of 4. |
| Info | The Resolvix `data` prompt is about 9K tokens, not the ~100K originally assumed. |

## Not run

- 432K level (larger than the 262,144-token window), and the third 150K pass: stopped for time.
- 9 of 40 questions for C (daily quota).
- Hinglish query rewrite and speculative (prefix) retrieval: scripts in `combos/`, **not run**.
- **Jev gate: planned, not run** (no key). Design: after retrieval, send the query, Moss top-k chunks and their scores
  to a Jev Choice question with options `answer` / `refuse` / `escalate` / `urgent_transfer`; report refusal accuracy,
  escalation precision and recall, and added latency against arm B.
- Other Tasks cases (cancel, 1-minute cap, fake task id, malformed schema, goal that asks to ignore limits, more lookups),
  concurrency sweeps, OpenAI-SDK compatibility and the error-case matrix.

## Read the numbers with care

- One machine, one afternoon; B and A calls were interleaved. The tasks ran during the second 150K pass (its p50 matched the first).
- The cost columns assume the warm prefix cache seen in a back-to-back benchmark. Real call traffic will cache less.
- Costs are computed from token counts at published prices.
- C is not like for like: smaller model, trimmed prompt, 31 calls; rate-limit waits are excluded from its latency.
- Grading is rule-based ([core/grade.py](core/grade.py)). 6 arm-A replies that stated the right fact in other words were
  corrected by hand ([core/overrides.csv](core/overrides.csv)); task correctness was checked by hand.
- Questions and expected answers were written from the knowledge base, so they favour answerable, single-entry lookups.

## Spend

Moss portal for the billing day: **$2.06**, of which $0.07 was an earlier manual task, so about $1.99 for this work
(read right after the last run; the script's own estimate is $1.91). Groq estimate: about $0.02.

## Reproduce

Python 3.12. Credentials come from the environment, or from a dotenv file named by `EVAL_ENV_FILE`:
`MOSS_PROJECT_ID`, `MOSS_PROJECT_KEY`, and `GROQ_API_KEY` for arm C. Knowledge-base files are read from a clone of
[Resolvix-AI](https://github.com/giri-harsh/Resolvix-AI) at pinned commits (cloned automatically, or set `RESOLVIX_REPO`).

```bash
pip install -r requirements.txt
python common.py && python -m core.grade && python -m core.make_eval_set   # offline checks
python -m core.network
python -m core.build_index 0
python -m core.run_core --level 0 --arms moss_full,moss_rag --reps 3
python -m core.build_index 2 && python -m core.run_core --level 2 --arms moss_full,moss_rag && python -m core.build_index 2 --delete
python -m core.run_core --level 0 --arms groq --reps 1 --groq-model openai/gpt-oss-20b --compact-prefix
python -m tasks.run_tasks lookup_fee impossible missing_required limit_cost
python analyze.py
```

A spend guard stops any call that could pass $8.00 in total ($3 / $3 / $2 for core, tasks and combos). Every request,
response and timing is in `logs/` with keys, account ids, phone numbers and e-mail addresses redacted.
In `results/spend_log.csv` the per-test amounts overlap where tests ran at the same time; the ledger is authoritative.
