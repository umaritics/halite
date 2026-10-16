# Usman + Umar Mid-I integration audit

Audit date: 2026-10-16<br>
Integration branch: `integrate/mid1-main`<br>
Inputs: `origin/usman@3788ae4`, `origin/umar/mid1-graph-diagnostics@4d96e5b`<br>
Scope: combine and verify Usman/Umar work; do not modify Shahmeer-owned React code/tests.

## Verdict

Usman and Umar backend work is integrated and locally verified. Umar's U1–U5
diagnostic work remains intact. Usman's maintenance list N+1 is replaced by a
single repository aggregation, generated runtime artifacts are no longer
tracked, and staging smoke is now blocking rather than advisory.

This is **not a claim that the three-member Mid-I delivery is complete**.
Shahmeer's Review Queue mock and Service Records history fan-out remain open.
The production frontend build passes, but the current frontend suite remains
12 passed / 1 failed on the already documented missing `getRecord` mock.

## Rubric mapping

| Mid-I rubric evidence | Current evidence | Verdict |
| --- | --- | --- |
| Live core module + failure cases | Maintenance ingest/review and diagnostic routes; 404/422/503 paths covered | PASS for Usman/Umar scope |
| Requirements and acceptance checks | Endpoint contracts and measurable assets latency/query-count target in `10_perf_assets_api_handoff.md` | PASS for owned scope |
| Design evolution | Current knowledge-bank artefacts match code; the accompanying Mid-I report addendum classifies embedding/cosine retrieval as planned and lexical/Jaccard retrieval as implemented | PASS for Usman/Umar scope |
| Repository/member evidence | Separate Usman/Umar branches and meaningful commit histories retained, then merged | PASS |
| Systematic tests | Backend **122 passed, 18 skipped**; skips are explicit unavailable-Neo4j parameterizations | PASS |
| Reproducible implementation docs | Setup, staging, API, diagnostics, ownership, and handoff files are versioned | PASS |
| Tool/dependency/risk disclosure | Engineering docs and the accompanying report addendum disclose Neo4j/Aura, Groq, OpenAI Codex assistance, review responsibility, privacy, cache, latency, and no-fabrication constraints | PASS for known Usman/Umar integration usage |
| Complete team UI gate | Review Queue test mock and Service Records request fan-out are Shahmeer-owned and still open | PENDING |

## Changes completed in this integration

1. Merged both member branches without rewriting history.
2. Added `list_assets_with_counts()` with one Neo4j aggregation and one-pass
   memory behavior.
3. Added API and repository regression tests that prevent the N+1 pattern.
4. Applied the documented Usman hygiene work: ignore and untrack coverage,
   runtime caches, and local debug output.
5. Made staging assets smoke blocking and bounded it to 30 seconds.
6. Validated the manual log-line input before interpolation into the SSH
   command and used constant-time comparison for the ops token.
7. Updated the knowledge bank and performance handoff with the new contract.
8. Made conflict/diagnostic caches failure-tolerant so removing generated
   cache files does not make a clean or read-only checkout fail.

## Executed verification

| Command | Result |
| --- | --- |
| `python -m pytest -p no:cacheprovider -q` | **122 passed, 18 skipped in 5.85s** |
| `npm test -- --run` | **12 passed, 1 failed** — known Shahmeer-owned `getRecord` mock |
| `npm run build` | **PASS** — 857 modules transformed |
| `git diff --check` | Run before commit/push; must pass |

`-p no:cacheprovider` is required only in this restricted Windows worktree
because its ACL blocks Pytest's cache temp-directory creation. It does not
skip tests or alter application behavior.

## Remaining owner actions

### Report handling

- `15_report_mid1_addendum.md` is the editable source for the controlling
  addendum distributed with `docs/Halite_FYP_Report.pdf`; keep its generated
  `Halite_FYP_Report_Mid1_Addendum.pdf` synchronized.
- Treat `F26_FYP1_Mid_Report_LaTeX_Complete.pdf` and its ZIP as the blank
  university template/reference, not as a completed submission.
- Each member must add any additional AI assistant they personally used before
  final university submission; this audit discloses the verified Codex use.

### Shahmeer

- Complete `06_frontend_review_queue_handoff.md` without skipping the test.
- Stop the all-assets history fan-out described in
  `10_perf_assets_api_handoff.md`; initial Service Records load should use no
  more than two API calls.
- Re-run Vitest and the production build, then provide the branch for final
  integration.
- Review the locked frontend dependencies. `npm audit --omit=dev` currently
  reports one high and two moderate production advisories (Axios and React
  Router); upgrade through the frontend-owner branch and rerun tests/build.

### Release verification after this integration is deployed

- Time `GET /api/maintenance/assets` against staging; target is under 2–3
  seconds and one graph query.
- Confirm `/api/health` and `/api/ops/version` report the deployed integration
  SHA, Neo4j mode, and the real maintenance corpus.
- Obtain the final independent reviewer/supervisor sign-off required by the
  university rubric.
