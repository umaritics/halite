# Actual phi4-mini reference at a 180-second deadline

Source/deployed revision `326cd885bb21e53019f25a6cfae82164bfba0a6a`.
Real hosted run [44984568357](https://github.com/umaritics/halite/actions/runs/44984568357)
finished with failure on 2026-11-22 at 05:03 UTC after all 30 attempts. One excluded
warmup is retained. These are staging CPU results, not M4 measurements.

| Task and arm | Attempts | Responses | Valid output share | Mean seconds per attempt | Median seconds per response |
| --- | --- | --- | --- | --- | --- |
| Facts with evidence | 10 | 10 | 100% | 40.28 | 36.43 |
| Prose with evidence | 10 | 4 | 40% | 164.56 | 148.24 |
| Prose without evidence | 10 | 10 | 100% | 52.99 | 46.29 |

Six evidence-prose requests recorded `TimeoutError` at approximately 180 seconds.
Their times remain in the attempt mean and their failures count against output
validity; they are not dropped or replaced. A complete journal is not an accepted
error-free measurement: the outer operation correctly failed. Its original
postflight was skipped because the quality gate raised before that step.

Facts validity means schema correctness, not extraction accuracy. Four returned
evidence-prose responses contained 25 citation occurrences, of which 24 were in
the supplied evidence. This selected subset cannot establish the full arm's
support accuracy. The baseline contained 47 unapproved uncited sentences; that
is not proof of 47 false statements. No accepted checker thresholds or human
ground truth were used, so semantic unsupported rates remain unavailable.

Independent scalar arithmetic, prompt hashes, exact frozen packet, method hashes,
raw assessments, task/arm coverage, warmup and journal checksum were replayed by:

```sh
python3 -S docs/work/usman/verify_reference_measurement.py --failed-attempt \
  docs/work/usman/evidence/phase25-reference-deadline/attempt-180s
```

This mode verifies failure evidence and explicitly returns
`measurement_accepted: false`; normal verifier mode still requires full success.
Raw artifacts and verification are retained in the phase25 evidence directory.

## State and remedy

The read-only observer run
[44987794344](https://github.com/umaritics/halite/actions/runs/44987794344)
found the same model container, running with zero restarts and no OOM event,
under the existing 4 GiB and two-CPU limits. Its after-job snapshot showed idle
CPU and 3.279 GiB memory use. Bounded server logs included six roughly-three-minute
HTTP 500 completions; journal errors are the authoritative client observations.
A separate public-health check confirmed unchanged revision and 2,079 records.
These are explicitly independent after-job checks, not retroactively inserted
original postflight output. The laptop ran no inference.

Prepare a separately labelled 600-second-deadline run using the same prompts,
order, model digest, context, prediction cap and seed. The workflow bound becomes
330 minutes to accommodate all 31 serial requests at that ceiling. Only the
client deadline changes; retain this original 180-second result. Longer completion
does not establish acceptable interactive latency or improve this deadline result.
Move the postflight ahead of the provider-error rejection so failed collected
attempts also retain after-health and safe model-state evidence.

Merge/release the verified instrumentation and run the public website check
before starting the next source-pinned measurement. Do not silently retry only
the six failed cases or pool the two deadlines into a single comparison.
