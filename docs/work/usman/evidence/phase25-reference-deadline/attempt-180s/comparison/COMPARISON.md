# Fixed-prompt interactive model comparison

Measurement role: `staging_reference`. No model has been selected.
Runner hardware: `{"machine": "x86_64", "release": "7.0.0-1020-azure", "system": "Linux"}`. Hardware describes the runner; even loopback can be a tunnel. Verify server placement before model selection.
Data year: 2024; twenty primary prompts (ten fact extraction, ten prose) plus ten paired no-evidence prose calls per model.
One warmup per active model/invocation excluded. Serial requests; latency includes provider load and network time.
Raw responses and exact prompts are retained in the response journal and packet. Provider failures count against valid-output share.
Checker status: thresholds pending; semantic support rates unavailable.

| Model | Arm | Task | Attempts | Responses | Valid output share | In-evidence citation share | Unsupported + uncited | Unsupported + uncited rate | Mean seconds / attempt | Median seconds / response |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phi4-mini:latest | evidence | facts | 10 | 10 | 1.0000 | unavailable | not applicable | unavailable | 40.2794 | 36.4330 |
| phi4-mini:latest | evidence | prose | 10 | 4 | 0.4000 | 0.9600 | 20 | unavailable | 164.5579 | 148.2357 |
| phi4-mini:latest | no_evidence | prose | 10 | 10 | 1.0000 | unavailable | 47 | unavailable | 52.9891 | 46.2940 |

Unsupported rate includes uncited non-whitelisted sentences; null if any cited sentence is unrated or a provider attempt failed. This is checker output, not human ground truth.

The no-evidence arm has an empty evidence list at generation and L2 assessment. Missing citations are observable citation failures; they are not proof of false aircraft facts. No human-ground-truth accuracy is claimed.
Exact output-schema validity is not extraction accuracy. Report task-specific denominators and raw outputs when choosing the interactive model.
No held-out 2025 data was used. No model winner or probability wording is inferred.
