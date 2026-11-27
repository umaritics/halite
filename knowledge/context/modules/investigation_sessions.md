---
id: mod-investigation-sessions
title: Persisted investigation sessions
status: active
owners: [Usman]
updated: 2026-11-20
---

# Investigation sessions

`backend/investigation/sessions.py` stores the lifecycle in PostgreSQL (SQLite in
tests). New tables are registered through `db/models/sessions.py`: diagnostic
sessions, ordered turns and one snapshot per turn. Identity tables are unchanged.

## Access

Every lifecycle operation requires a real user principal. Demo, API-key and
ops-token callers cannot access user sessions. Technicians see only their own
sessions in their organisation; supervisors/admins can read all sessions in that
organisation and change only their own. Invisible IDs return 404. Readable but
non-owned sessions reject mutations with 403. Closed sessions are read only.
Summary responses for service/demo callers preserve the preparation endpoint's
empty statistics; real users receive counts from their visible session scope.

## Durable turns

The client sends a message, not authoritative state. The service loads the last
persisted case state and performs inference without an open database transaction.
It then atomically claims the next turn index using a conditional update on
`status=open` and the expected `turn_count`. A competing turn or closure causes
409; no stale response is persisted. Revision, turn and snapshot commit together.
A database failure rolls all three back. Unique `(session_id, idx)` protects the
sequence independently of the application process.

Each turn stores the exact response, including evidence narratives, and its
snapshot stores hypotheses with derived beliefs, their entropy and evidence IDs. Replay does not call a model or
re-read changed graph records. Creation/list/detail/resume/close work across
clients and application engines. Lists use stable `(created_at, id)` cursor
pagination with visibility and status/outcome filters applied in SQL.

## Degraded mode and explicit runtime configuration

The session bridge delegates to the existing Copilot workflow. On a model outage
it supplies a deterministic explanation from the returned ranking/evidence and
retains `llm_status=unavailable`. It never uses canned software-domain responses.
The compatibility stateless Copilot endpoint retains its existing null-reply
outage behavior. With the default runtime configuration, session responses say
`decision=abstain`, `policy_status=not_configured`, `question=null` and
explicit uncalibrated beliefs/entropy and stored rule inputs; see
[investigation_decisions.md](investigation_decisions.md). The measured research
choice does not activate a live policy. `grounding_runtime.annotate_response`
adds saved citation/source/sentence audits; valid citations remain unrated until
accepted thresholds exist. These audits are not human validation or a claim of
calibrated probabilities; see [investigation_grounding.md](investigation_grounding.md).
Structured answers remain refused in the default bridge. The opt-in [managed controller](investigation_live_questions.md) validates saved question IDs/options, updates saved posteriors without graph/model reads and commits through the same transaction.

Quick diagnose adds `allow_degraded=false`; the default 503 contract remains.
Opt-in calls return `explanation=null`, `fallback_explanation`, ranking, evidence
and a warning on a model outage/empty explanation. Valid caches include record
count, active mode, prompt version and the retrieved context fingerprint, so
same-count record/status changes invalidate them. Empty explanations are never
served from cache. Cache writes use an atomic replace; malformed cache shapes
are ignored. Citations/rare-case IDs must be in the bounded evidence shown in the
prompt, not merely elsewhere in the graph.

## Outcomes and reports

Closing requires a non-blank outcome note and optionally records part, JASC and
a graph record reference. Closed sessions with a named outcome part are available
to other verticals through `status=closed&has_outcome=true`. Findings remain user
reports, not adjudicated labels or approvals. The authenticated HTML report
escapes every user/model/evidence value and is available only after closure.
The one-click frontend action was verified in the disposable production build and
integrated through PR48. Owner cross-review remains separate from merge/deployment.

## Verification

`test_investigation_sessions.py` runs against file SQLite and disposable
PostgreSQL schemas, including cross-client/restart replay, real JWT visibility,
concurrency, closure races and transaction rollback. `test_investigation_degraded.py`
checks outages, citation allow-lists and real cache-hit/invalidation behavior.
See `docs/work/usman/WORK_LOG.md` and `flows/FLOW-sessions.md`.

The actual signed-in public read flow passed run44988921561 (PR54 deployment
db574ac); empty history in that run is not lifecycle proof. A separate explicit
`scripts/verify_public_investigation.py` probe uses only the dedicated authorized
account and existing aircraft. It creates one labelled synthetic session, sends
one turn without retry, checks exact saved response/snapshot, closes with no
outcome part, checks the read-only guard and retrieves the printable report.
No corpus, admin or other-user writes occur. Typed VERIFY_SESSION, exact deployed
SHA, fresh evidence directory and in-memory credentials are required. Lifecycle
success and actual live-prose success are distinct recorded checks. The test note
is explicitly not a real maintenance finding or a training part label.

The actual phase27 probe verified creation, exact replay, closure, closed-write409
and authenticated HTML printing, but its live prose timed out. The prepared
runtime fix uses `investigation/prose.py`: at most2,048input bytes,192output tokens
and three prioritized source excerpts. Every full response/snapshot source remains
saved. `prose_context` records actual versus available IDs, prompt identity and
acceptance; a warning makes subset coverage explicit. Citation/sentence membership
uses actual model-supplied IDs only; fallback/structured replies use their own
saved source boundary. Structured answers discard prior model-context metadata.
Quick diagnosis retains its source lists/JSON schema with shorter wording and
512tokens; malformed structured fragments degrade. See the bounded-runtime-prose
decision and PUBLIC_SESSION_VERIFICATION.md; new live acceptance remains pending.

Actual release11beed1 passed mainCI44992947098/deploy44993176097. The
fresh public lifecycle case74c792ce-510c-4c60-addb-a7f441435246 persisted/replayed/
closed/printed correctly but compact model prose still timed out; live success
is not established. Hosted browser44993544541 verified this populated own-case
workspace, exact reload, closure guard and one-click PDF along with real auth,
phone geometry and research parity. PDF visual review found crowded text
at zero-margin page boundaries. Report print CSS now requests A4/16mm margins,
keeps fitting evidence items together and sets paragraph widows/orphans; browser
export honors CSS page size. The correction requires fresh deployed PDF review.
See docs/work/usman/PUBLIC_SESSION_VERIFICATION.md and phase28 raw artifacts.

Final print release: mainCI44994039620/deploy44994297938 passed; public health
confirmed exact6c3cd0d6fbac7a703570894257f0cad738a4e14b and2,079records.
Hosted browser44994441004 passed real own-case replay, closure and one-click
print plus all public read/auth/phone checks, with zero page errors/prohibited
requests. All4exportedPDF pages rendered and visually reviewed; all20record IDs
and20full normalized narratives independently match the saved response. New
PDF SHA2568ec1c3dbdc0830b1d5242de0cc62c1324f0e15a731c513f1103f199a7c0fc839.
A close-up of the original disproved the initially suspected missing glyphs;
the confirmed issue was zero-margin edge crowding. Correction is now visually
accepted. Model availability remains failed on both measured runtime paths.
