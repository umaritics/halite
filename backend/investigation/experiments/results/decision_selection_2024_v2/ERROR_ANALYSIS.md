# 2024 decision-selection error analysis

Generated from committed case scores by `python docs/work/usman/verify_decision_selection.py`.
All source/method fingerprints, fitted parameters, selection metrics and every bootstrap interval were reproduced exactly on this environment without network, graph or model calls. See `docs/work/usman/evidence/phase4-selection-replay.txt`.

The selection set contains 389 correction pairs from 340 original reports. 246 outcome part keys are absent from the retrieved top ten; 309 are absent from the top three. There is 1 empty ranking. 168 leading hypotheses have fewer than two evidence records (including the empty case).

| Part-change group | Cases | Outcome absent from top ten | Top-1 matches | Top-3 matches |
| --- | --- | --- | --- | --- |
| unknown_to_named | 53 | 46 | 2 | 3 |
| same | 144 | 47 | 49 | 68 |
| named_to_named | 192 | 153 | 5 | 9 |

These counts describe exact historical part-name agreement. They do not adjudicate a fault cause or label whether a sentence is supported. Unknown outcome keys were excluded before accuracy evaluation and counted in the main result. Multiple corrections of the same original are retained; uncertainty intervals cluster them together.

For a fixed retrieved list, belief reweighting alone cannot recover an outcome absent from that list. The other bucket and abstention are therefore necessary; question selection must be evaluated rather than assumed to solve retrieval misses. Retrieval improvements remain Umar’s work, and this branch changes none of his ranking weights or corpus-builder code.

The weak baseline is consistent with the bounded heuristic being an exploratory history ranking rather than a trained fault predictor. This interpretation is a hypothesis for follow-up, not a measured causal attribution. Exact-name variants, original symptoms, the 2,500-record scan cap, aircraft history and correction-label ambiguity need separate review before attributing individual errors.

## Deterministic examples for review

The first five top-three misses in case-ID order are shown below. They are examples, not a random qualitative sample or human adjudication.

| Correction pair | Outcome key | Ranked first three |
| --- | --- | --- |
| AALA202401032269->AALA202401112269 | APU | LOCK, DOOR, BATTERY |
| AALA202401035310->AALA202401101527 | OVEN | FITTING, SLIDING WINDOW, PIN |
| AALA202401035310->AALA202401105310 | OVEN | FITTING, SLIDING WINDOW, PIN |
| AALA202401038386->AALA202401098386 | SEAL | DOOR, HANDLE, BOTTLE |
| AALA202401057309->AALA202401087309 | OVEN | BATTERY, TAT PROBE, TRANSMITTER |

2025 remains held out. The next empirical step is question-conditioned 2024 evaluation and operating-point selection before a frozen-method 2025 run. No performance improvement or selected production threshold is claimed here.
