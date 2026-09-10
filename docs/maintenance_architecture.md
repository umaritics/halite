# Halite Maintenance Domain Architecture

This document describes the architectural implementation of the Maintenance Domain (field-service records) alongside the existing Software Engineering domain in the Halite system.

## 1. Multi-Domain Registry Architecture

The system uses a Domain Registry (`backend/domains/registry.py`) to decouple core business logic from domain-specific graph traversals and terminology. 

- **Domain Adapters:** Each domain implements the `DomainAdapter` interface. The `SoftwareDomainAdapter` and `MaintenanceDomainAdapter` define domain-specific labels (e.g., `Component` vs `Asset`), edge types, and rules for calculating source authority and semantic uniqueness.
- **Dynamic Routing:** API endpoints use the domain adapter to fetch data from the graph dynamically. This ensures that the backend can serve both domains simultaneously without duplicating route logic.
- **Strict Isolation:** The existing software-engineering domain is untouched. All regression tests for the software domain continue to pass, proving that the maintenance integration successfully avoids contaminating or breaking the base system.

## 2. Graph Schema Extensions

To represent maintenance records, the Neo4j schema (and its in-memory fallback equivalent) was extended with new nodes and edges:

- **`Asset` Nodes:** Represents a physical aircraft. It is uniquely identified by its tail number (`RegistryNNumber`), along with fields for make, model, and serial number.
- **`ServiceRecord` Nodes:** Represents an FAA Service Difficulty Report (SDR). Nodes are keyed by their `OperatorControlNumber`.
- **`ABOUT` Edges:** Links a `ServiceRecord` to the `Asset` it applies to.
- **`PRECEDED_BY` Edges:** Links a `ServiceRecord` to the chronologically prior record on the exact same asset, creating a continuous historical timeline for every aircraft in the fleet.

## 3. Conflict Engine Workflow

The Maintenance Domain introduces a specialized conflict engine (`backend/services/conflict_engine.py`) to detect and adjudicate relationships between maintenance reports. 

The pipeline works in a three-stage process:
1. **Candidate Retrieval (Heuristics):** Retrieves the historical records for the asset and scores them based on heuristic weights (e.g., `same_part_name`, `same_jasc_code`, temporal proximity). Only the highest-scoring candidates are passed to the LLM to conserve API tokens and reduce latency.
2. **Classification (LLM):** The Groq LLM evaluates the text of the new record against the prior record. It is strictly prompted to return a JSON payload with a discrete label (`no_conflict`, `scope_disjoint`, `supersedes`, `partial_supersedes`, `contradicts`) and a short rationale.
3. **Adjudication & Confidence:** An evidence-based scoring function computes a confidence score using a combination of LLM output, source authority, explicitly cited "SUPPLEMENTAL REPORT" language, and heuristic part agreement.
   - If `confidence >= threshold`, the record is automatically routed (e.g., marked `auto_accepted`).
   - If `confidence < threshold` or the label implies a high-risk contradiction, the record is flagged for human intervention (`needs_review`).

## 4. LLM Fallback and Graceful Degradation

The system ensures reliability in production by failing gracefully if the LLM is unavailable:

- **Strict Status Tracking:** The `GroqService` monitors its connection status (`is_live`). If an API call fails or the API key is not configured, it tracks the failure and triggers the fallback path.
- **Silent Degradation Prevention:** Masked failures are strictly forbidden. When the LLM is unavailable, the conflict engine safely aborts the conflict detection phase and routes all records directly to the human review queue (`needs_review`). 
- **Telemetry:** The system logs `fallback_invocations` to the `/api/health` endpoint, ensuring that operators are explicitly aware of degraded performance and can take action.
