import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { Link, MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import Diagnostics from '../pages/Diagnostics';
import AssetHistory from '../pages/AssetHistory';
import * as client from '../api/client';
import { ACTIVE_DIAGNOSTIC_WORKSPACE_KEY } from '../utils/diagnosticWorkspace';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    assets: vi.fn(),
    assetHistory: vi.fn(),
    records: vi.fn(),
    diagnose: vi.fn(),
    copilotTurn: vi.fn(),
  },
}));

const record = {
  id: 'record-node-1',
  record_id: 'SWIA2024010100001',
  asset_id: '1',
  asset_key: 'N813SK',
  occurred_at: '2024-01-01',
  status: 'auto_accepted',
  part_name: 'DRAG ANGLE',
  text: 'Historical drag angle crack report.',
};

const turn = {
  session_id: 'active-session',
  reply: 'Inspect the drag angle using SWIA2024010100001.',
  case_state: {
    symptoms: ['drag angle crack'], observations: ['crack grows under load'], checks_done: [], ruled_out: [], open_questions: [],
  },
  ranked_checks: [{
    rank: 1, part_name: 'DRAG ANGLE', score: 0.42, evidence_count: 1,
    evidence_record_ids: [record.record_id], sources: ['asset_history'],
  }],
  ranking_delta: { moved_up: [], moved_down: [], new: [{ part_name: 'DRAG ANGLE', rank: 1 }], dropped: [], newly_cited_records: [record.record_id] },
  evidence: [{ ...record, asset_id: 'N813SK', is_superseded: false }],
  citation_validation: { valid_ids: [record.record_id], invalid_ids: [], all_valid: true },
  llm_status: 'available',
  warnings: [],
};

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}{location.hash}</output>;
}

function BrowserControls() {
  const navigate = useNavigate();
  return (
    <div>
      <button type="button" onClick={() => navigate(-1)}>Browser back</button>
      <button type="button" onClick={() => navigate(1)}>Browser forward</button>
    </div>
  );
}

function TestRoutes() {
  return (
    <>
      <nav>
        <Link to="/app/assets">Assets navigation</Link>
        <Link to="/app/diagnostics">Diagnostics navigation</Link>
      </nav>
      <BrowserControls />
      <Routes>
        <Route path="/app/diagnostics" element={<Diagnostics />} />
        <Route path="/app/asset-history/:assetId" element={<AssetHistory />} />
        <Route path="/app/assets" element={<p>Assets page</p>} />
      </Routes>
      <LocationProbe />
    </>
  );
}

function renderRoutes(initialEntry = '/app/diagnostics') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <TestRoutes />
    </MemoryRouter>
  );
}

async function establishInvestigation() {
  await screen.findByRole('option', { name: 'N813SK' });
  fireEvent.change(screen.getByLabelText('Aircraft filter'), { target: { value: '1' } });
  fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'drag angle crack' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send' }));
  await screen.findByText(/Inspect the drag angle using/);
  const liveRanking = screen.getByRole('region', { name: 'Live investigation ranking' });
  fireEvent.click(within(liveRanking).getByRole('button', { name: 'Inspect evidence for DRAG ANGLE' }));
  await within(liveRanking).findByText('Historical drag angle crack report.');
  return liveRanking;
}

