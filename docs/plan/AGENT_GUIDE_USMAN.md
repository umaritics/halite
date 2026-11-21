# Agent guide: Investigation Sessions (owner: Muhammad Usman Al Haq)

You are the coding agent for Muhammad Usman Al Haq on the Halite final-year project. Usman owns vertical V3,
**Investigation Sessions**, from database to screen to measured result. Read `AGENTS.md` and
`docs/plan/CONTRACTS.md` first. This guide tells you how the current code works, what is wrong with it,
what to build and how each piece is accepted. Work on one work package at a time, the one Usman names.

Facts and line numbers refer to `origin/main` at `ac5aa66`. If the code has moved, re-locate the function by
name and tell Usman what changed.

---

## Current implementation evidence

Original code-map line numbers below are the baseline snapshot. Foundation/adapter
work is in PR #27, sessions/degraded/CI in #28, feature UI in #29 and the separately
authorized shared integration in #30. All have passed hosted checks; owner review,
merge and staging remain separate gates. The user explicitly authorized an
AI-assisted design note on his behalf, now in
`docs/fyp1-final/DECISION_LAYER_DESIGN.md` before WP-S4 code.

The decision-core branch adds tested beliefs/policy, exact stored beliefs/entropy,
a ranker boundary and real 2023-fit/2024-selection tooling. Runtime beliefs remain
uncalibrated and policy unconfigured pending measured selection. No 2025 result,
manual label, owner review or completed full mission is implied. See
`docs/work/usman/ACCEPTANCE_MATRIX.md` and `knowledge/context/modules/investigation_decisions.md`.

## 1. Mission

Given ranked hypotheses and their evidence, decide what to tell the technician: commit to an answer, ask one more
question, or say the evidence is insufficient. Then explain in sentences that each follow from a cited report.

By the FYP-I Final (December 2026) this vertical must deliver:

1. Sessions stored on the server, with history, resume, and a recorded outcome when a session is closed.
2. A decision rule (answer, ask or abstain) on top of calibrated beliefs.
3. Follow-up questions chosen by expected information gain, with an experiment that shows whether they help.
4. A check on every sentence of an explanation.
5. A model adapter that works for prose on the local model, and a mode that still answers when the model is down.
6. The home dashboard.
7. The backend preparation pull request and CI quality, which are your shared duties.

The research questions you serve:

- RQ4: can uncertainty-aware abstention reduce unsupported diagnostic suggestions?
- FR-20 made measurable: do selected questions improve the ranking more than arbitrary ones?
- RQ5 (training) in FYP-II, built on the same session and question machinery.

The panel will ask Usman to explain, justify against an alternative, predict what breaks and modify any of this.
You built the Copilot backend and the diagnostics workspace, so you know this code. What is new is the decision
layer and its experiment. Keep both visible in the code: the maths lives in small pure functions with tests, not inside route handlers or React components.

---

## 2. How the current code works

### 2.1 Backend (`backend/api/routes/diagnostics.py`, 749 lines)

| Piece | Line | What it does |
| --- | ---: | --- |
| `DiagnoseRequest`, `CaseState`, `CopilotTurnRequest` | 55 to 82 | Request models. `CaseState` has `symptoms`, `observations`, `checks_done`, `ruled_out`, `open_questions`. |
| `_cache_path`, `_cache_key`, `_load_cache`, `_save_cache` | 93 to 123 | A JSON file cache for diagnose, keyed by `sha256(asset, normalised symptom, model)[:16]`. Never invalidated when the graph changes. |
| `_build_prompt` | 125 | The one-shot diagnose prompt: top 5 ranked parts, 5 history rows, 5 fleet rows. The model must return `{"explanation", "rare_cases", "warnings"}`. |
| `_extract_case_facts`, `_merge_case_state` | 206, 241 | Model call 1 of a Copilot turn: extract new facts as JSON; on failure the raw message becomes a symptom. Each list is capped at 30. |
| `_collect_evidence`, `_select_report_records` | 265, 296 | Build the evidence set; pick records for report-style questions by explicit ID or by year and keyword. |
| `_limit_to_one_question` | 333 | Replaces every question mark after the first with a full stop. |
| `diagnose` | 387 | `POST /api/maintenance/diagnose`. Returns 503 when the model is not live (lines 410, 445, 460). |
| `copilot_turn` | 528 | `POST /api/maintenance/copilot/turn`. Stateless: `session_id` is echoed or freshly made, and nothing is stored. |
| `maint_chat` | 682 | `POST /api/maintenance/chat`. Older endpoint; the frontend client still exposes it. |

