# Private hosted reference-model measurement

Status: hosted instrument verified on eeb2b77 / CI 44984026697; actual measurement 44984568357 dispatched, outcome pending.
Owners: Muhammad Usman Al Haq. Date: 2026-11-22.

## Context

The user requested complete verified work and the portable M4 runner when no M4
endpoint was available. Staging already has phi4-mini in a private resource-limited
container. Real reference outputs and paired no-evidence generation are still
unmeasured. They can progress without installing a model on the frozen laptop,
changing shared data or claiming staging timings are M4 measurements.

## Decision

Provide a manual MEASURE workflow on exact-CI-green main using the existing staging
environment. Verify exact deployed health and private pinned model/resource state.
Use a temporary hosted loopback SSH tunnel to the existing Docker address and
in-memory token. Run the unchanged frozen comparison tool against the configured
installed phi4-mini only. Retain raw outputs/errors and provenance; require stable
revision/corpus/container/restart state afterwards. Always close the tunnel and
restore token environment. Keep model ports private and preserve all parameters,
settings, deployed code and databases.

## Consequences

Produces actual staging-reference and paired baseline outputs once executed and
verified. It does not complete human support calibration, M4 candidate comparison,
interactive-model choice or L4 live integration. Shared-server/network timings are
explicit and cannot support hardware-matched comparisons. Failure evidence is
retained instead of silently retrying model calls or discarding errors.
