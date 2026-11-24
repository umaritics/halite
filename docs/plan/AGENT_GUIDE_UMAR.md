# Agent guide: Retrieval and Ranking (owner: Muhammad Umar)

You are the coding agent for Muhammad Umar on the Halite final-year project. Umar owns vertical V1,
**Retrieval and Ranking**, from database to screen to measured result. Read `AGENTS.md` and
`docs/plan/CONTRACTS.md` first. This guide tells you how the current code works, what is wrong with it,
what to build and how each piece is accepted. Work on one work package at a time, the one Umar names.

**Frontend paths changed on 24 November.** Pages now live in `frontend/src/features/<name>/` and register through
a manifest; see `docs/plan/CONTRACTS.md` section 2 and `frontend/src/app/README.md`. Frontend file names below predate that.

Facts and line numbers refer to `origin/main` at `ac5aa66`. If the code has moved, re-locate the function by
name and tell Umar what changed.

---

## 1. Mission

Given an aircraft and a symptom in a technician's words, return the past cases that matter and rank the candidate
parts, using only what was known at the time and only evidence that still stands.

By the FYP-I Final (December 2026) this vertical must deliver:

1. A reproducible benchmark that compares six retrieval methods on held-out 2025 FAA data.
2. Hybrid retrieval running in the product behind the `RETRIEVAL_MODE` setting.
3. A graph layer of parts, systems and aircraft models.
4. Two pages: an Evaluation Lab and an evidence search.

The research questions you serve:

- RQ1: does graph-constrained retrieval find relevant cases better than keyword retrieval?
- RQ2: does hybrid graph and semantic retrieval rank fault evidence better than semantic retrieval alone?
- RQ3: does correction-aware retrieval reduce misleading historical recommendations?

The panel will ask Umar to explain, justify against an alternative, predict what breaks and modify any of this
under questioning. So keep the code small, named after the concepts, and free of cleverness he cannot defend.

---

## 2. How the current code works

Everything lives in `backend/services/diagnostic_retrieval.py` (486 lines).

| Function | Line | What it does |
| --- | ---: | --- |
| `_normalise`, `_text_similarity` | 27, 33 | Uppercase and whitespace-split; Jaccard similarity of the two word sets. No stopwords, no stemming. |
| `_record_is_superseded` | 42 | Returns `status == "superseded"`. Reads a status string, not the `SUPERSEDES` link. |
| `asset_history_context` | 50 | Newest 30 reports for the aircraft via `graph_repo.list_asset_history_recent`. Drops IDs starting with `DEMO`. |
| `similar_symptom_records` | 90 | The fleet scan. Loads `graph_repo.list_service_records(limit=2500)` and scores each in Python. |
| `build_diagnostic_context` | 208 | Picks a JASC hint, then combines history and fleet matches. |
| `rank_diagnostic_checks` | 275 | Sums evidence weights per part name. |
| `build_copilot_context`, `rank_copilot_checks`, `ranking_delta` | 355, 421, 442 | The same for the multi-turn Copilot, with ruled-out parts removed. |

The scoring, exactly as coded:

```
fleet_score(r) = 0.50 * [jasc(r) == jasc_hint]
               + 0.30 * Jaccard(symptom, r.part_name)
               + 0.20 * Jaccard(symptom, r.text)          # dropped if < 0.05; top 20 kept

score(part) = sum over the aircraft's recent reports i (newest i = 0) with that part:
                  0.4 * 1/(i+1) * (0.3 if superseded else 1)
            + sum over fleet matches r with that part:
                  0.6 * fleet_score(r) * (0.3 if superseded else 1)
```

Constants: `FLEET_SCAN_CAP = 2500`, `RANK_WEIGHT_ASSET_HISTORY = 0.4`, `RANK_WEIGHT_FLEET_MATCH = 0.6`,
`RANK_SUPERSEDED_PENALTY = 0.3` (lines 15 to 20). Ties break by score, then evidence count, then part name.
Parts named `UNKNOWN` or blank are skipped.