A Copilot turn today: extract facts, merge the case state, build context from symptoms and observations minus ruled-out
terms, rank with `rank_copilot_checks`, compute `ranking_delta` against the previous state (a second fleet scan),
then model call 2 writes the reply. The reply prompt (about line 607) says "Ask at most ONE clarifying question, only
when key information is missing". The question is whatever the model writes. After the reply, citations are validated
and any valid ID that was not in the evidence set is marked `[UNVERIFIED:ID]`. A model failure returns HTTP 200 with
`reply: null` and `llm_status: "unavailable"`.

Response of a turn: `session_id, reply, case_state, ranked_checks, ranking_delta {moved_up, moved_down, new, dropped,
newly_cited_records}, evidence (up to 20), citation_validation, llm_status, warnings`. **These fields are frozen.** Add; never rename.

`services/citation_validation.py`: `_RECORD_ID_RE = \b([A-Z]{2,6}\d{6,})\b`; `validate_citations(text, graph_repo)` looks
each ID up in the whole graph and rewrites unknown ones as `[UNVERIFIED:ID]`. It checks existence, nothing more.

`services/groq_service.py` (224 lines): `chat` (line 52), `_chat_openai_compatible` (55), `chat_with_usage` (100),
`extract_json` (168), `extract_json_with_usage` (175). `LLM_PROVIDER=groq` uses the Groq SDK; `openai_compatible`
posts to `{OPENAI_COMPAT_BASE_URL}/chat/completions`, which is how staging reaches Ollama. Temperature 0.3.
The demo responses in `_demo_response` are canned software-domain text and must never reach a maintenance screen.

### 2.2 Frontend

- `frontend/src/pages/Diagnostics.jsx` (1,581 lines, eight components): `QuickDiagnose` 28 to 522, session helpers
  524 to 557, `InvestigationUpdates` 559 to 747, `RankingItem` 806, `LiveRankingPanel` 876 to 1075, `TurnSnapshot` 1077,
  `Copilot` 1144 to 1557, tab wrapper 1559.
- `sendTurn` (line 1262) posts `{session_id?, asset_id?, message, case_state}`. The case state lives in React state and
  is replaced by the server's copy each turn. "Mark done" and "Rule out" append to it and send a synthetic turn.
- Persistence is `localStorage` only: `halite-diagnostic-active-workspace` (auto-saved, versioned, 7-day expiry, in
  `utils/diagnosticWorkspace.js`) and `halite-diagnostic-copilot-sessions` (manual saves, unbounded).
- The only thin-evidence handling is `insufficientEvidence = rankedChecks.length === 0 && evidence.length === 0` (line 92).
- `components/DiagnosticEvidenceInspector.jsx` (475 lines) groups a check's records by aircraft, component and condition.
- `api/client.js` (185 lines): axios instance with an in-memory JWT, one single-flight refresh on 401, no timeout.

---

## 3. Defects to fix (verified in code)

| ID | Defect | Evidence |
| --- | --- | --- |
| D1 | **Sessions are not really sessions.** They live in the browser, are not tied to a user, and are not cleared at logout, so the next person on that browser sees them. | `utils/diagnosticWorkspace.js`; `context/AuthContext.jsx` touches only `sessionStorage`. |
| D2 | **The local-model path forces JSON on every call.** `_chat_openai_compatible` always sends `response_format: {"type": "json_object"}`. Prose replies (Copilot reply, chat) come back as JSON objects or fail. The "empty explanation on staging" defect from the mid report is still open. | `services/groq_service.py:70`. |
| D3 | **No model means no answer.** `diagnose` returns 503, although ranking and evidence are deterministic. | `api/routes/diagnostics.py:410, 445, 460`. |
| D4 | **The follow-up question has no logic.** The model writes it. `open_questions` is carried in the case state and never rendered. | Reply prompt near line 607; `Diagnostics.jsx:530` is the field's only mention in the page. |
| D5 | **There is no abstention rule.** The interface says "insufficient evidence" only when there are no ranked checks and no evidence at all. | `Diagnostics.jsx:92`. |
| D6 | **Diagnose citations are checked for existence only.** An ID that exists anywhere in the graph counts as verified, even if it was never in the evidence shown. Nothing checks that a sentence follows from its citation. | `services/citation_validation.py:30`; the allow-list exists only in the Copilot path. |
| D7 | **The diagnose cache is never invalidated.** A stale entry has served an empty explanation on staging. | Lines 93 to 123; `docs/mid1/logs/staging-measurements.txt`. |
| D8 | Demo hazards on your pages: two stacked "Diagnostics" headers in Quick diagnose (113 to 123 inside 1563 to 1575); tabs with no selected state (1572); bare `.halite-btn` renders as plain text (`index.css:57-59`); aircraft-list failures swallowed (45, 1188); user-facing errors that say "Configure VITE_HALITE_API_KEY" (`utils/diagnostics.js:61`, `utils/loadError.js:22`). | Frontend audit of 20 November. |

