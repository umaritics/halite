# Legacy retirement — verified review preparation

Source commit: `5817fd9` (PR #43). [Successful hosted run](https://github.com/umaritics/halite/actions/runs/44882037412).

All CI jobs passed: **440 backend tests**, **279 frontend tests**, Ruff, production
and feature frontend builds, actual disposable Neo4j/PostgreSQL API/session smoke
and Chromium research/source-highlighting flows. Tests for retired contracts were
replaced with route-absence and production-lifespan checks; maintained maintenance,
auth, rate-limit and graph-reset coverage remains.

- Every plan-named software runtime file/root script and software regression suite
  is removed. MaintenanceAgent's five existing method bodies are AST-identical;
  only its constructor/inheritance integration changes.
- Maintenance is the sole/default domain. Retired routes are 404 and absent from
  OpenAPI, including when the obsolete Gitea flag is true. Anonymous and authorized
  calls neither mutate graph data nor invoke model work.
- Actual fresh hosted Neo4j starts empty before fixture ingest; all retired live
  API calls return 404. Real maintenance ingest creates three records, retries
  create zero duplicates, and existing review/diagnostic/session flows pass.
- Production-lifespan unit checks cover memory, connected synthetic Neo4j adapter
  and connection failure fallback; all forbid automatic seed calls and verify close.
  Existing data and ops-protected manual-reset compatibility are preserved.
- Pip selects **64 distributions versus 89 baseline**. Now-unused pypdf/docx2txt
  disappear; pandas/NumPy/requests retain baseline versions and dotenv still works.

Broad backend coverage is **4,656 / 5,851 statements = 79.58%**. The rounded terminal
80% does **not** satisfy the exact 80% target. Meaningful remaining verification
will address that gap separately; no source omissions or denominator exclusions
were introduced.

Evidence is retained in `evidence/phase13-retirement/`: importer preservation,
static audit, raw pip reports/inventory, JUnit, actual runtime proof, current
browser measurements and job/hash metadata. Screenshots remain downloadable from
the linked run artifact; previous source-highlighting screenshots remain in phase11.

This is user-authorized preparation/testing on a separate review branch. Owner
review, merge and deployment remain pending. No staging data was changed.
