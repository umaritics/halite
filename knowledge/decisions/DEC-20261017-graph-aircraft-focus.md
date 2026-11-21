---
id: dec-graph-aircraft-focus
title: Knowledge Graph page shows one aircraft's stored subgraph
status: accepted
owners: [Shahmeer]
updated: 2026-10-17
---

# DEC-20261017 — Knowledge Graph page: aircraft focus, truthful counts

## Context

The Graph page asked `/graph/overview` with no limit, so it received the backend
default of 200 nodes: a slice of a graph that holds about 2,200 nodes and 4,075
edges on staging. It still told the reader "Capped at 2000 nodes", labelled
nodes with UUID prefixes, drew every relationship identically, and the side panel
showed none of a record's stored fields. Whole-fleet rendering is unreadable.

## Decision

- The page requests `limit=3000` (enough for the whole staging graph) and says so
  when the cap is reached (`graph may be incomplete`).
- It opens on the aircraft with the most records and shows that aircraft's `Asset`
  node, its `ServiceRecord` nodes, and only the edges the backend already stored
  between them (813SK: 154 nodes, 305 edges). "Whole fleet" stays available with a
  density warning.
- `utils/graphScope.js` only **selects** nodes and edges. It never creates, infers
  or reorders a relationship (Umar's rule: no fabricated graph edges).
- `SUPERSEDES` (computed by the conflict engine) is drawn thicker and amber so
  corrections stand out from the ingest-derived `ABOUT` and `PRECEDED_BY`; a
  legend explains each type and counts the ones in view.
- Nodes are labelled by tail number or record id. The side panel shows the stored
  record or aircraft fields and links to Asset History.
- A browser without WebGL, or a renderer error, shows a message instead of a blank page; the legend, selector and navigation still work.
- Legacy software-domain nodes are filtered out (see
  [DEC-20261016-frontend-maintenance-only](DEC-20261016-frontend-maintenance-only.md)).

## Consequences

Staging holds seven stored `SUPERSEDES` edges, one each on 811NN, 826NN, 300UB,
800NN, 335RT, 981UY and 146AA; the selector marks those aircraft. The busiest
aircraft (813SK) has none. The page does not show the stored `confidence` on a
record, because the graph payload carries the legacy `1.0` placeholder that the
other pages deliberately hide.

No backend change. Counts shown are counts of what is drawn. Unit tests cover the
selection logic and page behaviour; WebGL rendering itself is checked manually
against staging.
