// Scoping helpers for the Knowledge Graph page.
//
// The backend returns the stored graph. Nothing here creates, infers or reorders a
// relationship: every function only SELECTS nodes and edges that the backend sent
// (AGENTS.md / Umar's rules: no fabricated graph edges).

export const MAINT_LABELS = ['Asset', 'ServiceRecord'];

// What each stored relationship means (knowledge/context/04_data_and_graph.md).
export const EDGE_MEANING = {
  ABOUT: 'A record is about this aircraft (from ingest).',
  PRECEDED_BY: 'The chronological prior record on the same aircraft (from ingest ordering).',
  SUPERSEDES: 'A newer record supersedes an older one (computed by the conflict engine).',
};

const endId = (v) => (typeof v === 'object' && v !== null ? v.id : v);

// Keep only maintenance nodes (the old software-domain nodes are not part of the product)
// and the edges whose two ends both survive.
export function maintenanceGraph(data) {
  const nodes = (data?.nodes ?? []).filter((n) => MAINT_LABELS.includes(n.label));
  const ids = new Set(nodes.map((n) => n.id));
  const edges = (data?.edges ?? []).filter((e) => ids.has(endId(e.source)) && ids.has(endId(e.target)));
  return { nodes, edges };
}

// Aircraft in the graph, most records first (ties by tail number). `corrections` counts the
// stored SUPERSEDES edges whose newer record belongs to the aircraft.
export function aircraftOptions(graph) {
  const counts = new Map();
  const keyById = new Map();
  for (const n of graph.nodes) {
    if (n.label === 'ServiceRecord' && n.asset_key) {
      counts.set(n.asset_key, (counts.get(n.asset_key) || 0) + 1);
      keyById.set(n.id, n.asset_key);
    }
  }
  const corrections = new Map();
  for (const e of graph.edges) {
    if (e.type !== 'SUPERSEDES') continue;
    const k = keyById.get(endId(e.source));
    if (k) corrections.set(k, (corrections.get(k) || 0) + 1);
  }
  return graph.nodes
    .filter((n) => n.label === 'Asset' && n.tail_number)
    .map((a) => ({
      tail: a.tail_number,
      id: a.id,
      records: counts.get(a.tail_number) || 0,
      corrections: corrections.get(a.tail_number) || 0,
    }))
    .sort((x, y) => y.records - x.records || x.tail.localeCompare(y.tail));
}

// One aircraft: its Asset node, its records, and the edges that already exist between them.
export function focusAircraft(graph, tail) {
  if (!tail) return graph;
  const keep = new Set(
    graph.nodes
      .filter(
        (n) =>
          (n.label === 'Asset' && n.tail_number === tail) ||
          (n.label === 'ServiceRecord' && n.asset_key === tail)
      )
      .map((n) => n.id)
  );
  return {
    nodes: graph.nodes.filter((n) => keep.has(n.id)),
    edges: graph.edges.filter((e) => keep.has(endId(e.source)) && keep.has(endId(e.target))),
  };
}

export function countBy(items, keyFn) {
  const out = {};
  for (const item of items) {
    const k = keyFn(item) || 'Other';
    out[k] = (out[k] || 0) + 1;
  }
  return out;
}
