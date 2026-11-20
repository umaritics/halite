# Coded report fields integration proposal

Status: concrete patch prepared; shared files unchanged in the question-core package. The user explicitly authorized preparation/testing on a separate review branch (“Prepare and test the separate review branch”). The plan's section 4.11
pre-agrees this additive edit but says to apply it after backend preparation
merges and with Shahmeer as reviewer. PR #27 has not merged. The shared-file
preparation exception needs authorization; no review/merge is implied here.

`CODED_FIELDS_INTEGRATION.patch` adds exactly four raw code fields to ingestion
and to both Neo4j/memory creation property lists:
`stage_of_operation`, `how_discovered`, `nature_of_condition`,
`precautionary_procedure`. It changes no identity, ranking, conflict or existing
record values. Existing records need the separately verified idempotent backfill
script; duplicate ingest intentionally remains duplicate-safe.

The patch passes `git apply --check` against this branch. After authorization,
apply and test on its own review branch, with CSV→Neo4j/memory round-trip and
idempotent/dry-run backfill evidence. Umar remains responsible for an actual
staging backup/backfill. Current research uses CSV fields and is independent of
this unmerged shared-file integration.
