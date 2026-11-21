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

## Degraded mode and incomplete decision layer

The session bridge delegates to the existing Copilot workflow. On a model outage
it supplies a deterministic explanation from the returned ranking/evidence and
retains `llm_status=unavailable`. It never uses canned software-domain responses.
The compatibility stateless Copilot endpoint retains its existing null-reply
outage behavior. Until the measured policy package lands, session responses say
`decision=abstain`, `policy_status=not_configured`, `question=null` and
`grounding=null`. It now returns explicit uncalibrated beliefs/entropy and stores
the rule inputs; see [investigation_decisions.md](investigation_decisions.md). No calibrated beliefs or sentence checks are claimed.
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
The one-click frontend action is verified on the shared integration review branch.

## Verification

`test_investigation_sessions.py` runs against file SQLite and disposable
PostgreSQL schemas, including cross-client/restart replay, real JWT visibility,
concurrency, closure races and transaction rollback. `test_investigation_degraded.py`
checks outages, citation allow-lists and real cache-hit/invalidation behavior.
See `docs/work/usman/WORK_LOG.md` and `flows/FLOW-sessions.md`.