---

## 4. Target design

### 4.1 Package layout

```
backend/investigation/
  __init__.py
  ranker_port.py     # the only way V3 reaches the ranker (contract 4.2)
  beliefs.py         # scores -> beliefs, entropy
  policy.py          # answer / ask / abstain
  attributes.py      # askable attributes and how to read them from a report
  questions.py       # likelihoods and expected information gain
  grounding.py       # sentence splitting, citation levels, support score
  explain.py         # templated explanation with no model
  sessions.py        # session service over PostgreSQL
  prompts.py         # PROMPT_VERSION
  params/            # fitted parameters per ranker version (small JSON)
  data/faa_codes.json   # official code meanings, supplied by Usman
  experiments/
    simulated_technician.py
    abstention_curve.py
    grounding_eval.py
    results/
backend/api/routes/sessions.py
backend/db/models/sessions.py
frontend/src/features/investigation/, features/home/
```

`api/routes/diagnostics.py` keeps its three endpoints and their response shapes and delegates to `investigation`.

### 4.2 The model adapter (`services/groq_service.py`)

- Add `json_mode: bool = False` to `chat`, `chat_with_usage` and `_chat_openai_compatible`. Send `response_format`
  only when `json_mode` is true. `extract_json` and `extract_json_with_usage` pass `json_mode=True`.
- Tests with `httpx` mocked: a prose call sends no `response_format`; a JSON call sends it.
- Shahmeer's classifier calls `extract_json` and must be unaffected. Ask him to review this pull request.
- Keep `reasoning_effort: "none"` on the compatible path.

### 4.3 Degraded mode (`explain.py`)

When the model is not live, or a call fails, the system still returns ranked hypotheses, evidence and the decision,
with a reply built from a template:

```
Most supported check: {part} ({n} records: {ids}).
Why: {top two breakdown signals in words}.
{If any evidence is superseded: "Record {id} was later corrected by {id2}; it is shown as history only."}
{If the decision is abstain: "The history is too thin to rank a cause. Records found: {ids}."}
Language model unavailable: this text was generated from the ranking, not written by a model.
```

- The new sessions API always supports degraded mode and reports `llm_status: "unavailable"`.
- `POST /api/maintenance/diagnose` keeps returning 503 by default, because existing tests assert it
  (`tests/test_api_diagnostics.py::TestDiagnoseLlmBoundary::test_503_when_llm_not_live`). Add an optional request field
  `allow_degraded: bool = False`. When true, it returns 200 with `explanation: null`, the template text in a new field
  `fallback_explanation`, and a warning. The frontend sends `allow_degraded: true`.
- Cache: include `graph_repo.count_service_records()` and the ranker mode in the diagnose cache key, and never cache an empty explanation.

### 4.4 Sessions (`db/models/sessions.py`, `sessions.py`, `api/routes/sessions.py`)

Tables (new; `create_all` creates them):

| Table | Columns |
| --- | --- |
| `diagnostic_sessions` | `id` (uuid string), `organization_id`, `user_id`, `asset_id` (graph UUID), `asset_tail`, `title`, `status` (`open`, `closed`), `outcome_part`, `outcome_jasc`, `outcome_note`, `outcome_record_id`, `created_at`, `updated_at`, `closed_at` |
| `session_turns` | `id`, `session_id` (FK), `idx`, `user_text`, `case_state_json`, `decision` (`answer`, `ask`, `abstain`, `report`), `question_json`, `answer_json`, `reply_text`, `llm_status`, `grounding_json`, `ranker_mode`, `ranker_version`, `latency_ms`, `created_at` |
| `session_snapshots` | `id`, `turn_id` (FK), `hypotheses_json` (top 10 with scores and beliefs), `evidence_ids_json`, `belief_entropy` |