The JASC hint is the first history report whose `part_name` has Jaccard above 0.2 with the whole symptom
(lines 239 to 243). For a sentence-length symptom this almost never fires, so the 0.50 term is usually zero.

Graph access goes through `GraphRepository` in `backend/graph/queries.py` (class at line 32; maintenance methods
from about line 700). `self.is_memory` switches between Cypher and the in-memory store used by tests.
Every new query needs both branches.

---

## 3. Defects to fix (verified in code)

| ID | Defect | Evidence |
| --- | --- | --- |
| D1 | The fleet scan never excludes the selected aircraft. `rec_asset` is `asset_key`, a tail number. `exclude_asset_id` is the Asset UUID passed by the route. They never match, so the aircraft's own reports are counted twice, as history and as fleet. | Lines 118 to 127. The tests at `tests/test_diagnostic_retrieval.py:123-127, 208-212` pass vacuously. |
| D2 | The history term has no symptom in it. The most recently reported part ranks high whatever the technician typed. | Line 316. |
| D3 | Validity comes from `status`. That string is overwritten when a record is re-processed. `superseded_by` reads a property `superseding_record` that nothing writes. | Lines 42 to 43, 82, 199. |
| D4 | Each request loads and scores up to 2,500 full reports in Python. The cap is newest-first, so older reports are invisible once the corpus grows past 2,500. The Copilot runs it twice per turn. | Lines 15, 112. |

**Before fixing anything, freeze the current behaviour as baseline B0.** Copy the module unchanged to
`backend/retrieval/baselines/mid_ranker.py` with a header comment giving the commit hash. B0 is what the mid
evaluation saw. B1 is the same code with D1 to D3 fixed. The difference between B0 and B1 is a result worth reporting.

---

## 4. Target design

### 4.1 Package layout

```
backend/common/
  faa_text.py            # shared regexes and boilerplate stripping (you own it; V2 and V3 may import it)
backend/retrieval/
  __init__.py
  text.py                # normalise(), tokenize(), ABBREVIATIONS (Umar writes the list)
  docstore.py            # DocStore: records sorted by submitted_ts, with numpy arrays of fields
  bm25.py                # BM25Index
  dense.py               # Embedder protocol, OnnxEmbedder, DenseIndex
  scope.py               # same_aircraft / same_model / fleet masks, as_of cut-off
  fusion.py              # rrf(), weighted()
  ranker.py              # hits -> part hypotheses
  service.py             # RetrievalService: build, refresh, search, rank
  baselines/mid_ranker.py
backend/evaluation/
  __init__.py
  datasets.py            # suite A and suite B from the corpus files
  protocol.py            # visibility rule and leak assertions
  metrics.py             # recall_at_k, mrr, ndcg_at_k, topk_accuracy, bootstrap_ci, paired_bootstrap
  run.py                 # CLI
  fit.py                 # coordinate ascent for the fitted hybrid
  results/               # small committed JSON files
backend/graph/repo/retrieval.py        # your Cypher and memory-store queries
backend/graph/migrations/001_retrieval_part_system_model.py
backend/api/routes/retrieval.py, evaluation.py
backend/db/models/evaluation.py
frontend/src/features/retrieval/, features/evaluation/, features/graph/
```

**One code path.** `backend/evaluation` imports `backend/retrieval`. The module that is benchmarked is the module
that serves requests. Never write a second implementation "just for the experiment".

### 4.2 Text handling (`common/faa_text.py`, `retrieval/text.py`)

FAA narratives are uppercase, abbreviated, and carry boilerplate. Examples from real 2025 reports:

