# Agent guide: Record Integrity (owner: Shahmeer Atif)

You are the coding agent for Shahmeer Atif on the Halite final-year project. Shahmeer owns vertical V2,
**Record Integrity**, from database to screen to measured result. Read `AGENTS.md` and
`docs/plan/CONTRACTS.md` first. This guide tells you how the current code works, what is wrong with it,
what to build and how each piece is accepted. Work on one work package at a time, the one Shahmeer names.

**Frontend paths changed on 24 November.** Pages now live in `frontend/src/features/<name>/` and register through
a manifest; see `docs/plan/CONTRACTS.md` section 2 and `frontend/src/app/README.md`. Frontend file names below predate that.

Facts and line numbers refer to `origin/main` at `ac5aa66`. If the code has moved, re-locate the function by
name and tell Shahmeer what changed.

---

## 1. Mission

Decide which reports are still valid. When a new report arrives, find the earlier report it corrects, completes
or contradicts, attach a confidence that means what it says, link automatically only when the risk is bounded,
and send the rest to a person.

By the FYP-I Final (December 2026) this vertical must deliver:

1. Exact linking of announced corrections, and review decisions that really change the graph.
2. A citation-masked benchmark of the local model on 2025 data, replacing the old F1 of 0.762.
3. A confidence fitted to data, with a risk-bounded policy, and the staging queue re-triaged from 494.
4. An integrity dashboard and a paginated review workbench.
5. The frontend preparation pull request, which unblocks both teammates and comes before everything else here.

The question this vertical answers, which makes proposal section 11.9 precise:

> With a 3.8B local model, how much of the correction workload can be decided automatically at a stated
> false-link rate, and does a fitted confidence beat the hand-weighted score?

The panel will ask Shahmeer to explain, justify against an alternative, predict what breaks and modify any of this.
Keep the code small and named after the concepts.

---

## 2. How the current code works

### 2.1 The engine (`backend/services/conflict_engine.py`, 759 lines)

| Function | Line | What it does |
| --- | ---: | --- |
| `find_candidate_pairs` | 105 | Earlier reports on the same aircraft, scored and capped at 25. |
| `classify_conflict` | 271 | Asks the model for a label and a one-sentence rationale. Votes: 5 in legacy mode, 2 then 3 more on disagreement in cascade mode. File cache keyed `{new_id}_{prior_id}_{model}`. |
| `_parse_classification` | 389 | Parses the JSON. A parse failure or invalid label becomes `no_conflict` with `parse_failed`. |
| `adjudicate` | 416 | Builds evidence strings, computes `days_between`, picks an action. |
| `score_confidence` | 495 | Sums the weights of true signals and clamps to 0..1. |
| `route` | 513 | `needs_review`, `no_action` or `auto_accepted`. |
| `process_record` | 529 | Orchestrates all of the above and writes to the graph. |

Candidate selection, exactly as coded (lines 152 to 232):

- History is `graph_repo.list_asset_history(asset_id, limit=200)`, ascending by occurrence date.
- A prior is skipped if its `occurred_at` is later than the target's. On the same day it is skipped when its raw
  `submitted_at` string is greater than or equal to the target's.
- `PAIR_WEIGHTS` (line 34): same part name 3, same JASC code 2, same location 1, occurrence dates within 30 days 1.
  A prior is a candidate only if its score is above 0.
- Order: score descending, occurrence date descending, record ID ascending. In cascade mode the list is then re-sorted
  by text containment.
- **Only `candidates[0]` goes further** (line 624).

