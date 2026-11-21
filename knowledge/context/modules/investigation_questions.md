---
id: mod-investigation-questions
title: Report attributes, information gain and original-report simulation
status: active
owners: [Usman]
updated: 2026-11-20
---

# Question engine boundary

The pure engine is implemented. [Managed live session questions](investigation_live_questions.md) are now implemented behind an explicit disabled-by-default flag and policy file.
`attributes.py` freezes thirteen attributes: four raw FAA fields, a 2023-only
part-condition top thirty, explicit hundred-level location zones, and seven
narrative mention patterns. A negated mention is still a mention; absence never
asserts that an aircraft condition was absent. Unknown categories use OTHER.

Official descriptions come from the SHA-pinned FAA SDRS lookup archive, retained
under `docs/work/usman/evidence/phase5-faa-lookup-tables.zip`. The standard-library
importer reproduces the checked-in codebook exactly. No descriptions were guessed.
The fitted schema records 2023 corpus and codebook fingerprints.

`questions.py` validates normalized finite likelihoods, computes entropy including
other, applies Bayesian updates and maximizes expected information gain. Alpha=5
smooths each part distribution toward the visible fleet marginal. At least twenty
same-model/part observations are required for model-specific counts; otherwise
fleet/part counts apply. Other always uses the fleet marginal. Empty counts give
uniform distributions. Questions with only one possible answer are omitted.
Lexical attribute order resolves equal-gain ties. Not-sure preserves belief and
removes that attribute from the remaining simulation pool.

`TemporalQuestionIndex` advances strictly before SubmissionDate, subtracts every
visible member of the query citation chain and restores it after the snapshot.
Unknown aircraft models never qualify as model matches. Future/equal-time records
and later corrections cannot enter likelihood counts. Tests compare the indexed
implementation with naive visible-record counting and mutate future records.

`simulated_technician.py` keeps original-report answers and downstream correction
outcome scoring on separate paths. It compares information gain, seeded random
and no questions at budgets zero through three, on frozen Mid-I candidate lists.
Controls use all thirteen attributes, six structured attributes and four coded
attributes. All-attribute narrative answers can repeat information already in the
initial prompt; these are simulated report-field questions, not fresh observations.

Committed 2024 selection retains 389 pairs / 340 originals. Paired 95% bootstrap
intervals cluster by original. Information gain reduces entropy, but its top-1
and top-3 advantages over random at three questions have intervals containing
zero in every attribute group. No production operating point or causal diagnostic
claim follows. No 2025 data was downloaded or evaluated. Replay script and static
scientific figure are under `docs/work/usman` and `docs/fyp1-final/figures`.

The four-field ingest patch and idempotent backfill are applied/tested on the
separate user-authorized review branch. Shared staging backup/backfill and Shahmeer review remain distinct
acceptance steps. See `CODED_FIELDS_INTEGRATION.md` for exact scope and authorization.

`test_research_artifact_tools.py` reproduces every checked-in official codebook
entry and fingerprint from the retained archive. It also exercises checksum
refusal through the actual command and malformed/missing/duplicate workbook
failures with explicitly synthetic containers. These checks do not introduce
new FAA meanings or download updated tables.
