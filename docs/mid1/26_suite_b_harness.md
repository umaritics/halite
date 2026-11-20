# Suite B offline harness (2026-11-20)

## Purpose

First measurable retrieval baseline on citation-valid correction pairs (resolution prediction), comparing frozen **B0** vs production **B1** rankers.

## Run on staging VM (canonical)

Corpus lives at `/home/umar/halite/corpus_data/` (raw + `evaluation/correction_pairs.csv`).

```bash
docker run --rm --user 0:0 \
  -v /home/umar/halite/backend:/app \
  -v /home/umar/halite/corpus_data:/app/data \
  -w /app halite-api:latest \
  python evaluation/run_suite_b.py \
    --raw-dir data/raw \
    --pairs data/evaluation/correction_pairs.csv \
    --splits data/evaluation/splits.json \
    --split test \
    --ranker both \
    --out data/evaluation/suite_b_test_2025.json
```

Log (example): `/home/umar/halite/logs/suite_b_test_2025.log`

## First numbers (2025 hold-out, n=141)

Committed snapshot: [`logs/suite_b_test_2025.json`](logs/suite_b_test_2025.json) (generated on VM 2026-11-20).

| Ranker | Top-1 | Top-3 | Top-5 | Top-1 95% CI |
| --- | ---: | ---: | ---: | --- |
| B0 (frozen mid) | 0.149 | 0.277 | 0.319 | 0.092 – 0.206 |
| B1 (bug fixes) | 0.199 | 0.284 | 0.319 | 0.135 – 0.262 |

B1 improves top-1 on this slice; hybrid retrieval (B2+) is next.

## CI

`backend/tests/test_suite_b_smoke.py` — toy corpus, no FAA download.

## Protocol

See `docs/plan/BENCHMARK_PROTOCOL.md` — **2025 is test-only**; do not tune on test labels.