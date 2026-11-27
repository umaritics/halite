# Coded report fields integration — separate review branch

The user authorized preparation and testing: **“Prepare and test the separate
review branch”**, after being told that master-plan §4.11 says backend preparation
must merge first and requires Shahmeer review. This exception covers local review
preparation/testing. It does not represent owner review, merge or staging work.

Branch: `codex/usman-coded-fields-integration`, stacked on question-core PR #32.
The original `CODED_FIELDS_INTEGRATION.patch` is applied: exactly twelve additive
lines across `agents/maintenance_agent.py`, `graph/repo/core.py` and
`graph/memory/core.py`. The fields are raw strings, stripped of surrounding space:

| FAA column | Graph field |
| --- | --- |
| StageOfOperationCode | stage_of_operation |
| HowDiscoveredCode | how_discovered |
| NatureOfConditionA | nature_of_condition |
| PrecautionaryProcedureA | precautionary_procedure |

Missing optional codes default to empty strings. Existing duplicate ingest stays
unchanged, including repair of ABOUT links; therefore older records require the
separate backfill. No code descriptions or integer coercion enter ingestion.

## Backfill procedure for review

`backend/scripts/backfill_coded_fields.py` reads original FAA CSV or CSV.gz with
all five required columns. It validates the complete source before graph access,
rejects malformed/blank IDs and contradictory duplicate IDs, records the file
SHA-256, and matches only exact record IDs. Identical duplicates are counted.

Use the configured Neo4j connection after the database owner has made a backup
and paused competing writes. Dry-run is the default:

```bash
python scripts/backfill_coded_fields.py --csv /absolute/path/to/original.csv --dry-run
python scripts/backfill_coded_fields.py --csv /absolute/path/to/original.csv --apply
python scripts/backfill_coded_fields.py --csv /absolute/path/to/original.csv --dry-run
```

Retain each JSON output. It reports matched/missing/unchanged records, field
changes with prior values, conflicting nonempty values and the input fingerprint.
Only missing/empty fields receive nonempty source values. Source blanks cannot
erase stored codes. Existing disagreements remain unchanged and appear explicitly
for owner review; they are not silently “fixed”. A write/verification error exits
nonzero, may follow earlier successful updates, and is safe to retry idempotently.
This is a resumable operator tool, not an atomic multi-record migration.

Umar still owns the real staging backup/backfill; Shahmeer review and merge remain
pending. No shared staging mutation was performed here.

## Executed proof

Tests exercise actual CSV ingestion through memory and Neo4j, leading zero codes,
missing codes, unchanged duplicate ingestion and history reads. Backfill checks
cover dry-run, missing IDs, conflicts, preservation of unrelated fields, repeat
apply, gzip input, invalid sources, CLI validation-before-connect/cleanup and
explicit write failure. The standalone proof launches the actual CLI three times
against a uniquely identified synthetic old node in disposable local Neo4j:
`evidence/phase5-coded-fields-cli.json`. Its second apply changes zero records;
no unrelated record or graph link is changed. See integration backend test/JUnit
and lint evidence for the full suite result.
