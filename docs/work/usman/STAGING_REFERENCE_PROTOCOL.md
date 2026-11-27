# Real staging-reference measurement

This workflow collects real outputs from staging's existing `phi4-mini`. It uses
the frozen model-comparison runner and its twenty primary prompts plus ten paired
no-evidence prose calls. It does not claim M4 measurements, human support accuracy
or an interactive-model decision. No local model is launched on Usman's laptop.

## Before execution

The implementation must be merged and pass full CI on the exact `main` revision.
Wait for that revision's normal backend deployment. The workflow requires the
same public live revision before measurement, including Neo4j, PostgreSQL,
private local-model provider, authentication and a loaded maintenance corpus.

Run **Actions → Measure staging model reference → Run workflow**, choose `main`
and enter `MEASURE`. This is an explicit research operation under the existing
staging environment. It does not deploy, change model settings or create data.
The user's standing instruction to complete and merge the work authorizes this
reference run; its existence is not a teammate or supervisor approval.

## Private transport and resources

- The runner reads only the deployed model configuration and Docker metadata over
  SSH. It checks the existing pinned Ollama image, private network, absence of
  published host ports and documented 4 GiB / two-CPU limits.
- The API key remains in memory and the temporary runner process environment.
  It is not printed, put in arguments, copied to files or retained as an artifact.
  SSH metadata commands use structured argument quoting. The client requires a
  verified known-hosts file; the hosted workflow populates it using the existing
  team's SSH keyscan procedure.
- A temporary `127.0.0.1:11435` listener on the hosted runner forwards over SSH
  to the existing container's private address. No host, Caddy or Docker port is
  opened on staging. The tunnel closes even if measurement fails.
- Only the exact installed tag corresponding to the configured `phi4-mini` is
  permitted. No model pull, install, fallback, new candidate model or local
  inference occurs. Requests use the existing comparison's 4,096 context,
  700 prediction-token cap, temperature zero, seed 1729 and serial ordering.
- This is a shared, resource-limited server. Wall timings include SSH/network,
  queueing and loading. They cannot be compared as hardware-matched M4 latency.

## Output and acceptance

The `staging-model-reference` artifact contains:

- public health before/after and explicit operation status;
- safe server-placement/resource provenance, distinguishing GitHub runner
  hardware from the actual staging inference container;
- the unchanged comparison runner's manifest, copied frozen packet, excluded
  warmup, raw response journal, results and generated `COMPARISON.md`.

Afterward the deployed revision, corpus count, model container identity and
restart count must be unchanged. Provider errors and interrupted attempts remain
in the artifact; they prevent successful full-run acceptance and are never
silently retried or removed. A failed preflight makes no model calls. Use the
specific retained run handle and failure stage to investigate before deciding
whether a fresh deliberately repeated measurement is justified.

Valid fact JSON is output-schema validity, not measured extraction accuracy.
Citation membership and unapproved uncited sentences are observable diagnostics,
not proof of false aircraft facts. Without accepted grounding thresholds, semantic
support rates remain unavailable. The same model's paired no-evidence generations
can later receive blinded human evaluation; their mere collection does not
complete that evaluation or the two-independent-reviewer requirement.

Runtime source: `backend/investigation/experiments/staging_reference.py`.
Workflow: `.github/workflows/staging-model-reference.yml`.
Tests use only explicit synthetic transports and never contact staging.

## Observed deadline failure and second-run procedure

The original 180-second run completed its journal but failed acceptance with six
evidence-prose timeouts. Preserve that full attempt and its denominator; see
STAGING_REFERENCE_RESULTS.md. A deliberately separate run uses a 600-second
client deadline and a 330-minute workflow bound. Frozen prompts, generation
parameters, seed, model and resource caps remain unchanged. This is an operational
completion study, not retrospective improvement of the original deadline result.
Postflight now precedes provider-error rejection, and safe final model metadata
is retained even when collected attempts contain errors. The strict success gate
remains; failed-attempt verification cannot label a failed measurement accepted.
