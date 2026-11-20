# Retrieval benchmark protocol (FYP-I Final)

**Owner:** Muhammad Umar (Retrieval & Ranking)  
**Status:** adopted 2026-11-20 — do not tune on the 2025 test year  
**Baseline:** commit tagged at plan adoption; **B0** = `rank_diagnostic_checks` + `build_diagnostic_context` as shipped before hybrid work (frozen in `backend/evaluation/baseline_b0.py`).

## Goal

Measure which retrieval/ranking method finds relevant past cases and ranks the correct **part** on held-out FAA data, with leak-free time splits.

## Datasets

| Suite | Unit | Relevance | Primary metrics |
| --- | --- | --- | --- |
| **A — system identification** | 2,000 sampled 2025 reports (stratified) | Same 4-digit JASC **and** same normalised part name | Recall@10, MRR, nDCG@10 |
| **B — resolution prediction** | 981 citation-valid correction pairs (2023–2025) | Query = original narrative; target = part named on the correcting report | Top-1 / top-3 / top-5 part accuracy |

**Corpus files** (offline, from `backend/scripts/fetch_sdr_data.py`):

- `data/raw/SDR-{year}.csv` — not committed  
- `data/processed/correction_pairs.csv` — all valid pairs with year, tails, submission dates  
- `data/evaluation/splits.json` — `train: [2023]`, `tune: [2024]`, `test: [2025]`

## Leakage rules (enforced in tests)

1. For query at submission time *t*, visible reports are those with `submission_date < t` only (occurrence date may match; validity follows **submission** time per master plan).  
2. Never index the query report’s own correction chain when predicting that correction’s part.  
3. **2025 is test-only:** no weight fitting, threshold choice, or embedding selection may use 2025 labels. Fit on 2023; select on 2024; report once on 2025.

## Baselines (run in order)

| ID | Method |
| --- | --- |
| B0 | Mid heuristic ranker (frozen B0 module) |
| B1 | B0 + documented bug fixes (fleet exclude, symptom-weighted history, SUPERSEDES-aware superseded flag) |
| B2 | BM25 over report text |
| B3 | Dense embedding similarity (CPU ONNX, 384-d) |
| B4 | Graph-only (same aircraft / type / JASC constraints) |
| B5 | Hybrid reciprocal-rank fusion (B2 + B3 + B4) |
| B6 | B5 + weights fit on **2024 only** (Should tier) |

**Serving rule:** The module benchmarked is the module behind `/api` for the active `RETRIEVAL_MODE`.

## Reporting

- Point estimates + **95% bootstrap CIs** (2025 pair n≈157).  
- RQ3: on pairs where part **changes**, compare top part with correction-aware demotion **off vs on**.  
- Error analysis: **30 failures** hand-classified (human-only).  
- Negative result allowed: if hybrid does not beat BM25 on 2025, publish with ablation and error table.

## What this does not claim

- Ranking scores are not calibrated probabilities.  
- Conflict F1 is **not** diagnostic accuracy (see Record Integrity vertical).