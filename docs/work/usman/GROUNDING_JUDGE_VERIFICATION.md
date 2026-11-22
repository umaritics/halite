# L4 evaluation instrument — hosted verification

Source: `8d3abab957a489094578220b35f64b43beb6c00e`.
[Full CI 44982604273](https://github.com/umaritics/halite/actions/runs/44982604273)
passed all three jobs. [PR #51](https://github.com/umaritics/halite/pull/51)
was merged under the user's instruction to merge completed work. This is not
evidence of independent teammate review or actual model-judge accuracy.

## Verified scope

- **515 backend tests, zero failures/errors/skips** in retained JUnit; **283
  frontend tests** in the hosted log. Fifteen additional backend cases exercise
  the actual new instrument and its failure/provenance boundaries.
- **5,407/6,587 = 82.09%** line coverage over the unchanged six core scopes,
  exceeding the exact 80% gate. Raw XML is retained.
- Ruff, both frontend builds, fresh Neo4j/PostgreSQL, maintenance/session API
  checks, production Chromium research/source-span flows, immutable policy
  preflight and independent saved-result replay all passed.
- The actual frozen 150-pair packet passes the instrument's full-source preflight.
  The longest prompt is 4,577 bytes, within the separately declared 6,000-byte cap
  and 8192-token context. No report or sentence is truncated to make it fit.
- Tests verify actual file/CLI import, distinct human-reference identities,
  separate fit/validation metrics, exact source quotes, strict verdict schema,
  wrong model and failed-call retention, no overwrite, complete denominators,
  source-method drift and prompt/raw/verdict tampering rejection.

The instrument does not modify live sessions, saved audits, selected-policy
parameters, labels, the frozen 2025 result or the portable M4 comparison bundle.
No model was installed or launched on the laptop. Real model calls were not
represented by the synthetic test client.

## Retained proof and remaining empirical work

`evidence/phase21-grounding-judge/` contains exact-source job metadata, raw
JUnit/coverage/preflight, test-log summary and PR #50/51 merge records. It also
retains PR #50's successful mainCI 44982470167 and CD 44982694707; those are report-
integration evidence, not the still-separate PR #51 main release.

Execution and human scoring commands are in
[GROUNDING_JUDGE_PROTOCOL.md](GROUNDING_JUDGE_PROTOCOL.md). Actual model judgments,
the independent Usman/Umar label exports, adjudication and measured human-reference
precision/recall remain required. Generated-prose/no-evidence comparison and any
live borderline-judge integration are distinct acceptance items. The full goal
remains active in [ACCEPTANCE_MATRIX.md](ACCEPTANCE_MATRIX.md).
