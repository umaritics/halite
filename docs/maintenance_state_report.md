# State of the Halite Maintenance Conflict Engine: Comprehensive Report

This report evaluates the recent agent critique regarding the Halite Maintenance Conflict Engine, verifying its claims against the current codebase and documentation, and outlines the current state of the maintenance side of the project.

## 1. Verification of Critique Claims

The critique raised four primary points regarding the documentation, architecture, and evaluation metrics of the project. Every single claim made in the critique has been verified as **highly accurate** based on the existing files.

### 1.1 The "Misdiagnosis Density" Story is Real and Documented
**Critique Claim:** `docs/misdiagnosis_density.md` shows a 65.2% rate of corrections naming a different part, based on 141 ground-truth pairs from FAA SDR data. The G0 spec fixed thresholds beforehand, failed them, and skipped G2 honestly.
**Verification (Accurate):**
- `docs/misdiagnosis_density.md` confirms exactly 141 ground truth pairs were measured.
- The document explicitly lists:
  - Different `PartName`: 92 (**65.2%**)
  - Different `JASCCode`: 60 (**42.6%**)
  - Different `PartLocation`: 67 (**47.5%**)
- The methodology was indeed pre-registered: "The thresholds were stated in the G0 specification before this measurement was run and have not been adjusted."
- As a result of failing the threshold, the document notes: "**Skip G2** — both thresholds were not met."

### 1.2 The True Purpose of the Graph is Candidate Reduction
**Critique Claim:** `conflict_engine.py` (`find_candidate_pairs`) explicitly states the graph is used for candidate-set reduction (cutting 11,628 all-pairs comparisons on a 153-record asset to just 25 scored priors), not memory or centralization.
**Verification (Accurate):**
- `conflict_engine.py` (lines 106-107) explicitly documents this: "Only searches within the same asset's graph-constrained history — this is the architectural reason a graph is used (not all-pairs comparison)."
- The engine uses `PAIR_WEIGHTS` (same part name, JASC code, location, within 30 days) to score history and returns exactly `MAINT_MAX_CANDIDATES = 25` items.
- `DEMO_SCRIPT.md` confirms the "813SK" asset has 153 records, which would otherwise require massive computational overhead for all-pairs comparison.

### 1.3 Evaluation Thresholds are Overfitted
**Critique Claim:** The threshold is fitted on the evaluation set (`evaluation_results.md` sweeps and picks 0.50 by max F1 on N=10 data), but `DEMO_SCRIPT.md` calls it "recalibrated."
**Verification (Accurate):**
- `evaluation_results.md` clearly states it was run on a subsample of `N_gt=5, N_neg=5` (Total N=10).
- In the "Threshold Sweep" section, it recommends `0.50` purely based on the max F1 score achieved on those exact 10 records.
- `DEMO_SCRIPT.md` reads: "Recalibrated Threshold: `0.50` (selected via max F1 criterion on E1 evaluation)". This confirms that the threshold was fitted and reported on the exact same tiny sample without a held-out validation set.

### 1.4 Auto-Accept is Practically Unreachable (Confidence Ceiling)
**Critique Claim:** Confidence distribution maxes at 0.650. `WEIGHTS_NO_CITATION` sums to exactly 1.00, so a 0.65 score means every signal fired except the heaviest one (0.35). The default threshold in code is 0.72, making auto-accept mathematically unreachable in these conditions.
**Verification (Accurate):**
- `evaluation_results.md` shows the maximum confidence achieved in the evaluation (positive partition) was `0.650`.
- `conflict_engine.py` defines `WEIGHTS_NO_CITATION` which indeed sums exactly to `1.00` (`0.35 + 0.25 + 0.15 + 0.15 + 0.10`).
- If the LLM classification signal (`classification_supersedes` = 0.35) fails or any combination leaves you at 0.65, you fall strictly under the `MAINT_CONFIDENCE_THRESHOLD` which is hardcoded to `0.72` by default.
- As a result, in the evaluation (threshold=0.72), the engine yielded `0 TP`, confirming that auto-accept is effectively blocked under current normal conditions.

---

## 2. Current State of the Maintenance Domain (Full Report)

Based on the codebase and the verified critique, the Halite Maintenance Conflict Engine currently stands as a functionally complete but defensively tuned prototype.

### Architecture & Strategy
- **Graph as a Search Space Reducer:** The system relies on Neo4j strictly to constrain the search space. By limiting candidate pairs to a single asset's history and applying lightweight heuristics (`PAIR_WEIGHTS`), it efficiently narrows down potentially thousands of comparisons per asset to the top 25 candidates before invoking the LLM.
- **LLM Classification:** The engine uses an external LLM (`openai/gpt-oss-120b` via Groq) to evaluate the top candidate pair. It supports a robust "Fast Mode" with self-consistency passes (majority voting across up to 5 generations) and employs intelligent JSON parsing for the classification labels.

### Confidence Scoring & Routing
- The engine uses a dual-weighted scoring system (`WEIGHTS_WITH_CITATION` vs `WEIGHTS_NO_CITATION`), heavily prioritizing explicit supersession language (e.g., "SUPPLEMENTAL REPORT FOR").
- The system evaluates evidence based on recency, source authority, part/JASC agreement, and temporal proximity (within 30 days).
- **The Threshold Bottleneck:** The default threshold of `0.72` is extremely restrictive. Because records lacking explicit citation fall back to `WEIGHTS_NO_CITATION`, achieving a score of >= 0.72 requires nearly every single heuristic to trigger perfectly. This results in an empty "auto_accepted" queue, pushing almost all records to "needs_review".

### Evaluation & Integrity
- **Honest Methodology:** The project demonstrates remarkable academic integrity. In `docs/misdiagnosis_density.md`, a pre-registered hypothesis failed its gate, and this was honestly reported ("Skip G2"). The 65.2% misdiagnosis rate on 141 ground-truth pairs is arguably the most valuable empirical finding in the project.
- **Evaluation Limitations:** The current `evaluation_results.md` relies on an extremely small subsample (N=10). The recommended threshold of 0.50 in the demo script is directly fitted to this sample, which represents a critical vulnerability if scrutinized in a defense setting without acknowledging the lack of a held-out validation set.

### Demonstration Readiness
- The system is well-prepared for live demonstrations (`DEMO_SCRIPT.md`), featuring robust contingencies for LLM rate limits (`429 Too Many Requests`).
- It implements file-based response caching (`backend/data/cache.json`) that can drop latency from ~8.0s to ~2.0s, ensuring the presentation of the "813SK" asset (153 records) remains smooth and reliable.

## Summary
The system's strongest asset is its empirical measurement of aviation maintenance misdiagnosis (65.2% first-diagnosis error rate) and its architectural use of graphs for scalable candidate reduction. However, care must be taken during presentation to preemptively address the overfitted 0.50 threshold on the tiny N=10 evaluation set, and to defensively justify why the default 0.72 threshold effectively disables auto-accepts for standard records.
