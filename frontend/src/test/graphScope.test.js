import { describe, expect, it } from 'vitest';
import { aircraftOptions, countBy, focusAircraft, maintenanceGraph } from '../utils/graphScope';

const nodes = [
  { id: 'a1', label: 'Asset', tail_number: '813SK' },
  { id: 'a2', label: 'Asset', tail_number: '105NN' },
  { id: 'a3', label: 'Asset', tail_number: 'N0REC' },
  { id: 'r1', label: 'ServiceRecord', record_id: 'R1', asset_key: '813SK' },
  { id: 'r2', label: 'ServiceRecord', record_id: 'R2', asset_key: '813SK' },
  { id: 'r3', label: 'ServiceRecord', record_id: 'R3', asset_key: '105NN' },
  { id: 'd1', label: 'Decision', title: 'old software node' },
];
const edges = [
  { source: 'r1', target: 'a1', type: 'ABOUT' },
  { source: 'r2', target: 'a1', type: 'ABOUT' },
  { source: 'r2', target: 'r1', type: 'PRECEDED_BY' },
  { source: 'r2', target: 'r1', type: 'SUPERSEDES' },
  { source: 'r3', target: 'a2', type: 'ABOUT' },
  { source: 'd1', target: 'r1', type: 'RELATES_TO' },
];

describe('maintenanceGraph', () => {
  it('drops non-maintenance nodes and the edges that touched them', () => {
    const g = maintenanceGraph({ nodes, edges });
    expect(g.nodes.map((n) => n.id)).not.toContain('d1');
    expect(g.edges.some((e) => e.type === 'RELATES_TO')).toBe(false);
    expect(g.edges).toHaveLength(5);
  });

  it('tolerates empty or missing data', () => {
    expect(maintenanceGraph(undefined)).toEqual({ nodes: [], edges: [] });
    expect(maintenanceGraph({})).toEqual({ nodes: [], edges: [] });
  });

  it('understands edges whose ends were already resolved to objects by the force graph', () => {
    const g = maintenanceGraph({
      nodes,
      edges: [{ source: { id: 'r1' }, target: { id: 'a1' }, type: 'ABOUT' }],
    });
    expect(g.edges).toHaveLength(1);
  });
});

describe('aircraftOptions', () => {
  it('counts the stored corrections per aircraft', () => {
    const opts = aircraftOptions(maintenanceGraph({ nodes, edges }));
    expect(Object.fromEntries(opts.map((o) => [o.tail, o.corrections]))).toEqual({ '813SK': 1, '105NN': 0, N0REC: 0 });
  });

  it('lists aircraft by record count, then tail number', () => {
    const opts = aircraftOptions(maintenanceGraph({ nodes, edges }));
    expect(opts.map((o) => [o.tail, o.records])).toEqual([
      ['813SK', 2],
      ['105NN', 1],
      ['N0REC', 0],
    ]);
    expect(opts[0].id).toBe('a1');
  });
});

describe('focusAircraft', () => {
  const graph = maintenanceGraph({ nodes, edges });

  it('keeps one aircraft, its records and only the stored edges between them', () => {
    const g = focusAircraft(graph, '813SK');
    expect(g.nodes.map((n) => n.id).sort()).toEqual(['a1', 'r1', 'r2']);
    expect(g.edges.map((e) => e.type).sort()).toEqual(['ABOUT', 'ABOUT', 'PRECEDED_BY', 'SUPERSEDES']);
  });

  it('never invents an edge', () => {
    const g = focusAircraft(graph, '813SK');
    for (const e of g.edges) expect(graph.edges).toContain(e);
  });

  it('returns the whole graph when no aircraft is chosen', () => {
    expect(focusAircraft(graph, '')).toBe(graph);
  });

  it('returns an empty graph for an unknown aircraft', () => {
    expect(focusAircraft(graph, 'NOPE')).toEqual({ nodes: [], edges: [] });
  });
});

describe('countBy', () => {
  it('counts, bucketing missing keys as Other', () => {
    expect(countBy([{ k: 'a' }, { k: 'a' }, {}], (x) => x.k)).toEqual({ a: 2, Other: 1 });
  });
});