A snapshot makes every turn replayable: what the system believed, on what evidence, and what it decided.

Access rules, enforced in the service and tested:

- A technician sees and writes only their own sessions.
- A supervisor or admin sees every session in their organisation, read only.
- Someone else's session ID returns 404, not 403.
- API-key and ops-token principals have no user; they cannot create sessions.

Endpoints:

| Method and path | Body | Returns |
| --- | --- | --- |
| `POST /api/sessions` | `{asset_id?, title?}` | The session |
| `GET /api/sessions` | `?status=&mine=&has_outcome=&cursor=&limit=` | A page of sessions, newest first |
| `GET /api/sessions/{id}` | | The session with its turns and snapshots |
| `POST /api/sessions/{id}/turns` | `{message, answer?: {attribute, value}}` | The Copilot turn shape plus `decision`, `beliefs`, `question`, `grounding` |
| `POST /api/sessions/{id}/close` | `{outcome_part?, outcome_jasc?, outcome_note}` | The closed session |
| `GET /api/sessions/{id}/report` | | Printable HTML (Should tier) |
| `GET /api/sessions/summary` | | Summary shape, contract 4.6 |

Closing a session records what was actually found. Closed sessions with an outcome are labelled cases that V1 and V2
may read later. Say this in the interface: "What did you find? This improves future rankings."

`POST /api/maintenance/copilot/turn` stays, stateless, for backward compatibility, and gains the same additive fields.

### 4.5 From scores to beliefs (`beliefs.py`)

The ranker returns scores, which are not probabilities. For the top `N = 10` hypotheses with scores `s_1..s_N`:

```
b_i     = exp(s_i / T) / Z
b_other = exp(c / T) / Z
Z       = sum_j exp(s_j / T) + exp(c / T)
H(b)    = - sum_i b_i * log2(b_i)          (including the "other" bucket)
```

- `T` (temperature) and `c` (the score of "none of these") are fitted on the 2024 split by minimising negative
  log-likelihood: the true part's bucket if it is in the top 10, the "other" bucket if not.
- Different ranker modes have different score scales. Fit per `ranker_version` and store the result in
  `params/<ranker_version>.json`. If no parameters exist for the active ranker, fall back to `T = 1`, `c = min score`,
  and set `calibrated: false` in the response.
- Report expected calibration error of the top belief on 2025 (10 equal-width bins).
- Interface wording follows the measurement. If the calibration error on 2025 is above 0.10, or `calibrated` is false,
  label the bars "relative support". Use the word "probability" only if the measurement supports it. **Stop and ask.**

### 4.6 The decision rule (`policy.py`)

```
ANSWER   if b_top >= tau_answer and evidence_count(top) >= n_min
ASK      else if questions_asked < max_questions and best_gain >= g_min
ABSTAIN  otherwise
```

Defaults before fitting: `n_min = 2`, `max_questions = 3`. `tau_answer` and `g_min` are chosen on the 2024 split from
the accuracy-coverage curve at an operating point Usman picks.

- ANSWER: present the top hypotheses with evidence and the grounded explanation.
- ASK: present one question (4.7). Still show the current ranking, marked provisional.
- ABSTAIN: say the history is too thin, show what was found, and point to the approved manuals and a supervisor.
  Never invent a cause.

Every decision is stored on the turn with the numbers that produced it.

### 4.7 Question selection (`attributes.py`, `questions.py`)

**Askable attributes.** Each has a function that reads its value from a report.

| Attribute | Source | Values |
| --- | --- | --- |
| `stage_of_operation` | `StageOfOperationCode` | 15 codes; 100% filled |
| `how_discovered` | `HowDiscoveredCode` | 13 codes; 100% filled |
| `nature_of_condition` | `NatureOfConditionA` | about 23 codes; 100% filled |
| `precautionary_procedure` | `PrecautionaryProcedureA` | about 13 codes; 100% filled |
| `part_condition` | `PartCondition` | the 30 most frequent values plus OTHER (CORRODED, CRACKED, INOPERATIVE, DAMAGED, FAULTED, ...) |
| `location_zone` | `PartLocation` | the hundreds digit of a zone (`ZONE 200`, `ZN 100 ...`), else OTHER |
| Narrative cues | regex on the text | binary: intermittent, leak, smoke or odour, noise or vibration, warning message, found during inspection, after recent maintenance |

