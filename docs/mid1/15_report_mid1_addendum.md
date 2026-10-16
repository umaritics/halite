# Halite FYP-I Mid Report Addendum

Date: 2026-10-16<br>
Applies to: `docs/Halite_FYP_Report.pdf`<br>
Purpose: implementation-status correction and responsible tool disclosure for the FYP-I Mid assessment.

## 1. Controlling implementation-status correction

This addendum controls wherever the report's planned architecture could be
read as a claim about the current FYP-I Mid implementation.

Section 10.4 describes embedding vectors, cosine similarity, and hybrid
retrieval. Those are **planned FYP-I Final/FYP-II design directions**, not
features implemented in the Mid prototype. The implemented Mid retrieval is:

- graph-bounded asset history and fleet record retrieval from Neo4j;
- lexical/Jaccard matching over the bounded candidate set;
- deterministic ranking with documented asset-history, fleet-match, and
  superseded-record weights;
- stable tie-breaking by score, evidence count, and component name;
- graph validation of cited FAA record identifiers;
- controlled 404 for missing history and 503 when live inference is
  unavailable.

The current score is an exploratory ranking aid, not a calibrated probability.
Conflict-detection F1 is not diagnostic accuracy. Embedding or hybrid retrieval
must not be demonstrated or claimed until it exists in code and has executed
tests/evaluation evidence.

## 2. Implemented FYP-I Mid scope

The verified Usman/Umar backend slice includes FAA record ingestion,
asset/history APIs, conflict review, bounded graph retrieval, deterministic
diagnostic ranking, citation validation, failure-safe LLM boundaries, CI,
Docker/Neo4j smoke verification, staging deployment support, and operational
health/version evidence. The integration audit recorded 122 passing backend
tests and 18 explicit Neo4j skips in a no-Neo4j local environment.

Shahmeer-owned frontend completion remains separately tracked in
`docs/mid1/14_usman_umar_integration.md`.

## 3. External services, frameworks, and tool-assisted development

- **Neo4j/Aura** stores and queries the maintenance graph. The system discloses
  graph mode through `/api/health`; synthetic CI evidence is not represented as
  full-corpus production evidence.
- **Groq API and its configured language model** generate explanations and
  conflict classifications. The model does not determine the deterministic
  ranking. Missing live inference fails explicitly, and generated FAA-shaped
  citations are validated against graph records.
- **FastAPI, React, Vite, Docker Compose, GitHub Actions, and Vercel/staging
  infrastructure** support the application, testing, build, and deployment
  workflow.
- **OpenAI Codex** assisted the 2026-10-16 integration audit by inspecting
  repository state, proposing scoped edits, running tests/builds, and drafting
  engineering documentation. The students remain responsible for reviewing,
  understanding, testing, defending, and accepting every committed change.
- Any additional member-specific AI or development assistants used while
  preparing the final submission must be added to this disclosure by that
  member; absence from this list must not be treated as permission to omit use.

## 4. Privacy, safety, and limitations

API keys, SSH keys, ops tokens, and ignored FAA working files are not committed.
Runtime/model caches are ignored and optional; inability to persist a cache
does not break core behavior. LLM output can hallucinate, so citations are
validated and unsupported identifiers are marked unverified. The corpus is
historical maintenance evidence and does not authorize an autonomous repair
decision. Human review remains required.

The Mid prototype does not establish calibrated diagnostic accuracy,
airworthiness approval, production multi-tenancy, or replacement of qualified
maintenance personnel. Dependency advisories, frontend completion, live
staging timing, and supervisor sign-off remain visible release/assessment
checks rather than hidden claims.

## 5. Evidence references

- `docs/mid1/08_umar_progress.md`
- `docs/mid1/10_perf_assets_api_handoff.md`
- `docs/mid1/11_u2_real_data_retrieval.md`
- `docs/mid1/12_u4_u5_diagnostics_handoff.md`
- `docs/mid1/13_u3_deterministic_ranking.md`
- `docs/mid1/14_usman_umar_integration.md`
- `knowledge/context/modules/diagnostics.md`
- `knowledge/context/modules/maintenance_api.md`
