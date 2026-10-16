# Halite — Research-Backed Problem Reformulation (Jam Session)

Working document. We go part by part. A part is not "locked" until we've
discussed it and you confirm it's solid. Do not skip ahead.

## Ground rule for every part

A claim is **rejected** if it can be fully solved by:
- writing better docs / ADRs by hand
- better prompt engineering / agent rules (`.claude/rules`, `CLAUDE.md`)
- putting context files under git and syncing/PR-reviewing them

A claim **survives** only if we can cite evidence that the failure is
**structural** — i.e., disciplined humans following best practice still hit
it — not a discipline or tooling gap.

---

## Part 0 — Problem statement (categorical, not anecdotal)

Status: **drafted below, pending your confirmation**

## Part 1 — Why tacit decisions don't get captured at all
(externalization gap — knowledge management research, Nonaka SECI, NDM/RPD)

Status: not started

## Part 2 — Why the decisions that DO get written down still decay
(ADR structural-failure research, documentation staleness empirical studies)

Status: not started

## Part 3 — Why the fix requires structure (a typed graph), not a better file format
(flat file vs relationship queries; what a version-controlled markdown file
structurally cannot represent)

Status: not started

## Part 4 — Why multi-person / multi-agent concurrent updates need real conflict
resolution, not git merge
(CRDT / semantic conflict resolution research — this is your teammate's slice)

Status: not started

## Part 5 — Why agent context injection needs bounded, ranked retrieval
(context engineering / GraphRAG / lost-in-the-middle — the token-efficiency
evidence we already measured)

Status: not started

## Part 6 — Delivery mechanism: export today, MCP later
This part is engineering scope, not a research claim. Discussed last.

Status: not started

---

## Decision log (fill in as we lock each part)

| Part | Locked claim | Key citation(s) |
|---|---|---|
| 0 | — | — |