In 2025 the most common stage code covers about 81% of reports, so that attribute alone will rarely help.
The experiment decides which attributes earn their place.

**Code meanings.** `data/faa_codes.json` maps each code to the FAA's own wording. Usman obtains it from the FAA's
SDR documentation. **Do not write these meanings yourself, and do not guess from the letters.** Until the file exists,
the interface shows raw codes and the question feature stays behind a flag.

**Likelihood of an answer under a hypothesis.** For hypothesis `h` (a part) and attribute `A`:

```
P(A = a | h) = ( count(reports of part h with A = a) + alpha * P_fleet(a) ) / ( n_h + alpha ),     alpha = 5
```

`P_fleet(a)` is the share of all visible reports with `A = a`. Use reports of the same aircraft model when there are at
least 20 for that part; otherwise the whole fleet. The "other" bucket uses `P_fleet`. Only reports visible at the
query's knowledge time count (contracts section 6).

**Expected information gain.**

```
P(a)          = sum_h b(h) * P(a | h)
b'(h | a)     = b(h) * P(a | h) / P(a)
EIG(A)        = H(b) - sum_a P(a) * H(b'(. | a))          in bits
```

Ask the attribute with the largest gain, if it reaches `g_min`. An answer of "not sure" leaves the beliefs unchanged
and removes that attribute from the list. After an answer, replace `b` with `b'` and store both on the turn.

The interface shows the question as multiple choice with a line such as "Why this question: it is expected to remove
0.7 of 2.1 bits of uncertainty." Unit test: a three-hypothesis toy case with hand-computed gain in the test's docstring.

**Free-text answers** are FYP-II. In December, questions are multiple choice.

### 4.8 The simulated-technician experiment (`experiments/simulated_technician.py`)

This is the evidence for FR-20 and part of RQ4.

- Cases: correction pairs of the split from `correction_pairs.csv`.
- Initial query: the **original** report's symptom text.
- Answer key: the part named by the **correction**.
- When the system asks about an attribute, the simulated technician answers from the **original** report's own fields.
  That is what a technician knew at the time. Never answer from the correction; that would leak the result.
- Policies compared: information gain; a random askable attribute; no questions. If time allows, the model's own
  question with the answer read from the original narrative.
- Measure after 0, 1, 2 and 3 questions: top-1 and top-3 accuracy of the answer key, and mean entropy.
  95% bootstrap intervals. Report by `part_change` category.
- State which ranker produced the scores (`mid_heuristic` until V1 ships a better one; re-run when it does).
- If the three-year corpus is not ready, run on the existing 2025 files and re-run later. Do not wait.

An honest small effect is acceptable. A claimed effect without this experiment is not.

### 4.9 RQ4: abstention (`experiments/abstention_curve.py`)

- For each case take the top belief after the questioning policy.
- Sweep `tau_answer`. At each value compute coverage (share of cases answered) and accuracy on answered cases
  (top-1 and top-3). Plot accuracy against coverage.
- "Unsupported suggestion rate" is the share of all cases where the system answered and the answer key was not in its top 3.
  Report it with abstention off (`tau_answer = 0`) and at the chosen operating point.
- Choose on 2024, report on 2025.

### 4.10 Sentence-level grounding (`grounding.py`)

Every sentence of an explanation is checked against the report it cites.

| Level | Check | Today |
| --- | --- | --- |
| L1 | The cited ID exists in the graph | Done for all paths |
| L2 | The cited ID is in the evidence shown this turn | Done for the Copilot only; add to diagnose |
| L3 | The sentence is supported by the cited report's text | New |
| L4 | A model judge rules on borderline sentences | Should tier |

L3 support score for a sentence `s` citing reports `R`:

```
support(s) = max over r in R of [ w * containment(s, r) + (1 - w) * cosine(embed(s), embed(r.text)) ]
containment(s, r) = | content_tokens(s) ∩ tokens(r.text + r.part_name) | / | content_tokens(s) |
```

- `content_tokens` drops stopwords, record IDs and hedging words. Part names and condition words in the sentence must
  appear in the cited report, or the sentence is at most "weak".
