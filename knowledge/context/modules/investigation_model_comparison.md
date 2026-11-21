---
id: mod-investigation-model-comparison
title: Fixed-prompt portable model comparison
status: active
owners: [Usman]
updated: 2026-11-20
---

# Interactive-model comparison boundary

The user chose a finished self-contained runner for Shahmeer's M4; no endpoint or
M4 measurements were supplied. `experiments/model_prompts.py` freezes 20 unique
real 2024 original observations from the existing selection corpus. Ten extract
facts, ten write prose; each prose prompt also gets a paired no-evidence arm.
The instruction/observation stay identical across prose arms; only evidence is
emptied. Evidence comes from the unchanged frozen ranker's top three hypotheses,
up to three reports each, verified strictly before submission and outside the
query's full correction chain. No downstream answer ID/key/narrative is exported.
This is a declared comparison prompt version, not a claim of exact live-prompt
replay or held-out test performance. No 2025 source is loaded.

`model_compare.py` speaks native Ollama HTTP with redirects disabled, bounded
responses, explicit timeouts and no fallback or automatic model download/retry.
Exact installed model names, digests/details and server version are required.
Generation is serial with fixed temperature, seed and token limit. A warmup is
excluded for each active model/invocation, including resumed runs. Arm/model order
is seeded. Wall timing includes network/loading; raw provider timings remain.

Each response or provider failure is fsynced to an append-only JSONL journal.
Resume validates source/packet/settings/model/machine identity and prior
assessments against raw responses, refuses foreign/duplicate/partial rows and
never replaces a failed attempt. Completed runs make no extra chat calls.
Raw outputs, exact prompt fingerprints, copied packet and a machine-readable
manifest accompany `results.json` and the generated `COMPARISON.md` table.

Output validity is strict fact-JSON shape or nonempty complete prose without a
model-written question. It does not prove extraction accuracy, textual support
or absence of every unsafe phrase. Citation membership uses the actual supplied
sources; a guessed ID in the no-evidence arm gets no evidence credit. Missing
citations are observed citation failures, not proof that an aircraft fact is
false. Grounding uses the existing pure checker. Without explicit accepted or
labelled experimental lexical thresholds, semantic unsupported rates remain
unavailable. Provider failures stay in valid-output denominators. Raw checks,
unrated/uncited/unsupported counts and exact denominators are retained.

Measurement roles distinguish development, M4 comparison and staging reference.
The M4 role requires a Darwin/arm64 M4 runner with local endpoint and two/three
models; chip/memory are read without serial numbers. A loopback tunnel is not
proof of server placement, so server hardware is explicitly unverified and must
be checked in the human handoff. Reference timings remain separate from M4
measurements. The tool never chooses a model or changes runtime settings.

`model_bundle.py` produces a reproducible ZIP containing only Python standard-
library code, the pure lexical checker, fitted guard vocabulary, frozen prompt
packet and instructions. The extracted entrypoint verifies bundle file hashes
and uses its fixed packet; no app/database/dependency installation is needed.
The user's selected delivery is this verified runner. Actual M4 execution and
Usman's interactive-model decision remain project gates; synthetic tests are
explicitly identified and cannot stand in for real measurements.
