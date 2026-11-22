# Dedicated public-site acceptance

Status: actual public read browser verified; separate dedicated-account lifecycle probe running

Owners: Usman

Date: 2026-11-22

## Context

Usman explicitly supplied a dedicated agent account for real website acceptance.
The working credential was verified by API, while signed-in browser behavior is
still unproven. The laptop previously froze; hosted Chromium avoids that load.
The separate live model measurement pins deployed source and must not be disturbed.

## Decision

Use a manual main-only staging-environment workflow with typed `VERIFY` and
encrypted repository account secrets. Validate the exact deployed source before
and after browsing fixed canonical origins. Inspect real public login, refresh,
research artifact/render parity, home/history, responsive layouts and logout.
Permit only authentication POSTs; abort other API mutations. This browser check
does not generate model output, change the corpus or activate a policy. Retain
screenshots only after login and sanitized status/path/hash proof; exclude request
bodies, headers, storage state, traces, token values and raw exception messages.
Merge/dispatch only after the source-pinned model measurement terminates and the
new revision's ordinary CI/deployment succeeds.

## Consequences

Production read acceptance complements the disposable write-capable session,
grounding and question tests. It cannot prove production turn creation or model
quality. Secret names may be documented; their values never belong in the repo.
The user intends to rotate the dedicated credential after verification.

## Separate actual lifecycle probe

Actual public read run44988921561 passed, but the account's empty history cannot
prove persistence or a model-backed turn. Under the user's full-project testing
authorization and explicitly dedicated agent account, a separate typed
VERIFY_SESSION client creates one clearly labelled own test session using existing
aircraft only. It checks exact replay, closure and printing, and records lifecycle
and live-prose gates separately. No outcome part is set, so the synthetic case
cannot enter the named-outcome training filter. The closing note denies an actual
maintenance finding/repair. No corpus, user-administration or foreign-session
writes occur. Secrets remain in memory; uncertain mutations are not retried.
The read-only browser instrument and its mutation guard remain unchanged.
