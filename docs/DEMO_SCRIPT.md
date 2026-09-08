# Halite Demo Script & Contingency Plan

This document details the procedures for executing the live demonstration of the Halite Maintenance Conflict Engine and contingencies for failure modes.

## Demo Execution Mode & Latency
- The system currently executes a single LLM classification pass per conflict check via `process_record`.
- During the live single-record latency test, the **first successful call took 22.72s**. Subsequent calls immediately hit the Groq 429 rate limit (Limit 200000 TPD exhausted) and failed in ~2.1s.
- Because a single pass takes >20s under normal load (or fails completely under rate limits), the engine cannot practically use 5x self-consistency for the live demo. The existing single-pass implementation is already the `--fast` mode.

## Fallback Procedure for `429 Too Many Requests`
In the event that the LLM API quota is exhausted (e.g., Groq returns a `429 Too Many Requests`) during the demo:
1. **Explain the Limitation**: Clearly state to the defense committee that the system relies on an external LLM provider whose rate limits (200,000 tokens per day) have been exceeded due to the heavy evaluation runs.
2. **Fail Loudly Demonstration**: Show how the system fails loudly via `RuntimeError` rather than silently swallowing the error, which is a required design constraint for the system.
3. **Demonstrate Deterministic Logic**: Walk through the non-LLM components of the adjudication logic (Part Agreement, Recency Advantage, Authority Advantage) which execute reliably outside the LLM constraints.

## Database Considerations
The graph database is currently configured via `config.py` and `docker-compose.yml`.
If Neo4j is unavailable locally (e.g., Docker not installed), the system will use its in-memory graph repository fallback or should be run with a remote Neo4j AuraDB instance via the `NEO4J_URI` environment variable.
