import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Graph, { MAINT_GRAPH_LIMIT } from '../pages/Graph';
import { GraphSidePanel } from '../components/GraphViewer';
import { ThemeProvider } from '../context/ThemeContext';
import * as client from '../api/client';

// WebGL is unavailable in jsdom: record the props the page hands to the renderer instead.
const fg = vi.hoisted(() => ({ last: null }));
vi.mock('react-force-graph-3d', async () => {
  const React = await import('react');
  return {
    default: React.forwardRef((props, ref) => {
      fg.last = props;
      React.useImperativeHandle(ref, () => ({ zoomToFit: () => {} }));
      return <div data-testid="force-graph" />;
    }),
  };
});
vi.mock('../api/client', () => ({ graphAPI: { overview: vi.fn() } }));

globalThis.ResizeObserver = globalThis.ResizeObserver || class { observe() {} unobserve() {} disconnect() {} };

const overview = client.graphAPI.overview;
const nodes = [
  { id: 'a1', label: 'Asset', tail_number: '813SK' },
  { id: 'a2', label: 'Asset', tail_number: '105NN' },
  { id: 'r1', label: 'ServiceRecord', record_id: 'R1', asset_key: '813SK', occurred_at: '2025-01-01', part_name: 'PUMP' },
  { id: 'r2', label: 'ServiceRecord', record_id: 'R2', asset_key: '813SK', occurred_at: '2025-02-01', part_name: 'SWITCH' },
  { id: 'r3', label: 'ServiceRecord', record_id: 'R3', asset_key: '105NN', occurred_at: '2025-03-01' },
  { id: 'd1', label: 'Decision', title: 'legacy software node' },
];
const edges = [
  { source: 'r1', target: 'a1', type: 'ABOUT' },
  { source: 'r2', target: 'a1', type: 'ABOUT' },
  { source: 'r2', target: 'r1', type: 'PRECEDED_BY' },
  { source: 'r2', target: 'r1', type: 'SUPERSEDES' },
  { source: 'r3', target: 'a2', type: 'ABOUT' },
];
const renderPage = () => render(<ThemeProvider><MemoryRouter><Graph /></MemoryRouter></ThemeProvider>);

