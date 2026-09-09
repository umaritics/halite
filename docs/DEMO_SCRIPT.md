# Halite Maintenance Domain — Demo Script & Contingency Plan

This document details the procedures for executing the live demonstration of the Halite Maintenance Conflict Engine and contingencies for failure modes.

## Demo Assets
The following three assets have genuinely long histories and provide the best demonstration of the timeline and conflict detection UI:
- **813SK**: 153 records
- **508AE**: 118 records
- **860NW**: 113 records

## System Configuration & Parameters
- **Pinned Model**: `openai/gpt-oss-120b`
- **Recalibrated Threshold**: `0.50` (selected via max F1 criterion on E1 evaluation)

## Performance and Contingencies (`429 Too Many Requests`)

The system relies on an external LLM provider whose rate limits may be exhausted during demonstration due to prior evaluation runs.

1. **Response Caching (Primary Contingency)**:
   The system implements file-based response caching (`backend/data/cache.json`) keyed by `(new_record_id, prior_record_id, model)`.
   **Pre-warm Command**: Run the following before the demo to ensure zero API calls are made during the live presentation:
   ```bash
   curl -X POST -H "Content-Type: application/json" -d "{\"record_id\":\"SWIA2025122876590\"}" http://localhost:8000/api/maintenance/records
   ```
   *Note: With cache warmed, response latency drops from ~8.0s to ~2.0s.*

2. **Fast Mode Toggle**:
   The engine's self-consistency passes can be reduced to 1 by setting `MAINT_SELF_CONSISTENCY_PASSES=1`. 
   Trade-off: Latency drops from ~8.0s to ~3.2s, with identical confidence output (0.55) on the demo record. This toggle is available for live uncached execution if required.

3. **Fallback API Key**:
   The engine automatically switches to `GROQ_API_KEY_FALLBACK` if a `429 Too Many Requests` is encountered.

## Database
The demonstration must run against the live Neo4j database using `NEO4J_URI=bolt://localhost:7687` in the environment. All demonstration paths rely on native Cypher queries which bypass the in-memory fallback store.

## Demo Walkthrough

**Step 10 — The query interface.** A senior technician has a symptom on 813SK. Instead of working the standard protocol in order, they ask the system. It answers from that airframe's 153 records plus fleet-wide matches, returns a ranked inspection order with the evidence behind each rank, and surfaces a rare prior occurrence from months earlier. Every line cites a real record. *The ranking comes from the graph; the language model only phrases it.*

*(Note: Diagnostic queries evaluate under 3 seconds using the internal cache keyed on `(asset_id, symptom, model)`. No explicit pre-warming is required for the live demo.)*