The screen (`backend/services/conflict_screen.py`): `meaningful_tokens` strips the citation phrase, boilerplate and
stopwords; `text_overlap_features` returns `containment` (shared tokens over the prior's tokens), `jaccard`,
three equality flags and

```
screen_score = min(1, max(containment, jaccard) + 0.30 * same_part + 0.20 * same_jasc + 0.10 * same_location)
```

In cascade mode a top candidate with `screen_score < 0.79` (`CASCADE_SCREEN_THRESHOLD`, line 74) gets a deterministic
`no_conflict` or `scope_disjoint` without a model call.

The model prompt (lines 82 to 98 and 306 to 311) sends the new and prior `occurred_at` and the first 800 characters
of each raw text. Labels: `no_conflict`, `scope_disjoint`, `supersedes`, `partial_supersedes`, `contradicts`.
The prompt defines `supersedes` as "new record explicitly updates or closes the prior record".

Confidence signals and weights (lines 44 to 60, 675 to 697):

| Signal | With citation phrase | Without |
| --- | ---: | ---: |
| `explicit_supersession_language` | 0.40 | 0 |
| `classification_supersedes` (times vote agreement in cascade) | 0.20 | 0.35 |
| `recency_advantage` (`days_between > 0`) | 0.15 | 0.25 |
| `authority_advantage` | 0.10 | 0.15 |
| `part_agreement` (same part and same JASC) | 0.10 | 0.15 |
| `proximity_bonus` (`0 < days_between <= 30`) | 0.05 | 0.10 |

Routing (lines 513 to 526, 704 to 705): parse failure, `contradicts` and `partial_supersedes` go to review.
`no_conflict` and `scope_disjoint` need no action. `supersedes` auto-accepts when confidence is at least
`MAINT_CONFIDENCE_THRESHOLD` (0.50). A cascade vote split forces review.

Persistence (lines 708 to 744): on auto-accept the engine calls `graph_repo.link_record_supersedes(...)` and sets the
prior's `status` to `superseded`. It then overwrites the target's `status`, `analysis_state`, `confidence` and the
`analysis_*` fields.

### 2.2 Routes (`backend/api/routes/maintenance.py`, 617 lines)

`/ingest`, `/ingest/upload`, `/records` (list, get one, process one), `/assets`, `/assets/{id}/history`,
`/review-queue`, `/review-queue/{id}/accept`, `/review-queue/{id}/reject`, `/analysis/status`, `/analysis/run`,
`/corrections`. **All existing request and response shapes are frozen.** Add fields; never remove or rename.

### 2.3 Staging today

2,079 reports. After the 16 November backfill with `phi4-mini` in cascade mode: 1,585 scored, 494 needs review,
0 reviewed. Methods: 1,043 screen, 801 model, 235 escalated. The run took about 12 hours 50 minutes.

---

## 3. Defects to fix (verified in code)

| ID | Defect | Evidence |
| --- | --- | --- |
| D1 | **Fixed in `6833222` (parser in `cdd6077`).** **The cited ID is never parsed.** The engine checks only that the phrase "SUPPLEMENTAL REPORT FOR" is in the new text, then links to its top candidate. The repo's own evidence puts the top candidate at the cited report in 94 of 141 cases (`gt_results.csv`), 124 of 141 (legacy order) or 136 of 141 (containment first). | Lines 457, 676; `docs/mid1/21_analysis_cascade_evidence.md`. |
| D2 | **Two confidence signals are dead on real corrections.** `days_between` comes from `occurred_at` (line 439). All 981 FAA correction pairs in 2023 to 2025 share the occurrence date, so `recency_advantage` and `proximity_bonus` are false on every true correction and true only on other pairs. | Lines 439, 680, 693. |
| D3 | **One signal is always true.** `source_authority` returns 5 for every record, so `authority_advantage` always fires. | `domains/maintenance.py:54-56`. |
| D4 | **The threshold does nothing in legacy mode.** Without a citation, a `supersedes` label alone scores 0.35 + 0.15 = 0.50 and auto-accepts. This also explains the old sweep, where recall fell to 0 at a threshold of 0.70: a true pair can reach at most 0.65. | Lines 53 to 60. |
| D5 | **Fixed in `52a5fa6`.** **Review decisions do not change the graph.** Accept sets `status = "accepted"` and creates no `SUPERSEDES` link. Reject removes none. | `api/routes/maintenance.py:513-607`. |
| D6 | **Fixed in `6833222`.** **Re-processing overwrites decisions.** `process_record` rewrites `status` unconditionally, including `superseded`, `accepted` and `rejected`. | Lines 724 to 726. |
| D7 | **Fixed in `52a5fa6` (stored prior and route) and `2e39946` (review screen).** **The proposed prior is not stored.** The review screen calls `GET /maintenance/records/{id}`, which re-runs the engine in dry-run mode with live model calls. A reviewer can be shown a different pair from the one that was scored, and each click costs model time on a CPU. | `api/routes/maintenance.py:244-267`; `frontend/src/pages/ReviewQueue.jsx:135`. |
| D8 | **Only the first candidate is classified.** | Line 624. |
| D9 | **The old evaluation was circular.** The phrase that defines the ground truth is inside the text the classifier reads (the prompt sends raw text). The 0.79 screen threshold was tuned on the same 141 pairs. The harness that produced `gt_results.csv` is not in the repo. | `docs/evaluation_results.md`, `scripts/evaluate_conflict_detection.py:107`. |
| D10 | Smaller items: `history_size` is capped at 50 (line 580); the candidate cap reads `os.environ`, not `settings`; `scripts/backfill_conflict_scores.py:75` hardcodes Groq; `scripts/c4_self_consistency.py` is broken; the classification cache is rewritten whole on every call with no lock; `GET /review-queue` is unpaginated. | Audit of 20 November. |

---

## 4. Target design

### 4.1 Package layout

```
backend/integrity/
  __init__.py
  citations.py     # parse cited IDs, open and closed markers
  timeutil.py      # parse SubmissionDate, gaps in days
  candidates.py    # candidate retrieval (moved from the engine), orderings
  features.py      # one feature vector per (new, prior) pair
  classify.py      # model votes; wraps today's classify_conflict; masked prompt
  calibrate.py     # fit offline, predict in pure Python
  policy.py        # accept / dismiss / review
  apply.py         # every graph write: link, unlink, never override a human
  validity.py      # contract 4.1
  cases.py         # FaultCase grouping (Should tier)
  prompts.py       # PROMPT_VERSION
  bench/
    build.py       # masked benchmark sets per split
    run.py         # CLI
    results/       # small committed JSON
backend/graph/repo/integrity.py
backend/graph/migrations/002_integrity_*.py
backend/api/routes/integrity.py
backend/db/models/integrity.py
frontend/src/features/integrity/, features/intake/, features/assets/
```

Usman wrote the engine and has handed it to you. Read it end to end before changing it, and ask him when a choice in
it is unclear. Keep `services/conflict_engine.py` as a thin facade: `process_record` keeps its signature and return keys and
delegates to `integrity`. Existing tests keep passing while you move logic out.

### 4.2 Two kinds of time (`timeutil.py`)

- Occurrence time: `occurred_at`, from `DifficultyDate`, a date.
- Knowledge time: `submitted_at`, from `SubmissionDate`, for example `2025-01-02T09:45:26.140-05:00`.
- Parse `submitted_at` into a timezone-aware datetime. Never compare the raw strings; offsets change with daylight saving.
- `submission_gap_days(new, prior)` is a float. `occurrence_gap_days` is an integer.
- A prior is eligible when `prior.submitted < new.submitted`. Fall back to occurrence date only when a submission time is missing.

Measured on the 981 pairs: the submission gap has median 5.1 days, 10th percentile 1.0, 90th percentile 24.0,
maximum 203.3, and is never negative. The occurrence gap is always 0.

### 4.3 Announced corrections: rule R1 (`citations.py`, `apply.py`)

```
CITATION_RE    = SUPPLEMENTAL\s+REPORT\s+FOR\s*\(?\s*([A-Z0-9]{6,})\s*\)?      (case-insensitive)
OPEN_MARKER_RE = SUPPLEMENTAL\s+REPORT\s+WILL\s+BE\s+SUBMITTED
```

`parse_citations(text) -> list[str]` returns every cited ID. Then, for a new report `n`:

1. For each cited ID `c`: if `c` exists in the graph, is not `n`, sits on the same aircraft, and was submitted no later
   than `n`, create `(n)-[:SUPERSEDES {method: "explicit_citation", confidence: 1.0, scope: "supersedes"}]->(c)`.
   No model call.
2. If `c` is not in the graph, store it in `n.cited_record_ids`, set no link, and do not queue it for review.
   The prior simply is not in our corpus.
3. Store `cited_record_ids` on every report that cites.

Umar's `backend/common/faa_text.py` will hold the same regexes. Until it lands, define them in `citations.py`.
Import his once it exists.

### 4.4 Unannounced corrections: the research problem

A report can correct an earlier one without saying so. That case needs the model and the features. We cannot label it
by hand at scale, so we manufacture labelled data from the announced pairs by hiding the announcement.

**The citation-masked benchmark (`bench/build.py`).**

- Positives: every pair in `correction_pairs.csv` for the split. Mask the newer report's text.
- Masking M1: remove the citation phrase and the ID. Masking M2: also remove `(OPEN)`, `(CLOSED)` and the
  "will be submitted" sentence from both reports. Build both.
- Hard negatives: for each masked newer report, its other candidates on the same aircraft, which are not the cited report.
- Presumed negatives: sample reports with no citation and at least one candidate, paired with their top candidate.
  Mark them `presumed`. Export 50 of them to a CSV for Shahmeer to check by hand, so the label noise can be estimated.
- The prompt must receive the **masked** text. Add a test that fails if the string "SUPPLEMENTAL REPORT FOR" reaches the model.
- Splits follow the contracts: 2023 to fit, 2024 to choose, 2025 to report.

**Stop and ask:** which masking is primary. The recommendation is M2, the stricter one. Shahmeer decides and writes why.

**Stage 1, candidates.** Measure on masked pairs whether the true prior is the top candidate, and whether it is in the
top 3, under three orderings: legacy, containment first, and submission gap ascending. Then decide how many candidates
to classify. Classifying the top 3 triples the model cost; the measurement must justify it.

**Stage 2, classification.** A predicted positive is a label of `supersedes` or `partial_supersedes`. Report on masked 2025:
precision, recall, F1, false-link rate (false positives over all negatives), parse failures, seconds per report and model
calls per report, each with a 95% bootstrap interval. Use `phi4-mini` through the OpenAI-compatible path so the number
describes staging. Run it on Shahmeer's M4 through Ollama; Umar's `scripts/benchmark_local_llm_gt.py` and the staging
setup in `docs/local-llm-staging.md` are the starting point. Time the first 20 pairs before launching the full run.

The prompt's definition of `supersedes` says "explicitly updates or closes". That wording suits announced corrections.
Draft a second prompt version for unannounced ones, bump `PROMPT_VERSION`, and compare both on 2024.
**Stop and ask** before changing the prompt used on staging.

### 4.5 Features (`features.py`)

One row per (new, prior) pair. Every feature must be computable without the citation.

| Feature | Definition |
| --- | --- |
| `containment` | Shared meaningful tokens over the prior's meaningful tokens (as in `conflict_screen`) |
| `jaccard` | Shared over union |
| `shared_tokens_log` | `log1p` of the shared token count |
| `same_part`, `same_jasc`, `same_ata_chapter`, `same_location` | Equality flags; chapter is the first two digits of the JASC code |
| `prior_part_unknown`, `new_part_unknown` | Part is `UNKNOWN`, `NONE` or blank |
| `submission_gap_log` | `log1p` of the submission gap in days |
| `occurrence_gap_zero` | Occurrence dates are equal |
| `prior_open_marker` | The prior carries the "will be submitted" sentence (only under masking M1; dropped under M2) |
| `new_closure_words` | The new text contains closure wording such as FOUND, REPLACED, REMOVED AND REPLACED, RESECURED, OPS CHECK GOOD |
| `candidate_rank` | Position of the prior in the candidate list |
| `n_candidates_log` | `log1p` of the candidate count |
| `llm_supersedes`, `llm_partial`, `llm_contradicts`, `llm_scope_disjoint`, `llm_no_conflict` | One-hot of the model label |
| `llm_vote_agreement` | Share of votes for the winning label |
| `llm_parse_failed` | The reply could not be parsed |

`recency_advantage`, `proximity_bonus` and `authority_advantage` are gone. The closure word list is Shahmeer's to write
after reading reports; ship it as a short list he edits.

### 4.6 Calibration (`calibrate.py`)

- Target: `y = 1` when the prior is the report the new one supersedes.
- Model: L2-regularised logistic regression. Standardise continuous features with statistics from the fit split.
  Choose the regularisation strength on 2024 by log loss. Try isotonic regression on top of the logistic score as the alternative.
- Training runs offline and may use scikit-learn as a development dependency.
- Serving uses no scikit-learn: `p = sigmoid(intercept + sum(coef_i * (x_i - mean_i) / scale_i))` in pure Python.
- Persist the model as JSON and as a row in `calibration_models`:
  `{version, feature_names, mean, scale, coef, intercept, trained_on, selected_on, metrics, masking, prompt_version}`.
- Report on 2025: expected calibration error with 10 equal-width bins, Brier score, area under the precision-recall curve,
  and the reliability diagram data. Report the same for the hand-weighted `score_confidence` on the same pairs.

**Ablation, required.** Fit three models: features only (no `llm_*`), model label only, and both. If "both" does not beat
"features only" on 2024 by more than the bootstrap noise, say so. **Stop and ask** whether the model stays in this step.
Dropping it would remove about 1,000 model calls from a staging run, which is a strong result, not a failure.

### 4.7 Policy (`policy.py`)

```
p >= t_high             -> auto_accept   (create the link with method "model")
p <= t_low              -> no_action
otherwise               -> needs_review
model label contradicts -> needs_review, always
parse failure           -> needs_review, always
```

- Choose `t_high` on 2024 as the lowest threshold whose false-link rate among accepted pairs stays at or below `alpha`.
  Report the empirical rate and a one-sided 95% Clopper-Pearson upper bound. With few accepted pairs the bound will be wide; say so.
- Choose `t_low` on 2024 so that the share of true corrections among dismissed pairs stays at or below `beta`.
- Report on 2025: coverage (share decided automatically), review load, realised false-link rate, each with an interval,
  and the full risk-coverage curve.

**Stop and ask:** `alpha` and `beta`. The plan proposes `alpha = 0.02`. A false link hides a valid report from
diagnosis, so Shahmeer must be able to defend the number.

### 4.8 Graph writes and review semantics (`apply.py`, `graph/repo/integrity.py`)

Every write goes through `apply.py`. Rules:

1. Store the proposed prior at analysis time: `proposed_prior_id`, `integrity_p`, `integrity_model_version`.
   The review screen reads these. It never re-runs the engine.
2. `SUPERSEDES` gains `method`, `model_version`, `decided_by`, `decided_at` (contract 4.1).
3. **Accept** of a proposed supersession creates the link with `method = "human"` and the reviewer's identity,
   writes a `review_decisions` row and an audit event, and sets `status = "accepted"`.
4. **Reject** deletes a `model` link between the pair if one exists, creates `(new)-[:NOT_SUPERSEDES {by, at}]->(prior)`
   so the pair is never proposed again, writes the row and the audit event, and sets `status = "rejected"`.
5. A report with `analysis_state == "reviewed"` is never re-processed unless an admin passes `force=true`.
6. Validity is read from links (`validity.py`). Keep writing `status = "superseded"` for backward compatibility; never read it.
7. Every automatic status change writes an audit event too (FR-27).
8. Backfill for staging: a migration recomputes `proposed_prior_id` deterministically (no model call) for records
   already analysed. `--dry-run` prints counts. Umar runs it after a backup.

`review_decisions` columns: `id, record_id, prior_record_id, decision, note, reviewer_id, reviewer_role, model_p,
model_version, created_at`.

### 4.9 Re-triage of staging

`python -m integrity.retriage --dry-run` prints, before and after: explicit links, auto-accepted, no action, needs review.
It applies R1 first, then the calibrated policy, and never touches a reviewed record. The before and after queue sizes go
into the report and the dashboard.

### 4.10 Endpoints

| Method and path | Auth | Returns |
| --- | --- | --- |
| `GET /api/integrity/summary` | any user | Summary shape, contract 4.6 |
| `GET /api/integrity/calibration` | any user | Latest model: reliability bins, calibration error, Brier, thresholds, coverage, the old score's bins for comparison |
| `GET /api/integrity/queue?cursor=&limit=&sort=priority` | any user | Paginated queue. Each item carries the stored prior, `p`, label, rationale and the changed fields. Priority is `abs(p - 0.5)` ascending, then newest. |
| `GET /api/integrity/cases?state=open` | any user | Fault cases (Should tier) |
| `POST /api/maintenance/assets` | supervisor or admin | Register an asset `{tail_number, make, model, serial_number}`; 409 if it exists (FR-05) |
| `GET /api/integrity/insights/trends`, `/repeat-faults` | any user | Fleet insights (Should tier) |
| `POST /api/integrity/intake/parse`, `/intake/confirm` | any user | Free-text and PDF intake (Should tier) |

The existing `/api/maintenance/review-queue`, `/accept` and `/reject` keep their shapes. `GET /maintenance/records/{id}`
keeps working but the new workbench does not call it.

Tighten roles while you are here: server-path ingest and the caller-supplied threshold on `POST /maintenance/records`
become admin only. CSV upload stays open to technicians. Audit ingest and analysis runs.

### 4.11 Frontend

- `features/integrity/ReviewWorkbench`: paginated queue sorted by priority; the new report beside the stored prior with
  changed fields highlighted (part X to part Y, JASC, location); `p`, label, rationale and method; accept and reject that
  update only after the server confirms; reviewer name and time on decided items; keyboard shortcuts.
- `features/integrity/IntegrityDashboard`: coverage counters, method mix (rule, model, human), the reliability diagram
  with the old score overlaid, the risk-coverage curve with the policy thresholds marked, queue size before and after.
- `features/assets`: the existing pages, plus a "Register aircraft" form.
- Remove the hard-coded "recall 0.66" at `ReviewQueue.jsx:527`. Map every label in `StatusChip`.
- Use the primitives in `src/components/ui/` and Recharts. Every page needs loading, empty and error states.

### 4.12 Should tier, in this order

1. **Fleet insights page** (FR-32 to 35). Fault counts by month and by ATA chapter. Repeat faults: the same part on the
   same aircraft at least 3 times within 365 days. Correction counts. Every figure is labelled "descriptive, not a prediction".
2. **Free-text and PDF intake** (FR-09, 10, 12). Extract the twelve fields as JSON with the local model. `pypdf` is already
   a dependency for text PDFs. Validate each field (tail pattern, date parse, four-digit JASC present in the corpus,
   part name seen before). Return a status per field: `extracted`, `missing` or `ambiguous`. The user confirms in a form.
   On confirm, create the record and run R1 and the policy at once. Evaluate by round trip: render 100 real records to
   text, parse them back, and report field-level accuracy.
3. **Fault cases.** Group a report with its corrections by following citation links. A case is `open` when a report
   carries the "will be submitted" sentence and no later report cites it, `closed` otherwise.
4. **Reviewer agreement tooling.** Export 60 queue items to CSV for two reviewers, import their labels, compute Cohen's kappa.

### 4.13 Frontend shell and design system (shared duty)

You also own the application shell: `src/app/`, `src/components/ui/`, `src/api/http.js`, `index.css`, the Tailwind
config, `App.jsx`, `Sidebar.jsx`, and the frozen `features/auth/` and `features/admin/` pages (login, invite, team,
settings). Other owners use the primitives and ask you for changes. In December the auth and admin pages get bug fixes
only: add confirmations to role change, deactivate and revoke in `TeamAccess`, and stop Settings flashing
"Backend not reachable" while loading.

The frontend preparation pull request is specified in contracts section 3.2. It has priority over every other work
package, because Umar and Usman cannot add pages until it merges. Time-box it to 24 November.

### 4.14 What the panel must see

The research is graded in a 15-minute presentation. Each result below must be visible on a product page, read from the
latest `calibration_models` row or a committed results file, never typed by hand.

| Research result | Screen |
| --- | --- |
| The fitted confidence is more honest than the hand-weighted score | Integrity dashboard: reliability diagram with both curves against the diagonal, and the calibration error of each |
| A stated error limit cuts the review queue | Risk-coverage curve with a threshold slider that updates the queue size and expected error; a before and after counter that starts at 494 |
| A correction changes the part | Review workbench: the two reports side by side, changed fields highlighted; after an accept the link appears on the aircraft history and graph without a reload |
| Announced corrections link by rule | Intake or ingest: a pasted report that cites an ID shows "linked to <id> by citation" at once |

You own the shared look. Build the primitives in `src/components/ui/` first, with a chart wrapper that fixes colours,
interval whiskers and the sample-size caption, so the other two owners get consistent charts without design work.

Follow the presentation standard in contracts section 11: shared primitives, one chart library, sample size and data
year on every chart, no hand-typed numbers, loading, empty and error states, dark and light themes at 1280 pixels wide.

---

## 5. Work packages

| ID | Tier | Work | Accepted when |
| --- | --- | --- | --- |
| WP-A0 | Must | Frontend preparation pull request (contracts section 3.2). Do this first. | All existing tests pass; `App.jsx` and `Sidebar.jsx` render from the registry; the dead files are gone. |
| WP-A1 | Must (done, commits `cdd6077` to `699e945`) | `citations.py`, `timeutil.py`, rule R1, `proposed_prior_id`, review semantics, the re-processing guard, audit events, `validity.py`. | Tests: a cited ID links to the cited report even when it is not the top candidate; accept creates a link; reject removes it and blocks re-proposal; a reviewed record survives re-processing; one audit row per status change. |
| WP-A2 | Must | `bench/build.py`, `bench/run.py`, candidate hit rates, the `phi4-mini` benchmark on masked 2024 and then 2025. | Results JSON committed; a test proves the citation never reaches the prompt. |
| WP-A3 | Must | `features.py`, `calibrate.py`, `policy.py`, the three-way ablation, `retriage`. | Calibration and risk-coverage results on 2025 committed; dry-run output of the re-triage shown to Shahmeer. |
| WP-A4 | Must | Integrity endpoints, tables, dashboard, workbench, asset registration. | Component and contract tests; the workbench opens an item with no model call. |
| WP-A5 | Should | Fleet insights. | Page and endpoint tests. |
| WP-A6 | Should | Intake. | Round-trip accuracy reported. |
| WP-A7 | Should | Fault cases and the open-cases list. | Built by an idempotent migration. |
| WP-A8 | Should | Reviewer agreement tooling. | Kappa computed from two label files. |

If the three-year corpus files are not ready when you start WP-A2, run on the existing 2025 files
(`sdr_poc_corpus.csv`, `ground_truth_pairs.csv`) and re-run later. Do not wait.

---

## 6. Stop and ask Shahmeer

1. Primary masking (M1 or M2).
2. `alpha` and `beta`.
3. Whether the model stays in the classification step after the ablation.
4. Any prompt change on staging.
5. The closure word list.
6. Anything that touches staging, including the re-triage.
7. Anything in the frontend preparation pull request that changes behaviour.
8. Any new dependency.

Things only Shahmeer does, which you support with tooling but never write for him:

- The one-page protocol note, written before WP-A2.
- Checking the 50 presumed negatives by hand.
- Adjudicating 60 queue items while a teammate does the same 60 blind.
- Reading 30 model errors and saying what a 3.8B model gets wrong on aviation prose.
- The report sections: integrity design and rationale, masked protocol, benchmark and calibration results, error analysis,
  FYP-2 plan.
- Editing the final report as a whole.

---

## 7. Do not

- Evaluate with the citation visible to the model, or reuse the 0.762 figure as current evidence.
- Tune `alpha`, thresholds, the screen threshold or the prompt on 2025.
- Write a link from anywhere except `apply.py`.
- Overwrite a human decision.
- Edit `backend/retrieval/`, `backend/investigation/`, `api/routes/diagnostics.py`, the shared backend registration files
  (Usman is their steward) or frontend features you do not own.
- Run anything against staging yourself.

---

## 8. Report back after each work package

1. What you built, by file.
2. The acceptance evidence: test names, command output, the results file path.
3. Anything in this guide that turned out to be wrong.
4. Knowledge-bank files you updated and any decision record you added.
5. A two-line AI-assistance note for the pull request.

---

## 9. Reading for Shahmeer

- Guo, Pleiss, Sun and Weinberger (2017), *On Calibration of Modern Neural Networks*.
- Platt (1999), *Probabilistic Outputs for Support Vector Machines and Comparisons to Regularized Likelihood Methods*.
- Zadrozny and Elkan (2002), *Transforming Classifier Scores into Accurate Multiclass Probability Estimates*.
- Geifman and El-Yaniv (2017), *Selective Classification for Deep Neural Networks*.
- Wang et al. (2022), *Self-Consistency Improves Chain of Thought Reasoning in Language Models*.
- Settles (2009), *Active Learning Literature Survey*.
- Cohen (1960), *A Coefficient of Agreement for Nominal Scales*.