```
ORIGINAL   AALA202412230156  part LIGHT           JASC 3350
  AIRCRAFT WAS GROUNDED: EMERGENCY CEILING LIGHT INOPERATIVE AT LEFT HAND ROW 17ABC.
  **SUPPLEMENTAL REPORT WILL BE SUBMITTED**(OPEN).
CORRECTION AALA202501020156  part ELEC CONNECTOR  JASC 3397
  AIRCRAFT WAS GROUNDED: EMERGENCY CEILING LIGHT INOPERATIVE AT LEFT HAND ROW 17ABC.
  **SUPPLEMENTAL REPORT FOR (AALA202412230156): FOUND LOOSE CONNECTOR FOR AFFECTED LIGHT ABOVE CEILING PANEL.
  RESECURED CONNECTOR AND OPERTIONAL CHECK GOOD. PER WDM 33-51-13 AND AMM 33-51-00**(CLOSED).
```

`faa_text.py` provides:

- `CITATION_RE = SUPPLEMENTAL\s+REPORT\s+FOR\s*\(?\s*([A-Z0-9]{6,})\s*\)?` (case-insensitive; the same pattern as
  `scripts/fetch_sdr_data.py` line 35).
- `OPEN_MARKER_RE = SUPPLEMENTAL\s+REPORT\s+WILL\s+BE\s+SUBMITTED`.
- `split_symptom_and_finding(text) -> (symptom, finding)`: everything before the citation phrase is the symptom;
  everything after is the finding. With no citation the whole text is the symptom.
- `strip_boilerplate(text)`: removes `AIRCRAFT WAS GROUNDED:`, the open marker, `(OPEN)`, `(CLOSED)` and stray `**`.

`services/conflict_screen.py` already holds similar regexes (`_ANSWER_KEY`, `_BOILERPLATE`). Do not import V2's module.
Shahmeer may switch to yours later.

`text.py` provides `tokenize(text)`: strip boilerplate, uppercase, keep `A-Z0-9` runs, keep manual references such
as `33-51-00` as one token and also emit `ATA33`, expand abbreviations from `ABBREVIATIONS`, drop one-letter tokens.

**Stop and ask:** `ABBREVIATIONS` is Umar's list, built by reading 100 narratives. Ship an empty dict and a test.
Do not fill it yourself.

### 4.3 DocStore

One ordering shared by every index: documents sorted ascending by `submitted_ts`, the timezone-aware datetime
parsed from `SubmissionDate` (format `2025-01-02T09:45:26.140-05:00`), stored as a float64 epoch array.
Then "what was known at time t" is a prefix: `cut = numpy.searchsorted(submitted_ts, t, side="left")`, and a
document is visible when its index is below `cut`. Keep parallel arrays: `record_id`, `asset_key`, `aircraft_model`,
`jasc`, `part_norm`, `chain_id` (an ID shared by a report and its corrections, from `correction_pairs.csv`;
unique otherwise).

Records with no parseable `SubmissionDate` fall back to `DifficultyDate` at midnight UTC and are counted in a log line.

### 4.4 BM25 (`bm25.py`)

Okapi BM25 over `tokenize(text) + tokenize(part_name)`:

```
score(q, d) = sum over query terms t of
    IDF(t) * f(t,d) * (k1 + 1) / ( f(t,d) + k1 * (1 - b + b * |d| / avgdl) )
IDF(t) = ln( 1 + (N - n_t + 0.5) / (n_t + 0.5) )
```

- Defaults `k1 = 1.2`, `b = 0.75`. Select on the 2024 split from `k1 in {0.9, 1.2, 1.6}`, `b in {0.5, 0.75}`.
- Implementation: an inverted index, token to (doc index array, term frequency array). Score with numpy.
  Do not add `rank_bm25`; a 60-line class you can explain beats a dependency.
- Statistics (`N`, `n_t`, `avgdl`) are computed on reports visible at the split boundary. For 2025 test queries that
  means 2023 plus 2024 only. Write this choice in the protocol note; it removes any argument about leakage through IDF.