- Embeddings come through `investigation/embed_port.py`, which uses V1's embedder if it can be imported and returns
  `None` otherwise. With no embedder, `w = 1` and the response says `checked_with: "lexical"`.
- Labels: `supported` (score at or above `theta_hi`), `weak` (between), `unsupported` (below `theta_lo`), `uncited`
  (no citation). An uncited sentence is acceptable only if it matches a short whitelist of safety and hedging templates.
- Thresholds are chosen on the hand-labelled set (below), not by feel.
- Response field: `grounding: {sentences: [{text, citations, level, score}], unsupported_count, checked_with}`.
- Interface: a mark beside each sentence; unsupported sentences are dimmed with a tooltip; a counter such as
  "7 of 8 sentences supported".

**Validating the checker** (`experiments/grounding_eval.py`, Should tier). Usman and one teammate label 150
sentence-report pairs as supported, partly supported or unsupported. Build the tooling: export a sample to CSV,
import two label files, compute Cohen's kappa, and the checker's precision and recall against the agreed labels.
Then compare the unsupported-sentence rate of Halite against the same model answering with no evidence. That
comparison is the proposal's "direct language-model" baseline.

### 4.11 The four coded fields on reports

The offline experiments read them from the corpus CSV. The live question feature needs them on `ServiceRecord`:
`stage_of_operation`, `how_discovered`, `nature_of_condition`, `precautionary_procedure` (raw codes).

- Ingest: four lines in `agents/maintenance_agent.py` (the record dict near lines 174 to 186) and four keys in the
  property whitelist of `create_service_record` in the graph repository, plus the memory store. These are Shahmeer's files.
  This specific additive edit is pre-agreed in the plan. Make it one small pull request **after** the backend
  preparation merges, with Shahmeer as reviewer.
- Backfill: `backend/scripts/backfill_coded_fields.py --csv <corpus file> [--dry-run]`, idempotent, matching on `record_id`.
  Umar runs it on staging after a backup. You do not.

### 4.12 Frontend

Shahmeer's frontend preparation pull request (contracts section 3.2) moves today's `pages/Diagnostics.jsx` into
`features/investigation/`, split into one file per component. Start your frontend work after it merges.

Then in `features/investigation/`:

- `InvestigationsPage` at `/app/investigations`: the user's sessions, filter by status, resume, open a closed one read-only.
- `InvestigationWorkspace` at `/app/investigations/:id`: the existing Copilot interface re-based on the sessions API.
  `/app/diagnostics` redirects here.
- Components: `BeliefBars` (label follows 4.5), `QuestionCard` (multiple choice, "not sure", the "why this question" line),
  `GroundedReply` (per-sentence marks), `AbstainCard`, `DecisionBadge`, `CloseSessionDialog`, the existing
  `DiagnosticEvidenceInspector`.
- On logout, remove `halite-diagnostic-active-workspace` and `halite-diagnostic-copilot-sessions` from `localStorage`.
  Drafts may stay in `localStorage` keyed by user ID.
- Fix the hazards in D8 as you touch each file.

`features/home/HomePage` at `/app/home`, the new landing route: one widget per vertical from the three summary
endpoints (contract 4.6). A widget whose endpoint fails is hidden, not shown as an error.

Shahmeer owns the shell, `src/components/ui/`, `index.css` and the Tailwind config. Use the primitives and ask him for changes.

### 4.13 Choosing the interactive model

Usman and Shahmeer run a 20-prompt comparison on Shahmeer's M4 among two or three 7 to 8B models that fit in 16 GB (candidates:
the installed `mistral:7b-instruct`, `qwen2.5:7b-instruct`, `llama3.1:8b`, and staging's `phi4-mini` as the reference).
Build the harness: fixed prompts from real cases, and for each model the share of valid outputs, the share of cited IDs
that are in the evidence, the unsupported-sentence count from 4.10, and seconds per reply. Usman decides. Staging keeps `phi4-mini`.

Your own laptop has no GPU worth using. Develop against `phi4-mini` or another 3 to 4B model through Ollama on CPU,
or against Groq while its quota lasts. The beliefs, the policy, question selection, the simulated experiment and
lexical grounding need no model at all, so most of this vertical runs anywhere.

### 4.14 Backend preparation and CI quality (shared duties)