describe('Graph page', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    fg.last = null;
    overview.mockResolvedValue({ data: { nodes, edges } });
  });

  it('asks the backend for enough nodes rather than its 200-node default', async () => {
    renderPage();
    await screen.findByTestId('force-graph');
    expect(overview).toHaveBeenCalledWith(MAINT_GRAPH_LIMIT);
    expect(MAINT_GRAPH_LIMIT).toBeGreaterThan(2227);
  });

  it('opens on the aircraft with the most records and shows only its real subgraph', async () => {
    renderPage();
    await screen.findByTestId('force-graph');
    expect(screen.getByLabelText('Aircraft')).toHaveValue('813SK');
    expect(fg.last.graphData.nodes.map((n) => n.id).sort()).toEqual(['a1', 'r1', 'r2']);
    expect(fg.last.graphData.links).toHaveLength(4);
  });

  it('states the true node and edge counts and no longer claims a 2000-node cap', async () => {
    renderPage();
    expect(await screen.findByText(/Aircraft 813SK: 3 nodes · 4 edges/)).toBeInTheDocument();
    expect(screen.queryByText(/Capped at 2000/)).toBeNull();
  });

  it('warns when the loaded cap is reached because the graph may be incomplete', async () => {
    overview.mockResolvedValue({
      data: {
        nodes: Array.from({ length: MAINT_GRAPH_LIMIT }, (_, i) => ({ id: `n${i}`, label: 'Asset', tail_number: `T${i}` })),
        edges: [],
      },
    });
    renderPage();
    expect(await screen.findByText(/cap reached — graph may be incomplete/)).toBeInTheDocument();
  });

  it('never shows legacy software nodes', async () => {
    renderPage();
    await screen.findByTestId('force-graph');
    fireEvent.change(screen.getByLabelText('Aircraft'), { target: { value: '' } });
    await waitFor(() => expect(fg.last.graphData.nodes).toHaveLength(5));
    expect(fg.last.graphData.nodes.map((n) => n.id)).not.toContain('d1');
  });

  it('marks aircraft that have a stored correction in the selector', async () => {
    renderPage();
    expect(await screen.findByRole('option', { name: '813SK · 2 rec · 1 corr.' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: '105NN · 1 rec' })).toBeInTheDocument();
  });

  it('switches aircraft and shows that aircraft only', async () => {
    renderPage();
    await screen.findByTestId('force-graph');
    fireEvent.change(screen.getByLabelText('Aircraft'), { target: { value: '105NN' } });
    await waitFor(() => expect(fg.last.graphData.nodes.map((n) => n.id).sort()).toEqual(['a2', 'r3']));
  });

  it('explains each stored relationship and counts the ones in view', async () => {
    renderPage();
    await screen.findByTestId('force-graph');
    const legend = document.getElementById('graph-edge-legend');
    expect(legend.textContent).toMatch(/computed by the conflict engine/);
    expect(legend.textContent).toMatch(/from ingest ordering/);
    expect(legend.textContent).toMatch(/SUPERSEDES1/);
    expect(legend.textContent).toMatch(/ABOUT2/);
  });

  it('draws SUPERSEDES corrections apart from other edges', async () => {
    renderPage();
    await screen.findByTestId('force-graph');
    const sup = { type: 'SUPERSEDES' };
    const about = { type: 'ABOUT' };
    expect(fg.last.linkColor(sup)).not.toBe(fg.last.linkColor(about));
    expect(fg.last.linkWidth(sup)).toBeGreaterThan(fg.last.linkWidth(about));
  });

  it('labels nodes by tail number and record id, not by UUID', async () => {
    renderPage();
    await screen.findByTestId('force-graph');
    const names = fg.last.graphData.nodes.map((n) => n.displayName).sort();
    expect(names).toEqual(['813SK', 'R1', 'R2']);
  });

  it('reports a load failure with retry and no stale "port 8000" advice', async () => {
    overview.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ data: { nodes, edges } });
    renderPage();
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).not.toMatch(/port 8000/);
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByTestId('force-graph')).toBeInTheDocument();
  });

  it('warns that the whole fleet is too dense to read', async () => {
    const big = Array.from({ length: 1600 }, (_, i) => ({ source: 'r1', target: 'a1', type: 'ABOUT', i }));
    overview.mockResolvedValue({ data: { nodes, edges: big } });
    renderPage();
    await screen.findByTestId('force-graph');
    expect(document.getElementById('graph-density-warning')).toBeNull();
    fireEvent.change(screen.getByLabelText('Aircraft'), { target: { value: '' } });
    expect(await screen.findByText(/too dense to read/)).toBeInTheDocument();
  });
});

describe('GraphSidePanel', () => {
  const rec = nodes[2];
  const renderPanel = (node, props = {}) =>
    render(<ThemeProvider><MemoryRouter><GraphSidePanel node={{ ...node, displayName: node.record_id || node.tail_number }} onClose={() => {}} {...props} /></MemoryRouter></ThemeProvider>);

  it('shows a record’s stored fields and links to its asset history entry', () => {
    renderPanel(rec, { assetUuid: 'a1' });
    expect(screen.getByText('PUMP')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open in asset history/ })).toHaveAttribute('href', '/app/asset-history/a1#R1');
  });

  it('does not show the stored confidence, which can be a legacy 1.00 placeholder', () => {
    renderPanel({ ...rec, confidence: 1, status: 'superseded' }, { assetUuid: 'a1' });
    expect(screen.queryByText(/Confidence/)).toBeNull();
    expect(screen.queryByText('1.00')).toBeNull();
  });

  it('shows no link for a record whose aircraft cannot be resolved', () => {
    renderPanel(rec);
    expect(screen.queryByRole('link', { name: /Open in asset history/ })).toBeNull();
  });

  it('links an aircraft node to its own history', () => {
    renderPanel(nodes[0]);
    expect(screen.getByRole('link', { name: /Open in asset history/ })).toHaveAttribute('href', '/app/asset-history/a1');
  });
});