- Unit test: a five-document toy corpus with scores computed by hand in the test's docstring.

### 4.5 Dense retrieval (`dense.py`)

- `Embedder` is a protocol with `embed(texts: list[str]) -> numpy.ndarray` returning L2-normalised float32 rows.
- `OnnxEmbedder` wraps a small CPU model through an ONNX runtime. Candidates: `BAAI/bge-small-en-v1.5` and
  `sentence-transformers/all-MiniLM-L6-v2`, both 384 dimensions. The `fastembed` package is the intended runtime.
  **Check its current documentation for the exact model names and API before writing code.** Do not rely on this guide's memory.
  Do not add `torch` to the API image.
- `DenseIndex` holds one float32 matrix in DocStore order. Cosine similarity is a dot product. Apply the visibility
  prefix and scope masks before taking the top k.
- Embed `strip_boilerplate(text)`. For queries from supplementals use only the symptom part.
- Size check: 196,424 x 384 x 4 bytes is about 300 MB. For offline evaluation store it as a `.npy` file under
  `backend/data/index/` (git-ignored) and memory-map it. The staging corpus (2,079 reports) is about 3 MB.
- Tests use a `FakeEmbedder` (hash of tokens to a fixed vector) so CI needs no model download.

**Stop and ask:** which embedding model to keep. Run both on suite A with the 2024 split and give Umar the table,
plus embedding throughput on his laptop. He decides.

### 4.6 Scopes (`scope.py`)

For a query about aircraft tail `T` with model `M`:

- `same_aircraft`: documents with `asset_key == T`.
- `same_model`: documents with `aircraft_model == M` and a different tail.
- `fleet`: everything else.

Baseline B4, graph only, uses no text: the aircraft's own reports newest first, then same-model reports newest first.
It answers "what does graph traversal alone give you".

### 4.7 Fusion (`fusion.py`)

Reciprocal rank fusion (Cormack, Clarke and Buettcher, 2009):

```
rrf(d) = sum over lists L of 1 / (k + rank_L(d)),   k = 60
lists = [BM25 top 200, dense top 200, graph list top 200]
```

Fitted hybrid (B6), on min-max normalised scores within the candidate set:

```
s(d) = a * bm25(d) + b * dense(d) + c * scope_bonus(d) + e * recency(d),    a + b + c + e = 1
scope_bonus = 1.0 same_aircraft, 0.5 same_model, 0.0 fleet     (the two constants are also fitted)
recency(d)  = exp(-(t_query - t_d) / tau)                      (tau fitted from {90, 365, 1095} days)
```

Fit by coordinate ascent on the 2024 split, maximising MRR of the correct part on suite B. Report suite A too.
RRF comes first because it has no parameters to overfit. Umar must be able to say that sentence and defend it.

### 4.8 From hits to part hypotheses (`ranker.py`)

```
score(part p) = sum over the top K fused hits d with part_norm(d) == p of  fused(d) * v(d)
v(d) = lambda if d is superseded else 1          # lambda = 0.3 by default; selected from {0, 0.1, 0.3, 0.5, 1}
K = 50
```

- `part_norm`: uppercase, trimmed, internal whitespace collapsed. Skip `UNKNOWN`, `NONE`, `NA`, `N/A`, `NOTREPORTED` and blank.
- "Superseded" comes from Shahmeer's `integrity.validity.superseded_by` when it exists, and from one local wrapper around
  the status check until then (contract 4.1). In offline evaluation it comes from `correction_pairs.csv`.
- Keep the existing tie-break: score descending, evidence count descending, part name ascending.
- Also return a system-level list aggregated by `jasc_code`.
- Fill `breakdown` per hypothesis with each signal's share of the score. The interface uses it for "why this rank".

### 4.9 Serving (`service.py`, `api/routes/retrieval.py`)

- `RetrievalService` is built at application start from the graph through a new repository method in
  `graph/repo/retrieval.py` that returns the indexed fields and the stored embedding.