- The backend preparation pull request is specified in contracts section 3.1. It has priority over every other work
  package, because all three verticals add routes, tables and queries on top of it. Time-box it to 24 November.
  If it runs late, cut the legacy removal and ship the splits and registrations.
- Add `ruff` to CI, failing only on real errors at first (syntax, undefined names).
- Add `pytest --cov` with an XML and terminal report. Report the coverage number for the core modules. NFR-04 asks for 80%.
- Remove unused dependencies (`langchain*`, `python-dotenv`, `python-docx`) in the preparation pull request.
- Keep the Panel Action Register (Form 10) current before each evaluation.

### 4.15 What the panel must see

The research is graded in a 15-minute presentation. Each result below must be visible on a product page, read from a
committed results file, never typed by hand. Serve the files through `GET /api/sessions/experiments` and show them in a
"How Halite decides" panel inside `features/investigation/`.

| Research result | Screen |
| --- | --- |
| Chosen questions beat random ones | Line chart: accuracy after 0, 1, 2 and 3 questions for the three policies, with intervals |
| Abstaining removes unsupported answers | Accuracy against coverage curve with the chosen operating point marked |
| Every sentence is checked | Marks beside each sentence and a counter such as "7 of 8 supported"; hovering a sentence highlights the matching words in the cited report |
| The system reasons in view | Belief bars that move after each answer, the decision badge, and the "why this question" line |

Follow the presentation standard in contracts section 11: shared primitives, one chart library, sample size and data
year on every chart, no hand-typed numbers, loading, empty and error states, dark and light themes at 1280 pixels wide.

---

## 5. Work packages

| ID | Tier | Work | Accepted when |
| --- | --- | --- | --- |
| WP-S0 | Must | Backend preparation pull request (contracts section 3.1). Do this first. | CI green; maintenance route tests unchanged and passing. |
| WP-S11 | Must | CI lint and coverage. Template for the Panel Action Register (Form 10). | CI shows both reports. |
| WP-S1 | Must | Adapter `json_mode`; degraded mode; `allow_degraded` on diagnose; cache key fix. | Tests: prose call sends no `response_format`; with the model off, a session turn returns ranking, evidence and template text; the existing 503 test still passes. |
| WP-S2 | Must | Session tables, service, endpoints, access rules. | Tests for the lifecycle and for each access rule; a session created in one client is readable in another. |
| WP-S3 | Must | Investigations page and workspace on the sessions API; close dialog; logout clears browser copies. | Component tests; `/app/diagnostics` redirects. |
| WP-S4 | Must | `ranker_port.py`, `beliefs.py`, `policy.py`, parameter fitting, `abstention_curve.py`. | Toy tests for the maths; results on 2024 and then 2025 committed. |
| WP-S5 | Must | `attributes.py`, `questions.py`, `simulated_technician.py`, `QuestionCard`, coded fields ingest and backfill script. | Hand-computed gain test; experiment results committed; the question appears in the interface behind a flag until `faa_codes.json` exists. |
| WP-S6 | Must | `grounding.py` levels L2 and L3 (lexical, plus dense when available), `GroundedReply`. | Tests for each level; the diagnose path now applies the evidence allow-list. |
| WP-S7 | Must | Home dashboard shell. | Hides a failing widget; component test. |
| WP-S8 | Should | Model judge (L4), labelling tooling, `grounding_eval.py`, the no-evidence comparison. | Precision, recall and kappa computed from two label files. |
| WP-S9 | Should | Printable investigation report. | One click from a closed session; prints cleanly. |
| WP-S10 | Must | Model comparison harness (4.13). | A table Usman can read and decide from. |

---

## 6. Stop and ask Usman

1. The operating point on the accuracy-coverage curve (`tau_answer`, `g_min`).
2. Whether the belief bars may be called probabilities.
3. `faa_codes.json`. You never write code meanings.
4. The interactive model.
5. The thresholds `theta_lo` and `theta_hi`, and the uncited-sentence whitelist.
6. Any change to a frozen response field of diagnose or the Copilot turn.
7. Any wording that could read as approving a repair or certifying airworthiness.
8. Any new dependency.
9. Deleting a legacy test, or anything in the backend preparation pull request that changes behaviour.

Things only Usman does, which you support with tooling but never write for him:

