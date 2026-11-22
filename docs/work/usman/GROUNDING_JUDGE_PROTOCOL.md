# Offline model-judge protocol

This adds the L4 evaluation instrument. It does not activate a runtime judge,
accept grounding thresholds or replace the two independent human reviews.
Source: `backend/investigation/experiments/grounding_judge.py`.

The frozen review packet contains constructed claims and real report text, not
model-generated prose. Use it for comparing sentence-support judgments after
independent human labels arrive. The separate model-comparison runner already
collects paired generated prose with and without evidence; do not describe this
constructed-pair evaluation as that baseline.

## Measurement boundary

- Explicit installed model name and digest, system/method/packet/prompt hashes,
  temperature zero, seed 1729, context 8192 and prediction cap 700 are saved.
- All 150 original claim/report pairs are judged serially without truncation,
  retries, model installation, automatic model choice or test-year access.
  The longest actual prompt is 4,577 bytes; a 6,000 byte preflight cap leaves context
  headroom. Oversized packets fail before network access or output creation.
- The model sees only the exact claim and single report text/part metadata.
  It cannot see constructed arms, lexical scores, split membership or human labels.
  Source text is marked untrusted. This instruction is not a guarantee against
  model prompt injection; independent human evaluation measures remaining errors.
- Each verdict requires a rationale and exact source quotes for positive/partial
  support. Quote validation makes the record auditable; a quote's presence does
  not establish entailment. Unknown labels, missing quotes, fabricated quotes,
  wrong model identities and malformed responses remain explicit failed records.
- Raw responses and latency are flushed to an append-only journal after each
  call. A fresh output directory is required. An interrupted run's journal is
  preserved; it is not a complete measurement. Complete runs retain all failures.
  Failures never become unsupported labels or disappear from the denominator.
- Human metrics require two complete independent fingerprint-bound label files,
  explicit disagreement adjudication, every judge row and matching saved raw
  verdicts/provenance. Any failed judge record blocks full-set metrics. Fit and
  validation are reported separately; the tool does not choose thresholds.

## Execute on a machine with an existing model

Run from `backend/`; select a real installed model, not the illustrative name:

```bash
python -m investigation.experiments.grounding_judge \
  --packet ../docs/work/usman/grounding_review_v1/packet.json \
  --output /path/to/new-judge-run \
  run --endpoint http://127.0.0.1:11434 --model YOUR_INSTALLED_MODEL
```

Remote endpoints require HTTPS or a loopback SSH tunnel. If authentication is
required, use `--token-env JUDGE_ENDPOINT_TOKEN`; put the value in the environment,
not in a command argument or report. No endpoint or credential is saved in the
manifest. Do not launch a local model on Usman's laptop while investigating its
previous freezes. A remote endpoint must be deliberately selected; this command
does not call the live application or staging model by default.

After the real labels and required adjudications are available:

```bash
python -m investigation.experiments.grounding_judge \
  --packet ../docs/work/usman/grounding_review_v1/packet.json \
  --output /path/to/new-judge-evaluation.json \
  evaluate --results /path/to/new-judge-run/results.json \
  --first /path/to/usman.csv --second /path/to/umar.csv \
  --adjudications /path/to/actual-adjudications.json
```

Omit adjudications only when both independent reviewers agree on every pair.
Compare this result with `grounding_eval.py`'s lexical validation readout using
the same human reference. Do not reuse validation labels to alter judge prompts.
Live borderline-judge integration is a separate reviewed change after accepted
thresholds and actual judge performance justify it. No actual model judgment,
human precision/recall/kappa or deployment acceptance is claimed by tool tests.