- A report with no `embedding` property is embedded in a batch and written back
  (`SET r.embedding = $vec, r.embedding_model = $name`).
- Refresh without touching Shahmeer's ingest code: before a search, compare `graph_repo.count_service_records()` with the
  index size. If they differ, load the missing reports and append them. A newly ingested report is then retrievable in the demo.
- It must work in memory mode, because tests and `DEMO_MODE` use the memory store.
- Setting `RETRIEVAL_MODE` (default `mid_heuristic`) chooses the mode. A request may override it with `mode`.
  If the embedder fails to load, log it, serve `bm25`, and report the downgrade in `/api/health` and in the response.

Endpoints (all need an authenticated user; none calls a language model):

| Method and path | Body or query | Returns |
| --- | --- | --- |
| `POST /api/retrieval/search` | `{query, asset_id?, mode?, k? (max 50), as_of?, filters?: {jasc_code?, part_name?, scope?: [...]}}` | `{mode, hits: [evidence item], took_ms}` |
| `POST /api/retrieval/rank` | `{asset_id?, symptoms: [...], observations?: [...], ruled_out?: [...], as_of?, mode?, k?}` | The shape in contract 4.2 |
| `GET /api/retrieval/summary` | | Summary shape, contract 4.6 |
| `GET /api/evaluation/runs` | `?suite=&split=` | Committed results, newest first |
| `GET /api/evaluation/runs/{id}` | | One run with per-method metrics and intervals |
| `GET /api/evaluation/replay/{pair_id}` | `?methods=b2,b3,b5` | For one correction pair: the original, the correction, and each method's top 5 with the true part marked |

Measure retrieval latency (no model call) on staging: p50 and p95 over 200 requests. The target in NFR-02 is p95 at or
below 500 ms. Report the number whatever it is.

### 4.10 Graph layer (`graph/migrations/001_retrieval_part_system_model.py`)

Idempotent, with `--dry-run`:

- For each `ServiceRecord` with a usable part name: `MERGE (p:Part {name: part_norm})` and `MERGE (r)-[:INVOLVES]->(p)`.
- For each with a JASC code: `MERGE (s:System {jasc_code})` setting `ata_chapter = jasc_code[:2]`, and `MERGE (r)-[:CONCERNS]->(s)`.
- For each `Asset` with make and model: `MERGE (m:AircraftModel {make, model})` and `MERGE (a)-[:OF_MODEL]->(m)`.

Never use the label `Component`; it belonged to the deleted legacy domain. Add the memory-store equivalents.
Extend `/api/graph/overview` only additively, for example `?include=parts,systems`, default off.
Staging is migrated by Umar after a backup. You do not run it.

### 4.11 Frontend

- `features/retrieval/EvidenceSearchPage`: a query box, an optional aircraft picker, a mode toggle
  (keyword, semantic, hybrid), scope chips (this aircraft, same type, fleet), result cards with per-signal scores,
  a "superseded" badge with a link to the correcting report, and deep links to asset history.
- `features/evaluation/EvaluationLabPage`: a results table per suite, a bar chart per method with interval whiskers,
  run metadata (commit, date, corpus size, split), the ablation table, and case replay.
- `features/graph`: a toggle to show the parts and systems an aircraft's reports share.
- Each feature has `api.js`, `manifest.jsx` and colocated tests that mock only its own `api.js`.
- Use the primitives in `src/components/ui/` and Recharts. Every page needs loading, empty and error states.

### 4.12 What the panel must see

The research is graded in a 15-minute presentation. Each result below must be visible on a product page, read from a
committed results file, never typed by hand.

| Research result | Screen |
| --- | --- |
| Six methods compared on held-out 2025 cases | Evaluation Lab: one bar per method with interval whiskers, the winner highlighted, the number of cases, the split year and the commit shown |
| Hybrid finds what keywords miss | Evidence search: the same query under keyword, semantic and hybrid, with a small bar per signal on each result |
| Ignoring a corrected report changes the top answer | Case replay: before and after for one real pair, with the corrected part moving to the top |

