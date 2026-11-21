# Independent grounding review — 150 pairs

Reviewers: **Muhammad Usman Al Haq** and **Muhammad Umar** (chosen by Usman).

Each reviewer opens their own HTML file in a browser:

- `review_usman.html` — Usman's independent copy.
- `review_umar.html` — Umar's independent copy.

The copies contain the same claims and cited reports, in the same frozen order.
No checker predictions, sampling categories, split assignments or suggested labels
appear in the review interface. Do not inspect `packet.json`, checker results or
the other reviewer's work before completing your independent labels.

Read the claim and only the supplied report. Choose:

- **Supported**: the report supports every material assertion in the claim.
- **Partly supported**: some material assertion is supported, but another detail is
  missing, ambiguous or mismatched.
- **Unsupported**: the report does not support the material claim, or contradicts it.

Check named parts, conditions, quantities and negation. A plausible aircraft fact
is not evidence that the supplied report says it. Write a short rationale for each
choice. This task assesses textual support; it does not approve aircraft repairs.

Press **Save label and next** for each pair. Export a **draft JSON** before closing
or taking a break, and import your own draft to resume. Nothing is automatically
saved or sent anywhere. Export the **completed CSV** after all 150 labels. Keep
reviewer identity consistent. Preserve the independent files separately; do not
resolve differences by silently editing either completed file.

After both reviews, calculate agreement on the original labels. Each disagreement
requires an explicit adjudication JSON entry with `label`, `reviewer` and
`rationale`, keyed by pair ID. The evaluation tool refuses incomplete files,
foreign packet fingerprints, duplicate pairs and unresolved disagreements. It
reports observed agreement, Cohen's kappa (or explicitly undefined), confusion
counts and precision/recall. A threshold proposal remains **unaccepted** until
Usman records his operating decision; the safety-template whitelist is empty.

## Method and scope

This is a **constructed calibration sample**, not 150 generated model answers.
Actual FAA narrative sentences are paired with their original report, an earlier
same-part report and an earlier same-JASC/different-part report. These are sampling
categories, not ground-truth labels. Humans decide all labels. Fifty distinct 2024
original reports produce 150 pairs. Negative references must precede the original
submission and fall outside its complete citation chain. The source corpus is the
frozen 2023/2024 selection corpus; no held-out 2025 source is used.

The declared split keeps originals and reference report IDs disjoint: 33 originals
(99 pairs) fit candidate thresholds, 17 originals (51 pairs) provide a separate
validation readout. This small constructed sample does not establish performance
on generated prose, a no-evidence baseline, or the held-out 2025 test. Those require
separate measured runs. The current real calibration tool fits **lexical**
thresholds only; synthetic dense vectors are confined to unit tests.

`packet.json` records source and method hashes, seed, exact texts, split and the
review fingerprint. The blank CSV templates are alternatives to the HTML tool.
No human labels or empirical agreement results are included in this package.

From the repository's `backend` directory, after both human files are returned:

```sh
python -m investigation.experiments.grounding_eval \
  --packet ../docs/work/usman/grounding_review_v1/packet.json \
  --first /path/to/usman-completed.csv \
  --second /path/to/umar-completed.csv \
  --adjudications /path/to/explicit-adjudications.json \
  --output /path/to/new-grounding-proposal.json
```

Omit `--adjudications` only when both files agree on every pair. Preserve all raw
files, rationales and generated results; never replace independent reviews with a
consensus file and then claim independent agreement.
