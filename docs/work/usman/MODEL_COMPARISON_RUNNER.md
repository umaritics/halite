# Portable interactive-model comparison

The user requested a finished, verified self-contained runner for Shahmeer's M4.
This package does not claim the M4 measurement has already happened or choose the
interactive model on Usman's behalf. Staging's model configuration is untouched.

## Run on the M4

Extract `halite-model-comparison-v1.zip` into a new folder. Python 3.10 or newer
and an already running Ollama service are required. There is no package install,
model download, database, frontend or application server dependency in the runner.
Use the exact names of two or three **already installed** candidate models.
For example, if these exact names appear in `ollama list`:

```sh
python3 run_compare.py --role m4_comparison \
  --models mistral:7b-instruct qwen2.5:7b-instruct llama3.1:8b \
  --output ./m4-comparison-01
```

Run it on the actual M4 host, against its local Ollama service, while other model
work is stopped. A loopback tunnel by itself does not prove the inference server
runs on that machine: the manifest deliberately distinguishes runner hardware from
server placement. Record the actual server placement in the handoff. Do not label
remote/staging or synthetic-server timings as M4 timings. The runner records
Apple chip, OS, architecture and memory without serial numbers or user identity.
It records exact installed model digests/details and Ollama server version. M4 candidate runs require installed-model metadata confirming the declared 7–8B size class; phi4-mini remains a separate reference run.

If interrupted, repeat the same command with `--resume` and the same output path.
The runner verifies packet, source, model, configuration and machine identities,
checks saved assessments against raw responses, preserves completed attempts and
rewarms each model with unfinished work. A partially written journal tail fails
explicitly rather than discarding a potentially completed response. Preserve it
for inspection before any manual repair. Failed provider attempts stay in the
original denominator; resume never silently retries or replaces them. Use a fresh
output directory for a deliberately repeated measurement.

Read `COMPARISON.md` in the output folder. Return the **entire output folder**,
including manifest, copied packet, raw response journal, warmups and JSON results.
The table shows attempted/responded counts, strict output-validity share, cited-ID
membership, sentence diagnostics and seconds per reply. No model winner is chosen
automatically. Usman reviews the raw outputs and records the interactive-model
decision; staging keeps its reference model.

An optional accepted lexical checker configuration can be supplied with
`--grounding /path/to/checker.json`. Without it, valid cited sentences are unrated
and semantic-support rates are unavailable. Do not invent thresholds to fill in
the table. Experimental configurations are explicitly labelled. Blended dense
configurations are refused in this portable lexical runner.

For the reference model, run on its actual host using the same bundle:

```sh
python3 run_compare.py --role staging_reference \
  --models phi4-mini:latest --output ./phi4-reference-01
```

Replace the name only with the exact installed `phi4-mini` tag. Reference host
measurements are reported separately; they are not hardware-matched M4 latency
comparisons. The runner does not modify the deployed Halite application.

## Frozen comparison protocol

The packet contains 20 unique real 2024 FAA original observations, deterministically
sampled from the committed selection cases. Ten prompts extract explicit facts
into the five existing string-array fields. Ten write historical-evidence prose.
Each prose case also has a paired **no-evidence** arm: the instruction and
observation are identical, and only the supplied evidence list becomes empty.
Thus each model has 20 primary prompts and 10 paired baseline calls, plus excluded
warmups. This two-task benchmark is a declared comparison prompt version; it is
not a replay claim about the live product prompt.

Evidence is the frozen ranker's first three hypotheses, up to three cited reports
each. Every reference is validated strictly before the original submission and
outside its complete correction chain. The downstream correcting narrative, ID
and part key never enter the packet. No 2025 source is used, and no output from
these cases may be called held-out test performance.

Requests are serial. Model order and evidence/baseline order are seeded. Generation
uses temperature zero, seed 1729, a 4,096-token context and a 700-token output limit, with JSON mode for facts
and ordinary prose mode for explanations. Prompt content is capped at 3,200 UTF-8 bytes before sending; the frozen real packet fits this conservative budget without report truncation. Every model/invocation with pending
work gets one warmup excluded from the results. Timings are wall-clock durations
including network/model loading; provider token/load/evaluation timings remain in
the raw response. Warmup exclusion is not a claim that all subsequent calls were
fully warm. Do not compare machines by ignoring these distinctions.

Strict fact-schema validity is not factual extraction accuracy. Nonempty complete
prose without a model-written question is counted as output-valid; this does not
certify factual support or absence of every unsafe instruction. Citation share is
counted by sentence citation occurrence. Zero citations yields **unavailable**,
not 100%. Evidence-arm L2 uses supplied sources; a guessed ID in the no-evidence
arm is not credited as supplied evidence. Sentence counts include invalid cited
sentences and unapproved uncited sentences, with the categories preserved in raw
audits. Such citation failures are not proof that an uncited aircraft statement
is false. Human-ground-truth agreement/accuracy remains a separate evaluation.

Provider errors remain visible, count against valid-output share and cause a
nonzero CLI exit after results are saved. There is no automatic retry, fallback,
model pull, winner selection or application-setting change. Raw response bodies
are preserved; credentials are read only from `HALITE_MODEL_API_KEY` if needed and
are never written into results. Remote endpoints require HTTPS or a loopback SSH
tunnel; redirects and credential-bearing/query URLs are refused.

## Reproduce the bundle

From the repository's `backend` directory:

```sh
python -m investigation.experiments.model_bundle \
  --packet investigation/experiments/data/model_prompts_2024_v1.json \
  --readme ../docs/work/usman/MODEL_COMPARISON_RUNNER.md \
  --output /path/to/new/halite-model-comparison-v1.zip
```

ZIP member timestamps/order/permissions are fixed. `BUNDLE_MANIFEST.json` hashes
every included source/data/instruction file; the sidecar hashes the ZIP. Rebuilding
from the same sources yields the same bytes. The committed source packet records
its corpus fingerprint, seed and generator hash. Tests use explicit synthetic
providers, never fake real-model or human-labelled results.


## Protocol references

The transport follows Ollama's official [chat API](https://docs.ollama.com/api/chat)
(`stream: false`, optional JSON format, runtime options and provider duration fields)
and [installed-model listing API](https://docs.ollama.com/api/tags) (exact names,
digests and model details). The explicit context setting follows the official
[context-length guide](https://docs.ollama.com/context-length). These references
specify the wire protocol; they do not supply any experimental result in this project.