Follow the presentation standard in contracts section 11: shared primitives, one chart library, sample size and data
year on every chart, no hand-typed numbers, loading, empty and error states, dark and light themes at 1280 pixels wide.

---

## 5. The benchmark

### 5.1 Suites

**Suite A, system identification, at scale.**

- Queries: 2,000 reports sampled from the split year with seed 42, stratified by ATA chapter (`jasc_code[:2]`).
  Exclude reports that contain a citation and reports whose part is unknown.
- Query text: the boilerplate-stripped narrative. Variant "A-masked" also removes the tokens of the report's own part name.
- Graded relevance of a retrieved report: 2 if same part and same JASC, 1 if same JASC only, 0 otherwise.
- Metrics: Recall@10 (relevance at least 1), MRR, nDCG@10; top-1, top-3, top-5 accuracy of the hypothesised part.

**Suite B, resolution prediction, the thesis test.**

- Queries: every pair in `correction_pairs.csv` for the split. Query text is the **original** report's symptom.
- Answer key: the correction's `part_name` and `jasc_code`. Skip pairs whose corrected part is unknown.
- Report overall and by `part_change` category: `named_to_named`, `unknown_to_named`, `same`.
- Metrics: top-1, top-3, top-5 accuracy of the corrected part; MRR of the corrected part; the same for JASC.

### 5.2 Visibility (`protocol.py`)

For a query built from report `q`: visible documents are those with `submitted_ts < q.submitted_ts` and
`chain_id != q.chain_id`. `protocol.assert_no_leak(query, hits)` raises if any hit violates this, and the harness
calls it on every query. A unit test builds a toy corpus where the leak exists and checks that the assertion fires.

### 5.3 Methods

| ID | Method |
| --- | --- |
| B0 | The mid ranker exactly as shipped (`baselines/mid_ranker.py`) |
| B1 | The mid ranker with D1 to D3 fixed |
| B2 | BM25 |
| B3 | Dense |
| B4 | Graph only |
| B5 | Hybrid, reciprocal rank fusion |
| B6 | Hybrid, weights fitted on 2024 (Should tier) |
| B7 | A language model with no evidence, on 150 suite B cases (Stretch) |

### 5.4 RQ3, correction-awareness

On `named_to_named` pairs of the split: make both the original `o` (part X) and the correction `s` (part Y) visible,
query with their shared symptom text, and compute how often Y ranks above X and how often Y is top-1.
Run with `lambda = 1` (unaware) and the selected `lambda` (aware). Run twice: with links taken from
`correction_pairs.csv`, and, when available, with links produced by V2 in a graph snapshot.

### 5.5 Statistics and output

- 95% bootstrap intervals over queries (1,000 resamples, seed fixed).
- Paired bootstrap for the difference between two methods on the same queries.
- CLI: `python -m evaluation.run --suite A,B --methods b0,b1,b2,b3,b4,b5 --split test`.
- Output: `backend/evaluation/results/<date>_<suite>_<split>.json` with commit hash, corpus fingerprint
  (row counts and a hash of the record ID list), seed, per-method metrics and intervals.
- `python -m evaluation.run --smoke` runs on `tests/fixtures/` in seconds for CI.

### 5.6 Discipline

Follow section 6 of the contracts. In particular: choose everything on 2024, touch 2025 once per method version,
and report a method that loses.

---

## 6. Work packages

Each is done when its acceptance check passes in CI or is shown to Umar, and the knowledge bank is updated.

