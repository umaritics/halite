# Maintenance Domain: System Handoff & Architecture

This document serves as a comprehensive handoff for the Maintenance Domain of the Halite system. It details the data structures, graph topology, evaluation parameters, and key architectural findings from our implementation.

---

## 1. Graph Topology & Schema

The maintenance domain uses a dual-domain graph architecture (isolated from the software domain) stored in Neo4j. The graph represents historical Service Difficulty Reports (SDRs) and their relationships to physical assets and components.

### Nodes
- **`Asset`**: Represents a specific aircraft tail number or fleet vehicle (e.g., `813SK`, `508AE`).
- **`ServiceRecord`**: Represents a specific historical maintenance job, technician report, or SDR. Contains metadata such as the symptom, action taken, and timestamp.
- **`Component`**: Represents the physical part or system that was inspected or replaced (e.g., `DRAG ANGLE`, `IDG`, `BATTERY PACK`).

### Edges (Relationships)
- **`[:LOGGED_AGAINST]`**: Connects a `ServiceRecord` to its parent `Asset`.
- **`[:INVOLVES]`**: Connects a `ServiceRecord` to the specific `Component`(s) that were repaired or inspected.
- **`[:SUPERSEDED_BY]`**: (Conflict Engine) Connects an older `ServiceRecord` to a newer one if the older fix is deemed ineffective or directly replaced by the newer action.

---

## 2. Key Components & Features

### The Conflict Engine
Monitors newly ingested technician reports and compares them against historical fixes. 
- Analyzes recent maintenance history for the same asset.
- Flags "Auto Accepted" records if they align with past fixes, or marks them for manual review if they deviate or suggest a recurring failure.
- Tracks `history_size` and `candidates_considered` to calculate confidence scores.

### The Diagnostic Ranker
Powers the `/api/maintenance/diagnose` endpoint.
- Takes an `Asset` ID and a symptom string.
- Queries the graph for prior occurrences of similar symptoms on the specific asset (Asset History) and across the entire fleet (Fleet History).
- Ranks candidate components based on a lift-based scoring metric.
- Includes a **Server-Side Citation Validator** that explicitly verifies all LLM-generated record IDs against the live Neo4j database, stripping out any hallucinations before returning the payload to the UI.

---

## 3. Findings & Testing Parameters

### Ingestion & Corpus
- **Dataset**: Tested on 2,000 historical SDR records (`data/processed/sdr_poc_corpus.csv`).
- **Parameters**: 
  - `MAINT_CONFIDENCE_THRESHOLD = 0.72` (Calibrates the pruning line for auto-accepting records).
  - `MAINT_MAX_CANDIDATES = 25` (Limits the number of historical records the LLM evaluates during conflict detection to prevent context saturation).

### Evaluation Results
- **Misdiagnosis Density / Lift Dependency (G0 / G2)**: We ran `measure_misdiagnosis_density.py` to evaluate the graph's ability to mine component dependencies purely from co-occurrences in service records. 
  - **Finding**: The results failed to meet the required confidence thresholds for automated component-dependency graph mining (G2). 
  - **Action**: G2 was intentionally skipped. The diagnostic ranker instead relies purely on symptom-to-component historical frequencies (lift scores) rather than inferring complex physical component trees. This is fully documented in `docs/misdiagnosis_density.md`.
- **Demo Performance**: The diagnostic retrieval process caches effectively, taking warm queries down to ~2-3 seconds for live demos, bypassing expensive LLM graph-extraction hops when possible.

---

## 4. Operational Guidelines

- **Isolation**: The maintenance domain logic is strictly isolated from the software domain logic via `domain === 'maintenance'` routing in the frontend and distinct API controllers in the backend.
- **Neo4j Requirement**: The maintenance features (especially the Diagnostic Ranker's server-side citation validation) rely heavily on Neo4j Cypher queries. They will *not* function correctly in `DEMO_MODE=true` (in-memory graph). `NEO4J_URI` must be bound and `DEMO_MODE=false`.