- The one-page design note, written before WP-S4.
- Labelling the 150 sentence-report pairs.
- Weighing a wrong answer against an extra question when he picks the operating point.
- The report sections: decision-layer design and rationale, experiment protocol, results, FYP-2 plan for RQ4 and RQ5.

---

## 7. Do not

- Answer a simulated question from the correcting report.
- Tune `T`, `c`, thresholds or prompts on 2025.
- Let the model rank, choose the question or decide to abstain. It extracts facts and writes prose.
- Import `backend/retrieval/` or `backend/integrity/` directly. Use `ranker_port.py`, `embed_port.py` and
  `integrity.validity` through the wrapper in contract 4.1.
- Edit Shahmeer's or Umar's feature folders, the frontend shell or the design system.
- Show a session to anyone but its owner and their supervisors.

---

## 8. Report back after each work package

1. What you built, by file.
2. The acceptance evidence: test names, command output, the results file path.
3. Anything in this guide that turned out to be wrong.
4. Knowledge-bank files you updated and any decision record you added.
5. A two-line AI-assistance note for the pull request.

---

## 9. Reading for Usman

- Guo, Pleiss, Sun and Weinberger (2017), *On Calibration of Modern Neural Networks* (temperature scaling).
- Lindley (1956), *On a Measure of the Information Provided by an Experiment*.
- de Kleer and Williams (1987), *Diagnosing Multiple Faults* (choosing the next measurement by entropy).
- Geifman and El-Yaniv (2017), *Selective Classification for Deep Neural Networks*.
- Rashkin et al. (2023), *Measuring Attribution in Natural Language Generation Models*.
- Min et al. (2023), *FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation*.
- Es et al. (2023), *RAGAS: Automated Evaluation of Retrieval Augmented Generation*.

### Verified implementation snapshot — offline WP-S5

The pure question engine and three-control 2024 simulation are implemented. See `knowledge/context/modules/investigation_questions.md`, committed result traces and `docs/work/usman/evidence/phase5-*`. All 342 backend tests pass. Information-gain accuracy advantage is uncertain; no threshold or 2025 result is asserted. Live question UI/answers and the separately authorized shared-field integration remain open.

### Verified implementation snapshot — coded-field review preparation

User-authorized separate branch adds exactly twelve shared-file lines and the idempotent/dry-run backfill. All 355 backend tests pass with isolated Neo4j/PostgreSQL; actual CLI apply/repeat proof is saved. See `docs/work/usman/CODED_FIELDS_INTEGRATION.md`. Shahmeer review/merge and Umar’s actual staging backup/backfill remain pending; no staging mutation claimed.

### Verified implementation snapshot — managed live WP-S5

The session question/answer controller is implemented behind disabled-by-default `SESSION_QUESTIONS_ENABLED` and an explicit policy file. It saves a unique question ID, model basis/matrices, policy, prior/posterior and answer history. Answers never read graph/model state. The production-built browser verifies changing bars, not-sure, three-question budget and exact reload replay with real local databases. The synthetic policy fixture is not the chosen operating point; shared responsive-shell preparation was separately authorized after visual QA exposed the phone-width sidebar problem.

### Implemented sentence-audit/review preparation

L2/L3 audits now accompany managed turns and quick diagnosis; original prose and
stateless response fields remain intact. Default valid citations are unrated until
calibration is accepted. Explicit experimental settings are labelled. The frozen
150-pair constructed FAA-text packet has separate blinded copies for Usman and
Muhammad Umar (chosen by the user). No human labels or results are fabricated.
The strict importer/agreement/adjudication/fit-validation tooling and protocol are
in `docs/work/usman/grounding_review_v1/README.md` and
`knowledge/context/modules/investigation_grounding.md`. Actual labels, accepted
thresholds/whitelist, L4 and generated-answer/no-evidence measurements remain gates.

### Portable model-comparison preparation

The user requested a self-contained runner for Shahmeer to execute on the M4.
`model_prompts.py`, `model_compare.py` and `model_bundle.py` provide a frozen real
20-case packet, strict serial Ollama measurements, saved raw responses/failures,
resume verification and a generated comparison table. The portable ZIP needs
only Python and already installed models/Ollama, and verifies its source hashes.
Protocol, role/hardware distinctions and the handoff are documented in
`docs/work/usman/MODEL_COMPARISON_RUNNER.md`. Synthetic verification is not real
M4 measurement, human grounding accuracy or the interactive-model decision.