describe('active diagnostic navigation', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.localStorage.clear();
    Element.prototype.scrollIntoView = vi.fn();
    HTMLElement.prototype.animate = vi.fn(() => ({ cancel: vi.fn() }));
    window.matchMedia = vi.fn().mockReturnValue({ matches: false });
    client.maintenanceAPI.assets.mockResolvedValue({ data: [
      { id: '1', tail_number: 'N813SK', record_count: 1 },
      { id: '2', tail_number: 'N900ZZ', record_count: 1 },
    ] });
    client.maintenanceAPI.assetHistory.mockResolvedValue({ data: { count: 1, records: [record] } });
    client.maintenanceAPI.records.mockResolvedValue({ data: { items: [], total: 0, next: null } });
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: turn });
  });

  it('returns from a linked record to the same investigation without inference or animation replay', async () => {
    renderRoutes();
    const liveRanking = await establishInvestigation();
    const history = screen.getByRole('log', { name: 'Conversation history' });
    const rail = screen.getByRole('complementary', { name: 'Investigation workspace panels' });
    Object.defineProperties(history, {
      scrollHeight: { configurable: true, value: 1000 },
      clientHeight: { configurable: true, value: 400 },
      scrollTop: { configurable: true, writable: true, value: 48 },
    });
    rail.scrollTop = 72;
    fireEvent.scroll(history);
    fireEvent.scroll(rail);
    fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'unsent inspection note' } });

    HTMLElement.prototype.animate.mockClear();
    fireEvent.click(within(liveRanking).getByRole('button', { name: /Open full record view/ }));
    expect(await screen.findByRole('link', { name: /Back to investigation/i })).toHaveAttribute('href', '/app/diagnostics');
    expect(screen.getByRole('link', { name: /Back to Assets/i })).toBeDefined();
    await screen.findByText('Linked record');
    expect(document.getElementById(`record-${record.record_id}`)).toHaveAttribute('data-linked', 'true');

    fireEvent.click(screen.getByRole('link', { name: /Back to investigation/i }));
    await screen.findByText(/Inspect the drag angle using/);
    const restoredRanking = screen.getByRole('region', { name: 'Live investigation ranking' });
    expect(within(restoredRanking).getByRole('button', { name: 'Inspect evidence for DRAG ANGLE' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getAllByText('crack grows under load').length).toBeGreaterThan(0);
    expect(screen.getByLabelText('Aircraft filter')).toHaveValue('1');
    expect(screen.getByLabelText('Message')).toHaveValue('unsent inspection note');
    expect(screen.getByRole('log', { name: 'Conversation history' }).scrollTop).toBe(48);
    expect(screen.getByRole('complementary', { name: 'Investigation workspace panels' }).scrollTop).toBe(72);
    expect(client.maintenanceAPI.copilotTurn).toHaveBeenCalledTimes(1);
    expect(client.maintenanceAPI.assetHistory).toHaveBeenCalledTimes(2);
    expect(HTMLElement.prototype.animate).not.toHaveBeenCalled();
  });

  it('keeps the workspace through Asset History, Assets, and sidebar-style Diagnostics navigation', async () => {
    renderRoutes();
    const liveRanking = await establishInvestigation();
    fireEvent.click(within(liveRanking).getByRole('button', { name: /Open full record view/ }));
    await screen.findByText('Linked record');
    fireEvent.click(screen.getByRole('link', { name: /Back to Assets/i }));
    expect(await screen.findByText('Assets page')).toBeDefined();
    fireEvent.click(screen.getByRole('link', { name: 'Diagnostics navigation' }));

    await screen.findByText(/Inspect the drag angle using/);
    expect(within(screen.getByRole('region', { name: 'Live investigation ranking' })).getByRole('button', { name: 'Inspect evidence for DRAG ANGLE' })).toHaveAttribute('aria-pressed', 'true');
    expect(client.maintenanceAPI.copilotTurn).toHaveBeenCalledTimes(1);
  });

  it('preserves source-aware behavior through browser Back and Forward', async () => {
    renderRoutes();
    const liveRanking = await establishInvestigation();
    fireEvent.click(within(liveRanking).getByRole('button', { name: /Open full record view/ }));
    await screen.findByText('Linked record');

    fireEvent.click(screen.getByRole('button', { name: 'Browser back' }));
    await screen.findByText(/Inspect the drag angle using/);
    expect(client.maintenanceAPI.copilotTurn).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: 'Browser forward' }));
    await screen.findByText('Linked record');
    expect(screen.getByRole('link', { name: /Back to investigation/i })).toBeDefined();
  });

  it('restores across refresh, preserves manual sessions, and lets New investigation clear only the active workspace', async () => {
    const firstRender = renderRoutes();
    await establishInvestigation();
    fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'draft survives refresh' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save session' }));
    firstRender.unmount();

    HTMLElement.prototype.animate.mockClear();
    const restoredRender = renderRoutes();
    await screen.findByText(/Inspect the drag angle using/);
    expect(screen.getByLabelText('Message')).toHaveValue('draft survives refresh');
    expect(screen.getByRole('button', { name: 'drag angle crack' })).toBeDefined();
    expect(client.maintenanceAPI.copilotTurn).toHaveBeenCalledTimes(1);
    expect(HTMLElement.prototype.animate).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'New investigation' }));
    expect(screen.getByText('Start an evidence-grounded investigation')).toBeDefined();
    expect(screen.getByRole('button', { name: 'drag angle crack' })).toBeDefined();
    restoredRender.unmount();

    renderRoutes();
    expect(screen.getByText('Start an evidence-grounded investigation')).toBeDefined();
    expect(screen.getByRole('button', { name: 'drag angle crack' })).toBeDefined();
    expect(client.maintenanceAPI.copilotTurn).toHaveBeenCalledTimes(1);
  });

  it('ignores an invalid active snapshot without disturbing Diagnostics', async () => {
    window.localStorage.setItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY, JSON.stringify({ version: 999, thread: 'invalid' }));
    renderRoutes();
    expect(screen.getByText('Start an evidence-grounded investigation')).toBeDefined();
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY)).toBeNull());
    expect(client.maintenanceAPI.copilotTurn).not.toHaveBeenCalled();
  });

  it('preserves an explicitly switched aircraft without starting a new turn', async () => {
    renderRoutes();
    await screen.findByRole('option', { name: 'N900ZZ' });
    fireEvent.change(screen.getByLabelText('Aircraft filter'), { target: { value: '2' } });
    fireEvent.click(screen.getByRole('link', { name: 'Assets navigation' }));
    await screen.findByText('Assets page');
    fireEvent.click(screen.getByRole('link', { name: 'Diagnostics navigation' }));
    expect(await screen.findByLabelText('Aircraft filter')).toHaveValue('2');
    expect(client.maintenanceAPI.copilotTurn).not.toHaveBeenCalled();
  });
});
