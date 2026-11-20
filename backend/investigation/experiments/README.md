# Investigation decision selection

Run from `backend/` with the ordinary backend development environment. No new
application dependencies, models or graph service are needed for this benchmark.
The compressed projection is separate from Umar's corpus-builder outputs.

```bash
python -m investigation.experiments.download_projection --year 2023 --output data/raw/usman_decision_2023.csv.gz
python -m investigation.experiments.download_projection --year 2024 --output data/raw/usman_decision_2024.csv.gz
python -m investigation.experiments.decision_benchmark --fit-corpus data/raw/usman_decision_2023.csv.gz --selection-corpus data/raw/usman_decision_2024.csv.gz --output /tmp/halite-decision-selection-reproduction --bootstrap 1000
```

Downloads and benchmark outputs refuse overwrite; choose a fresh destination.
Do not delete prior experiments to hide a method change. Original source CSVs or
the contract's processed CSVs can also be supplied if they contain the projection
columns. Download metadata is checked where present. Source-content fingerprints
must match before comparing numerical reproduction: the FAA can revise records.
No 2025 download/evaluation is performed by this command.

`results/decision_selection_2024_v2/` is the executed 406-pair 2023 fit and 389-pair
2024 selection (340 distinct originals), before the question policy. The sample
is all valid explicit same-tail forward-submission correction pairs with a known
named correction part; 22 fit-year and 7 selection-year unknown outcome keys are
excluded and counted. All known multiple corrections are retained. Bootstrap
intervals cluster by original report. See `selection.json` for fingerprints,
search domain, source hash, commit/dirty status, protocol and exclusions; the
small case-score files contain the exact inputs to the mathematics without raw
narratives. They do not contain human sentence labels.

`params/mid_heuristic-v1.json` contains the 2023 fitted T/c. Its presence does not
activate runtime calibration or authorize probability wording. Runtime still
uses the uncalibrated fallback and unconfigured policy; threshold selection,
question-conditioned evaluation and the final held-out run remain separate gates.

The v1 exploratory run had retained only the earliest correction per original.
A protocol audit replaced it before held-out evaluation. The reason and omitted
case counts are preserved in `docs/work/usman/evidence/phase4-protocol-correction.json`.

The unchanged bounded Mid-I ranker is deliberately the baseline here. The result
is an exact part-name outcome-key proxy, not validated fault diagnosis. Weak
coverage/accuracy remain visible in the table; no improvement is invented. The
abstention-off baseline removes both confidence and evidence gates; the tau=0
policy row still enforces at least two evidence records. Empty answer sets have
null accuracy. Selection results cannot be presented as 2025 performance.