| ID | Tier | Work | Accepted when |
| --- | --- | --- | --- |
| WP-U0 | Must | Corpus builder: extend `scripts/fetch_sdr_data.py` with `--years 2023 2024 2025`, the four coded columns, `correction_pairs.csv`, `splits.json`, an updated `docs/dataset_profile.md`. Keep producing the two existing staging files unchanged. | From a clean checkout the files appear; counts are within the expected range in contract 4.4; a test on a fixture CSV covers citation parsing, tail mismatch and `part_change`. |
| WP-U1 | Must | Freeze B0. Implement B1 behind `mode=mid_fixed`. Replace the vacuous exclusion tests. | New tests fail on B0 and pass on B1. |
| WP-U2 | Must | `common/faa_text.py`, `retrieval/text.py`, `docstore.py`, `bm25.py`; `evaluation/datasets.py`, `protocol.py`, `metrics.py`, `run.py`; methods B0 to B2. | The toy BM25 test, the leak test, and a results file for B0 to B2 on the 2024 split. |
| WP-U3 | Must | `dense.py`, `scope.py`, `fusion.py`, `ranker.py`; methods B3 to B5; the embedding model comparison. | Results for B0 to B5 on 2024; then one run on 2025, committed. Under 30 minutes on a 16 GB laptop with embeddings cached. |
| WP-U4 | Must | `service.py`, the retrieval routes, `RETRIEVAL_MODE`, lazy refresh, health reporting, latency measurement. | Contract tests for each endpoint in memory mode; the latency numbers written to a decision record. |
| WP-U5 | Must | Graph migration and memory-store equivalents; additive `/api/graph/overview` option. | Running it twice changes nothing the second time; contract tests on both stores. |
| WP-U6 | Must | Evaluation routes and table `evaluation_runs`; Evaluation Lab and evidence search pages. | Component tests; the Lab shows the committed 2025 results. |
| WP-U7 | Should | `evaluation/fit.py` and B6; the ablation table; RQ3; case replay; `breakdown` in the interface. | Results committed; replay works for any 2025 pair. |
| WP-U8 | Stretch | B7; the three-year corpus on staging. | Agreed with Umar first. |

---

## 7. Stop and ask Umar

These are his decisions. Prepare the evidence, then wait.

1. The abbreviation list.
2. The definition of relevance in suite A, if you think it should change.
3. The embedding model.
4. Any second look at 2025 data.
5. Anything that touches staging, including running a migration.
6. Any change to a response field that V3 reads (contract 4.2).
7. Any new dependency.

Things only Umar does, which you support with tooling but never write for him:

- The one-page benchmark protocol note, written before WP-U2.
- Reading 100 narratives for the abbreviation list.
- Reading 30 failures of the best method and classifying them by cause.
- The report sections: retrieval design and rationale, protocol, results, error analysis, FYP-2 evaluation plan.

---

## 8. Do not

- Import from `backend/integrity/` or `backend/investigation/`, except `integrity.validity` through the wrapper in contract 4.1.
- Change `api/routes/diagnostics.py`, `agents/maintenance_agent.py` or any file you do not own.
- Call a language model anywhere in retrieval or ranking.
- Describe a score as a probability.
- Add `torch`, a vector database or a second chart library.

---

## 9. Report back after each work package

1. What you built, by file.
2. The acceptance evidence: test names, command output, the results file path.
3. Anything in this guide that turned out to be wrong.
4. Knowledge-bank files you updated and any decision record you added.
5. A two-line AI-assistance note for the pull request.

---

## 10. Reading for Umar

- Robertson and Zaragoza (2009), *The Probabilistic Relevance Framework: BM25 and Beyond*.
- Cormack, Clarke and Buettcher (2009), *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods*.
- Reimers and Gurevych (2019), *Sentence-BERT*.
- Karpukhin et al. (2020), *Dense Passage Retrieval for Open-Domain Question Answering*.
- Brundage et al. (2021), *Technical language processing: Unlocking maintenance knowledge*.
- Aamodt and Plaza (1994), *Case-Based Reasoning: Foundational Issues, Methodological Variations, and System Approaches*.
