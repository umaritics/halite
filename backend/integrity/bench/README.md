# Citation-masked benchmark

Owner: Shahmeer (Record Integrity). Design and reasons:
[DEC-20261124-integrity-masked-benchmark](../../../knowledge/decisions/DEC-20261124-integrity-masked-benchmark.md).

## What it is

- Some FAA reports correct an earlier report and say so ("SUPPLEMENTAL REPORT FOR (id)"). Each one is a free label.
- The builder hides that announcement, then asks what staging would ask of an unannounced correction.
- Stage 1 (no model): is the true earlier report among the candidates, and at what rank?
- Stage 2 (the model): does the model call the pair `supersedes` or `partial_supersedes`?
- Two maskings are built. M1 removes the citation. M2 also removes the "will be submitted" sentence and the OPEN and CLOSED markers.

## Rules

- 2023 is the fit year. 2024 is the select year. 2025 is the test year.
- 2025 is touched once per method version, and only with `--unlock-test "<reason>"`. Every opening is logged.
- Nothing is tuned on 2025. No threshold, prompt, ordering or cut-off is chosen by looking at a 2025 number.
- The 2025 file is kept out of the working folder (see below), so a build of 2023 or 2024 cannot read it.
- Every number comes out of a run into a result file. Nothing is typed in by hand.
- Run all commands from `backend/`.

## 1. Get the FAA files

The source is public. The URL pattern is in `docs/plan/CONTRACTS.md` section 4.4:
`https://external.apic4e.faa.gov/sdrs/retrieve/SDR-{year}.csv`.

```bash
mkdir -p data/raw/faa
curl -fL -o data/raw/faa/SDR-2023.csv https://external.apic4e.faa.gov/sdrs/retrieve/SDR-2023.csv
curl -fL -o data/raw/faa/SDR-2024.csv https://external.apic4e.faa.gov/sdrs/retrieve/SDR-2024.csv
```

`data/raw/` is git-ignored. Files may also be gzipped (`SDR-2023.csv.gz`).
A build of year N reads the file of year N and of every earlier year present, because earlier years are history.
It never reads a later year.

The held-out 2025 file goes outside the repository and outside `data/raw/faa`:

```bash
mkdir -p ~/halite-heldout/faa
curl -fL -o ~/halite-heldout/faa/SDR-2025.csv https://external.apic4e.faa.gov/sdrs/retrieve/SDR-2025.csv
```

Do not download it before the protocol note exists (see "Not done yet" in the decision note).
A 2025 build needs the 2023 and 2024 files beside it, so copy or link them into a folder at run time only.

## 2. Build a bench

```bash
python -m integrity.bench.build --raw-dir data/raw/faa --year 2023 --masking M2 --out data/processed/bench
python -m integrity.bench.build --raw-dir data/raw/faa --year 2023 --masking M1 --out data/processed/bench
python -m integrity.bench.build --raw-dir data/raw/faa --year 2024 --masking M2 --out data/processed/bench
python -m integrity.bench.build --raw-dir data/raw/faa --year 2024 --masking M1 --out data/processed/bench
```

Options: `--negatives` (default: as many presumed negatives as positives), `--hard-per-positive` (default 2),
`--history-limit` (default 200, the deployed cap; 0 means no cap), `--seed` (default 20261124).
Building 2025 is refused unless `--unlock-test "<reason>"` is given.
The build stops with an error if any masked text still holds a citation, a cited id, an emphasis mark or (M2) a status marker.

## 3. Run stage 1 (no model)

```bash
python -m integrity.bench.run candidates \
  --bench data/processed/bench/bench_2024_M2.jsonl \
  --out integrity/bench/results/candidates_2024_M2.json
```

It prints hit rates per ordering and writes the result file. It needs no model and takes seconds.

## 4. Run stage 2 (the model)

Stage 2 needs a running OpenAI-compatible endpoint. Staging uses `phi4-mini` through Ollama
(see `docs/local-llm-staging.md`). Pull the model first (`ollama pull phi4-mini`).

Time a few pairs first. This writes nothing:

```bash
python -m integrity.bench.run classify \
  --bench data/processed/bench/bench_2024_M2.jsonl \
  --model phi4-mini --base-url http://localhost:11434/v1 \
  --prompt v1 --mode cascade --predictions data/processed/bench/predictions \
  --time-first 20
```

Then the full run:

```bash
python -m integrity.bench.run classify \
  --bench data/processed/bench/bench_2024_M2.jsonl \
  --model phi4-mini --base-url http://localhost:11434/v1 \
  --prompt v1 --mode cascade --predictions data/processed/bench/predictions \
  --out integrity/bench/results/classify_2024_M2_phi4-mini_v1.json
```

- `--prompt` is `v1` (the staging prompt) or `v2-unannounced` (a draft, benchmark only).
- `--mode` is `cascade` (as deployed: a screen, then two votes, five on disagreement) or `legacy` (`--passes` votes, default 5).
- `--limit N` classifies N pairs drawn by seeded shuffle.
- `--api-key-env` names the variable holding the key (default `OPENAI_COMPAT_API_KEY`; a local Ollama needs none).
- A run that stops can be started again with the same command. Finished pairs are kept and skipped.
- A predictions file is tied to its bench, model, endpoint, prompt, mode and pass count. Changing any of them needs a new `--predictions` directory.
- A model failure on one pair is listed under `errors` and retried on the next run.

## What each file holds

| File | Holds |
| --- | --- |
| `bench_<year>_<masking>.jsonl` | One pair per line: the masked new and prior records, `kind` (`positive`, `hard_negative`, `presumed_negative`), label, ranks of the true prior under each ordering, text-overlap features. |
| `bench_<year>_<masking>.manifest.json` | Counts, source file hashes, rejected citations, operator mix, the options used, positives hidden by the history cap, the unlock reason. |
| `presumed_negatives_check_<year>.csv` | 50 presumed negatives, unmasked, with an empty `is_really_a_correction` column for a human to fill in. |
| `candidates_<year>_<masking>.json` | Stage 1. Hit rates at 1, 3, 5 and anywhere with 95% bootstrap intervals, for three orderings (`legacy`, `containment`, `submission_gap`) and three rank sets (`ranks`, `ranks_ignoring_chain`, `ranks_capped`); share of true priors that are not candidates; candidate counts; metadata (file hashes, git commit, dirty flag, seed). |
| `classify_<year>_<masking>_<model>_<prompt>.json` | Stage 2. Two systems, `model` and `cascade_as_deployed`: precision, recall, F1, false-link rate (also split by hard and presumed negatives), confusion, parse-failure rate, seconds and model calls per pair. Intervals are 95% bootstrap. |
| `<bench stem>__<model>__<prompt>__<mode>.jsonl` and `.config.json` | Resumable predictions: ids, labels, timings and tokens, never report text; and the configuration that made them. |
| `test_split_log.jsonl` | One line per opening of the 2025 split: file, model, prompt, reason, git commit, time. |

Stage 2 assumes every pair reaches the model, so stage 1 misses are not counted against recall.
Read stage 2 together with the stage 1 hit rates.

## What is committed and what is not

Committed:

- the code in this folder and its tests (`backend/tests/test_integrity_bench_*.py`);
- the result files in `results/` (`candidates_*.json`, later `classify_*.json`).

Not committed:

- the FAA files (`backend/data/raw/` and `backend/data/processed/` are git-ignored);
- the bench files, manifests, hand-check CSVs and predictions, which sit under `backend/data/processed/bench/`;
- the 2025 FAA file, which is kept outside the repository.

A result file names its bench by SHA-256, so a bench can be rebuilt and checked against it.
The bench is deterministic for a given seed and set of source files.

## Tests

```bash
python -m pytest tests/test_integrity_bench_*.py tests/test_integrity_candidates.py tests/test_integrity_classify.py
```

`test_citation_never_reaches_the_model` fails if "SUPPLEMENTAL REPORT FOR", a cited id or (M2) "WILL BE SUBMITTED"
reaches the model. `check_no_leaks` runs before any model call and raises `LeakageError` on a leaked text.
