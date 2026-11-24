---
id: DEC-20261124-integrity-foundation
title: Record Integrity foundation: rule-linked citations, link-based validity, one writer
status: accepted
owners: [Shahmeer]
updated: 2026-11-24
---

# DEC-20261124 — Record Integrity foundation

## Context

The engine only tested whether a report contained "SUPPLEMENTAL REPORT FOR" and then linked to its top-ranked
candidate. Accept and reject changed a status string and nothing in the graph. Re-processing rewrote the status of
reviewed records. The review screen re-ran the engine, with model calls, on every view.

## Decision

1. **Announced corrections are linked by rule R1, not by the model.** `integrity/citations.py` parses the cited ID.
   If the cited report exists, is on the same aircraft and is not known to be later, `process_record` links to it with
   method `explicit_citation` and confidence 1.0 and makes no model call. "Not known to be later" means submitted at
   the same time or earlier; without submission times, the same occurrence date or earlier
   (`timeutil.is_known_not_later`). Candidate search keeps the stricter rule, submitted strictly earlier
   (`timeutil.is_eligible_prior`), because there nothing else orders the pair.
   - Not taken: keep classifying the top candidate and use the citation as a score signal. The top candidate is not
     always the cited report (guide D1), and a stated ID needs no guess.
2. **Validity is read from links.** `integrity/validity.py` (`superseded_by`, `is_current`) reads `SUPERSEDES` links.
   The `status` string `superseded` is still written for compatibility with existing readers.
   - Not taken: keep reading the status string. It is overwritten on re-processing, so it can lose the decision.
3. **Every integrity write goes through `backend/integrity/apply.py`.** Links, `NOT_SUPERSEDES` edges, status changes
   and review fields are written there, and it emits the audit events through a callable the route supplies.
   - Not taken: let the engine and routes write to the graph directly, as before. Then each caller must repeat
     the human-decision check and the audit call.
4. **A human decision is never overwritten.** A record with `analysis_state=reviewed` or status `accepted` or
   `rejected` is skipped by `process_record` (`skipped="reviewed"`), refused by `record_analysis`, and its status is not
   changed when a link to it is written. Only an explicit `force` writes it again.
   - Not taken: let the next analysis run replace it with the newer model result. A reviewer's work would be lost
     silently.
5. **Accept creates and reject removes the link, and reject blocks re-proposal.** Accept confirms existing links in
   place (keeping method and model version, adding `decided_by` and `decided_at`) and creates a `human` link to the
   proposed prior when the label is `supersedes` or `partial_supersedes`. Reject removes the record's links and writes a
   `NOT_SUPERSEDES` edge per pair; candidate search and R1 skip such pairs.
   - Not taken: store only a status on reject. The pair would come back at the next analysis run.
6. **The review screen reads a stored proposal.** `GET /maintenance/review-queue/{id}/proposal` returns what analysis
   stored (`proposed_prior_id`, label, rationale, confidence) and makes no model call. A record analysed before the field
   existed (field absent) gets its prior recomputed deterministically; `python -m integrity.backfill` stores it.
   - Not taken: keep calling `GET /maintenance/records/{id}`, which re-runs the engine in dry-run mode. It can show a
     different pair from the one scored, and each view costs model time.
7. **The hand-weighted confidence is unchanged for now.** Model-path records store `integrity_p` equal to the existing
   confidence and `integrity_model_version="handweighted-v0"`. WP-A3 replaces it with a calibrated model.
   - Not taken: change the weights in this work. It would mix a behaviour change into a refactor and has no
     evaluation behind it yet.

## Consequences

- Guide defects D1, D5, D6 and D7 are fixed. D2, D3, D4 and D8 are not touched.
- `SUPERSEDES` links carry `method`, `model_version`, `decided_by`, `decided_at`. A pair has one link; a repeat write
  updates it. The new `NOT_SUPERSEDES` edge carries `decided_by` and `decided_at`.
- The `review_decisions` table (PostgreSQL) keeps each accept or reject with the model's probability and version.
- Audit: the reviewed record gets one `maintenance.review.accepted` or `.rejected` event, as before. The link a
  decision creates or removes, and the earlier report's status change, get `integrity.link.*` and
  `integrity.status.changed` events with the reviewer as actor.
- A link's `model_version` names what decided it: `rule-R1` for a citation link, `handweighted-v0` for a model link.
- Known limits: the analysis mode of a stored record is inferred, not stored (`proposal._stored_mode`), so a
  cascade record with two agreeing votes and a non-default pass count could be read as legacy when its prior is
  recomputed. Records with `proposed_prior_id` absent are recomputed; an empty string means no prior was found.
- The `status` string of a superseded report is still overwritten if that report itself is re-processed. Its link
  stays, so `validity.superseded_by` is still right; anything that reads the string is not. Readers must move to
  `validity.py`.
- The Cypher for the new link methods is tested with a fake store that checks the query and its parameters. It has
  not been run against a live Neo4j outside the CI smoke test.
- A citation token must contain a digit, so a word after "SUPPLEMENTAL REPORT FOR" is not read as an ID. The regex
  itself is the one the other verticals use.
- `GET /maintenance/records/{id}` still re-runs the engine in dry-run mode. The review screen no longer calls it.
- The proposal route needs a signed-in user only, so a technician can read it.

## Owners

Shahmeer (Record Integrity). Built by an orchestrated run of coding agents and reviewed before merge.

## Date

2026-11-24
