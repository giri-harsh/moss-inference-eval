## Latency (ms)

| Level | Arm | ok | calls | TTFT p50 | TTFT p95 | Spoken p50 | Spoken p95 | Total p50 | Total p95 | Retrieval p50 | Retrieval p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | groq | 31 | 31 | 676.8 | 906.0 | 814.0 | 1010.9 | 816.9 | 1055.7 |  |  |
| 0 | moss_full | 120 | 120 | 151.9 | 170.0 | 600.3 | 650.3 | 778.9 | 899.1 |  |  |
| 0 | moss_rag | 120 | 120 | 142.8 | 209.0 | 587.6 | 654.8 | 768.6 | 936.1 | 9.8 | 14.1 |
| 1 | moss_full | 120 | 120 | 172.1 | 183.9 | 624.0 | 695.5 | 814.7 | 1037.1 |  |  |
| 1 | moss_rag | 120 | 120 | 145.6 | 207.5 | 591.1 | 662.0 | 798.3 | 1007.8 | 9.8 | 14.4 |
| 2 | moss_full | 120 | 120 | 308.1 | 334.0 | 774.7 | 836.4 | 993.1 | 1258.9 |  |  |
| 2 | moss_rag | 120 | 120 | 145.1 | 174.6 | 592.1 | 639.7 | 770.8 | 978.8 | 10.1 | 16.1 |
| 3 | moss_full | 80 | 80 | 628.6 | 736.9 | 1133.5 | 1246.5 | 1360.5 | 1639.9 |  |  |
| 3 | moss_rag | 80 | 80 | 149.6 | 187.7 | 594.7 | 647.1 | 770.8 | 998.2 | 10.5 | 19.0 |

## Quality, tokens and cost

| Level | Arm | Overall | Answerable | Correct refusal | Urgent | False refusal | Bad format | Prompt tok | Cached share | $ / 1k turns |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | groq | 29/31 | 23/23 | 4/4 | 2/4 | 0/23 | 0 | 7601.0 | 0.284 | 0.5251 |
| 0 | moss_full | 120/120 | 90/90 | 18/18 | 12/12 | 0/90 | 0 | 10243.0 | 0.937 | 0.6305 |
| 0 | moss_rag | 117/120 | 87/90 | 18/18 | 12/12 | 3/90 | 0 | 2889.0 | 0.766 | 0.9165 |
| 1 | moss_full | 120/120 | 105/105 | 3/3 | 12/12 | 0/105 | 0 | 17437.0 | 0.963 | 0.8522 |
| 1 | moss_rag | 117/120 | 102/105 | 3/3 | 12/12 | 3/105 | 0 | 3031.0 | 0.728 | 0.9634 |
| 2 | moss_full | 120/120 | 105/105 | 3/3 | 12/12 | 0/105 | 0 | 66002.0 | 0.994 | 2.2616 |
| 2 | moss_rag | 117/120 | 102/105 | 3/3 | 12/12 | 3/105 | 0 | 3047.0 | 0.799 | 0.9178 |
| 3 | moss_full | 80/80 | 70/70 | 2/2 | 8/8 | 0/70 | 0 | 160145.0 | 0.999 | 5.0278 |
| 3 | moss_rag | 76/80 | 66/70 | 2/2 | 8/8 | 4/70 | 0 | 3039.0 | 0.806 | 0.9106 |

## By category

| Level | Arm | Category | Correct |
|---|---|---|---|
| 0 | groq | disfluent | 8/8 |
| 0 | groq | english | 8/8 |
| 0 | groq | hinglish | 7/7 |
| 0 | groq | unanswerable | 4/4 |
| 0 | groq | urgent | 2/4 |
| 0 | moss_full | disfluent | 24/24 |
| 0 | moss_full | english | 33/33 |
| 0 | moss_full | hinglish | 33/33 |
| 0 | moss_full | unanswerable | 18/18 |
| 0 | moss_full | urgent | 12/12 |
| 0 | moss_rag | disfluent | 24/24 |
| 0 | moss_rag | english | 33/33 |
| 0 | moss_rag | hinglish | 30/33 |
| 0 | moss_rag | unanswerable | 18/18 |
| 0 | moss_rag | urgent | 12/12 |
| 1 | moss_full | disfluent | 24/24 |
| 1 | moss_full | english | 33/33 |
| 1 | moss_full | hinglish | 33/33 |
| 1 | moss_full | unanswerable | 18/18 |
| 1 | moss_full | urgent | 12/12 |
| 1 | moss_rag | disfluent | 21/24 |
| 1 | moss_rag | english | 33/33 |
| 1 | moss_rag | hinglish | 33/33 |
| 1 | moss_rag | unanswerable | 18/18 |
| 1 | moss_rag | urgent | 12/12 |
| 2 | moss_full | disfluent | 24/24 |
| 2 | moss_full | english | 33/33 |
| 2 | moss_full | hinglish | 33/33 |
| 2 | moss_full | unanswerable | 18/18 |
| 2 | moss_full | urgent | 12/12 |
| 2 | moss_rag | disfluent | 21/24 |
| 2 | moss_rag | english | 33/33 |
| 2 | moss_rag | hinglish | 33/33 |
| 2 | moss_rag | unanswerable | 18/18 |
| 2 | moss_rag | urgent | 12/12 |
| 3 | moss_full | disfluent | 16/16 |
| 3 | moss_full | english | 22/22 |
| 3 | moss_full | hinglish | 22/22 |
| 3 | moss_full | unanswerable | 12/12 |
| 3 | moss_full | urgent | 8/8 |
| 3 | moss_rag | disfluent | 14/16 |
| 3 | moss_rag | english | 22/22 |
| 3 | moss_rag | hinglish | 20/22 |
| 3 | moss_rag | unanswerable | 12/12 |
| 3 | moss_rag | urgent | 8/8 |

## Retrieval (MossClient.query)

| level | kb_tokens_est | questions_with_gold | hit@1 | hit@3 | hit@5 | local_query_p50_ms | server_retrieve_p50_ms | server_retrieve_p95_ms |
|---|---|---|---|---|---|---|---|---|
| 0 | 9100 | 34 | 25/34 | 32/34 | 33/34 | 15.7 | 9.8 | 14.1 |
| 1 | 15300 | 39 | 30/39 | 36/39 | 38/39 | 15.1 | 9.8 | 14.4 |
| 2 | 60000 | 39 | 30/39 | 36/39 | 38/39 | 13.5 | 10.1 | 16.1 |
| 3 | 150000 | 39 | 29/39 | 37/39 | 39/39 | 4.5 | 10.5 | 19.0 |

## Hinglish rewrite

_not run_

## Speculative retrieval

_not run_

## Tasks

| Case | Status | HTTP | Error | Correct | Schema ok | Cost $ | Cap $ | Run s | Cap s | Steps | In tok | Out tok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| limit_cost | failed | 202 | budget_exceeded | enforced late |  | 0.02417 | 0.01 | 7.6 | 180 | 1 | 8164 | 82 |
| lookup_fee | completed | 202 |  | yes | True | 0.095606 | 0.2 | 51.8 | 180 | 7 | 121869 | 1084 |
| missing_required | completed | 202 |  | no | True | 0.195766 | 0.2 | 112.8 | 180 | 17 | 396169 | 2402 |
| impossible | completed | 202 |  | yes | False | 0.11093 | 0.2 | 120.7 | 180 | 9 | 155441 | 1858 |

