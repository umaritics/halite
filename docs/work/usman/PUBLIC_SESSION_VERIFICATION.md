# Actual public investigation lifecycle and model deadline

Executed one explicitly labelled synthetic case using the authorized dedicated
account against deployed `db574acadd4caf5cf60be45559708c82319711a6`. No corpus,
configuration, administrative or other-user writes occurred. The lightweight
standard-library client made HTTP calls; no local model/browser was launched.

Case: `cbc8d780-9af2-4144-8a21-27cf8209c063`, aircraft `813SK`.
Title: Automated acceptance check - no maintenance finding.
Evidence: `evidence/phase27-public-session/attempt1/`.

| Check | Observed result |
| --- | --- |
| Dedicated account creates its own case | 201; ownership confirmed |
| Single turn, no automatic retry | 200;158.71seconds; historical ranking/evidence and marked fallback saved |
| Independent HTTP replay | Exact response and belief snapshot match |
| Close with explicit test note | Closed; no outcome part, repair or actual finding recorded |
| Closed write guard | Further turn rejected409 |
| Authenticated report | HTML200; test title/outcome note present |
| Deployment/corpus stability | Exact source and2,079records unchanged |
| Logout | Explicitly confirmed |
| Actual model prose | Failed:120-second provider timeout; `llm_status=unavailable` |

The lifecycle passed, but the overall client intentionally returned failure at
the separate live-prose gate. It did not call the fallback a successful live model
reply. No named outcome part was written, so this synthetic case does not enter
the `has_outcome=true` training-part filter. The full returned evidence and source
narratives remain saved exactly. This is API/report-HTML proof, not yet a real
browser workspace/one-click-print acceptance.

A separate one-call quick-diagnose baseline also failed its live-model gate after
131.05seconds, returning ten ranked checks and explicit fallback. It used the
existing aircraft, no retries and no ingestion; logout was confirmed. Raw response
and request parameters are retained under `quick-baseline/`.

## Prepared operational fix

The old session phrasing request reconstructed from its actual saved response
contained15,259UTF-8bytes and allowed2,400output tokens. The prepared shared prose
builder supplies at most2,048bytes and192output tokens. It prioritizes three
report excerpts for phrasing, preserves complete ranking and all20saved evidence
records, and explicitly records/warns which sources the model received. Source
IDs, aircraft identity, dates and historical flags within that subset are retained.
Citation membership and sentence audits use the actual supplied subset; a fallback
or structured deterministic answer retains its appropriate full saved boundary.
Report-help preserves the requested-record ordering. Structured answers remove
old model-prompt provenance and remain graph/model independent.

The smaller context is an operational change, not a claim that a model inspected
all20full narratives. An unexecuted all20metadata prototype already consumed3,129
bytes before narrative excerpts, so its superseded design metadata is retained
separately. The final prepared-input replay states that no new live output has
yet been measured. Full saved evidence is never discarded to satisfy the budget.

Quick diagnosis retains its bounded source lists and JSON schema, asks for at
most60explanation words and uses512tokens. Malformed structured fragments degrade
instead of appearing as raw JSON; complete legacy plain prose remains compatible.
Provider-marked token-cutoff prose is rejected instead of accepted as complete.
JSON classification behavior is unchanged. Runtime prompt/cache versions change;
frozen comparison prompts/700-token budget and published research results do not.

Five pure-function tests and Node syntax checks passed locally without installs.
API/provider/full-stack hosted checks and actual post-release model outputs remain
required. The browser verifier gains an explicit optional saved-case check for
closed replay and one-click A4 PDF printing, without any new session/model writes.

Ownership follows the recorded accepted vertical handoff
`DEC-20261120-vertical-ownership.md` and CONTRACTS§2: Usman owns the Copilot/diagnose
route, adapter and investigation package. No retrieval weights, maintenance
ingestion, auth or shared app-shell behavior is changed by this fix.

## Runtime release — verified source and merge

PR55 source `b9bad632c25f3d26dac356489904a3b02100432c` passed
CI44992570766: 549 backend tests, zero failures/errors/skips,
5,629/6,815 measured lines (82.60%); frontend/build and disposable real-graph
full-stack/browser checks also passed. The first failed attempt is retained.
Ordinary exact-head merge produced `11beed1f2b050057942ba31321ce7f2e7b0bf80f`
at 2026-11-22T06:15:57Z. Raw receipts and XML are retained under
`evidence/phase28-bounded-runtime-release/`. Main CI44992947098, deployment
and real post-release model/browser results are separate pending gates.

Merged-main CI44992947098 and deployment44993176097 both passed. Public
health independently confirmed exact SHA11beed1f2b050057942ba31321ce7f2e7b0bf80f,
live Neo4j/model mode and2,079records. A fresh labelled lifecycle/model probe
is now being measured separately; source health is not a successful response.

## Actual post-release result

Fresh case74c792ce-510c-4c60-addb-a7f441435246 on11beed1 again
verified lifecycle/replay/closure409/report200, with unchanged corpus and logout.
The192-token/2,042-byte prose request still timed out; total turn154.35seconds.
`live_prose_verified=false`, overall probe failed. This disproves sufficiency
of prompt reduction on the current service. Observer44993459031 found199.87%
CPU of the2CPU cap,3.383GiB/4GiB, no OOM/restart. Its strict parser covers only
/api/chat, so absence of new completions cannot describe /v1/chat/completions.

Hosted browser44993544541 passed with require_saved_case=true: selected this
exact case, exact turn replay after real reload/refresh, closed read-only guard,
one-click authenticated print/PDF,390px layout, chart parity, both themes and
logout. The recorded model status remains unavailable. Seven screenshots and
PDF are retained in phase28/public-browser; visual PDF review is separate.
