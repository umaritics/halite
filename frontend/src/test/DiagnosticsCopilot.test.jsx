import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import Diagnostics from '../pages/Diagnostics';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    assets: vi.fn(),
    diagnose: vi.fn(),
    copilotTurn: vi.fn(),
  },
}));

const assets = [{ id: '1', tail_number: 'N813SK', record_count: 3 }];
const baseTurn = {
  session_id: 'session-1',
  reply: 'Inspect the drag angle using SWIA2024010100001.',
  case_state: {
    symptoms: ['drag angle crack'], observations: [], checks_done: [], ruled_out: [], open_questions: [],
  },
  ranked_checks: [{
    rank: 1, part_name: 'DRAG ANGLE', score: 0.42, evidence_count: 1,
    evidence_record_ids: ['SWIA2024010100001'], sources: ['fleet_match'],
  }],
  ranking_delta: { moved_up: [], moved_down: [], new: [{ part_name: 'DRAG ANGLE', rank: 1 }], dropped: [], newly_cited_records: ['SWIA2024010100001'] },
  evidence: [{ record_id: 'SWIA2024010100001', asset_id: 'N813SK', occurred_at: '2024-01-01', part_name: 'DRAG ANGLE', is_superseded: false }],
  citation_validation: { valid_ids: ['SWIA2024010100001'], invalid_ids: [], all_valid: true },
  llm_status: 'available',
  warnings: [],
};

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}{location.hash}</output>;
}

function renderPage(withLocation = false) {
  return render(
    <MemoryRouter initialEntries={['/app/diagnostics']}>
      <Diagnostics />
      {withLocation && <LocationProbe />}
    </MemoryRouter>
  );
}

async function send(text) {
  fireEvent.change(screen.getByLabelText('Message'), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: 'Send' }));
}

describe('Diagnostics copilot', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.localStorage.clear();
    client.maintenanceAPI.assets.mockResolvedValue({ data: assets });
  });

  it('defaults to All fleet and carries accumulated case state across turns', async () => {
    const secondTurn = {
      ...baseTurn,
      reply: 'The pump moved up after the new observation.',
      case_state: { ...baseTurn.case_state, observations: ['hydraulic leak'] },
      ranking_delta: { moved_up: [{ part_name: 'PUMP', from_rank: 3, to_rank: 1 }], moved_down: [], new: [], dropped: [], newly_cited_records: [] },
      ranked_checks: [{ ...baseTurn.ranked_checks[0], part_name: 'PUMP', rank: 1 }],
    };
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: baseTurn })
      .mockResolvedValueOnce({ data: secondTurn });

    renderPage();
    expect(screen.getByLabelText('Aircraft filter')).toHaveValue('');
    expect(screen.getByRole('option', { name: 'All fleet' })).toBeDefined();

    await send('crack found on drag angle');
    const firstNarrative = await screen.findByText(/Inspect the drag angle/);
    const initialUpdates = screen.getByRole('region', { name: 'Investigation Updates' });
    expect(within(initialUpdates).getByText('Initial ranking established')).toBeDefined();
    expect(within(initialUpdates).getByText(/1 ranked component/)).toBeDefined();
    expect(within(initialUpdates).getByText(/1 displayed below/)).toBeDefined();
    expect(screen.queryByText('Newly introduced')).toBeNull();
    expect(initialUpdates.compareDocumentPosition(firstNarrative) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    await send('hydraulic leak observed');
    await screen.findByText(/pump moved up/i);
    const updates = screen.getAllByRole('region', { name: 'Investigation Updates' }).at(-1);
    expect(within(updates).getByText('Moved up')).toBeDefined();
    expect(within(updates).getByText('Rank 3 → Rank 1')).toBeDefined();
    expect(client.maintenanceAPI.copilotTurn).toHaveBeenLastCalledWith(expect.objectContaining({
      session_id: 'session-1',
      message: 'hydraulic leak observed',
      case_state: baseTurn.case_state,
    }));
  });

  it('shows upward, downward, new, and dropped ranking changes with exact positions', async () => {
    const changedTurn = {
      ...baseTurn,
      reply: 'The deterministic ranking changed.',
      ranked_checks: [
        { ...baseTurn.ranked_checks[0], part_name: 'SUPPORT ANGLE', rank: 4 },
        { ...baseTurn.ranked_checks[0], part_name: 'DRAG ANGLE', rank: 5 },
        { ...baseTurn.ranked_checks[0], part_name: 'SEAL', rank: 3 },
      ],
      ranking_delta: {
        moved_up: [{ part_name: 'SUPPORT ANGLE', from_rank: 13, to_rank: 4 }],
        moved_down: [{ part_name: 'DRAG ANGLE', from_rank: 1, to_rank: 5 }],
        new: [{ part_name: 'SEAL', rank: 3 }],
        dropped: [{ part_name: 'STRINGER SPLICE', from_rank: 12 }],
        newly_cited_records: [],
      },
    };
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: changedTurn });

    renderPage();
    await send('hydraulic leak changed the ranking');
    const updates = await screen.findByRole('region', { name: 'Investigation Updates' });

    expect(within(updates).getByText('Moved up')).toBeDefined();
    expect(within(updates).getByText('SUPPORT ANGLE')).toBeDefined();
    expect(within(updates).getByText('Rank 13 → Rank 4')).toBeDefined();
    expect(within(updates).getByText('Moved down')).toBeDefined();
    expect(within(updates).getByText('Rank 1 → Rank 5')).toBeDefined();
    expect(within(updates).getByText('Newly introduced')).toBeDefined();
    expect(within(updates).getByText('Entered at rank 3')).toBeDefined();

    const more = within(updates).getByText('Show 1 more ranking update');
    expect(more.closest('details')).not.toHaveAttribute('open');
    fireEvent.click(more);
    expect(within(updates).getByText('Dropped from ranking')).toBeDefined();
    expect(within(updates).getByText('STRINGER SPLICE')).toBeDefined();
    expect(within(updates).getByText('Previously rank 12 · no longer ranked')).toBeDefined();
  });

  it('summarises an initial 21-component ranking with ten displayed checks and collapsed evidence', async () => {
    const rankedChecks = Array.from({ length: 10 }, (_, index) => ({
      ...baseTurn.ranked_checks[0],
      part_name: `COMPONENT ${index + 1}`,
      rank: index + 1,
    }));
    const introduced = [
      ...rankedChecks.map(check => ({ part_name: check.part_name, rank: check.rank })),
      ...Array.from({ length: 11 }, (_, index) => ({
        part_name: index === 9 ? 'STRINGER SPLICE' : index === 10 ? 'SUPPORT ANGLE' : `COMPONENT ${index + 11}`,
        rank: index + 11,
      })),
    ];
    const evidenceIds = Array.from({ length: 8 }, (_, index) => `SWIA20240101000${index + 10}`);
    const evidence = evidenceIds.map(recordId => ({
      ...baseTurn.evidence[0], record_id: recordId,
    }));
    client.maintenanceAPI.copilotTurn.mockResolvedValue({
      data: {
        ...baseTurn,
        ranked_checks: rankedChecks,
        evidence,
        ranking_delta: { moved_up: [], moved_down: [], new: introduced, dropped: [], newly_cited_records: evidenceIds },
      },
    });

    renderPage(true);
    await waitFor(() => expect(client.maintenanceAPI.assets).toHaveBeenCalled());
    await send('initial visual QA fixture');
    const updates = await screen.findByRole('region', { name: 'Investigation Updates' });
    expect(within(updates).getByText('Initial ranking established')).toBeDefined();
    expect(within(updates).getByText(/21 ranked components/)).toBeDefined();
    expect(within(updates).getByText(/10 displayed below/)).toBeDefined();
    expect(within(updates).getByText(/8 newly cited evidence records/)).toBeDefined();
    expect(within(updates).getByText('COMPONENT 1')).toBeDefined();
    expect(within(updates).getByText('COMPONENT 2')).toBeDefined();
    expect(within(updates).getByText('COMPONENT 3')).toBeDefined();
    expect(within(updates).queryByText('COMPONENT 4')).toBeNull();
    expect(within(updates).queryByText('Newly introduced')).toBeNull();

    const disclosure = within(updates).getByText('View 8 evidence record IDs');
    const evidenceDetails = disclosure.closest('details');
    expect(evidenceDetails).not.toHaveAttribute('open');
    expect(within(evidenceDetails).getByRole('button', { name: evidenceIds[0] })).toBeDefined();
    expect(within(updates).getAllByText(evidenceIds[0])).toHaveLength(1);
    fireEvent.click(disclosure);
    expect(evidenceDetails).toHaveAttribute('open');
    fireEvent.click(within(evidenceDetails).getByRole('button', { name: evidenceIds[0] }));
    expect(screen.getByTestId('location')).toHaveTextContent(`/app/asset-history/1#${evidenceIds[0]}`);
  });

  it('shows three newly cited links and puts additional records in a collapsed disclosure', async () => {
    const evidenceIds = Array.from({ length: 7 }, (_, index) => `SWIA20240202000${index + 10}`);
    const evidenceTurn = {
      ...baseTurn,
      reply: 'Additional supporting evidence was found.',
      evidence: evidenceIds.map(recordId => ({ ...baseTurn.evidence[0], record_id: recordId })),
      ranking_delta: { moved_up: [], moved_down: [], new: [], dropped: [], newly_cited_records: evidenceIds },
    };
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: evidenceTurn });

    renderPage(true);
    await waitFor(() => expect(client.maintenanceAPI.assets).toHaveBeenCalled());
    await send('add the latest supporting record');
    const updates = await screen.findByRole('region', { name: 'Investigation Updates' });

    expect(within(updates).getByText('Ranking unchanged; new supporting records were added.')).toBeDefined();
    expect(within(updates).getByText(/7 newly cited evidence records/)).toBeDefined();
    const visibleRecords = within(updates).getByLabelText('Newly cited evidence records');
    expect(within(visibleRecords).getAllByRole('button')).toHaveLength(3);
    expect(within(visibleRecords).getByRole('button', { name: evidenceIds[0] })).toBeDefined();
    expect(within(updates).getAllByText(evidenceIds[0])).toHaveLength(1);

    const disclosure = within(updates).getByText('Show 4 more evidence records');
    const evidenceDetails = disclosure.closest('details');
    expect(evidenceDetails).not.toHaveAttribute('open');
    expect(within(evidenceDetails).getByRole('button', { name: evidenceIds[3] })).toBeDefined();
    fireEvent.click(disclosure);
    expect(evidenceDetails).toHaveAttribute('open');
    expect(within(evidenceDetails).getByRole('button', { name: evidenceIds[3] })).toBeDefined();
    fireEvent.click(within(visibleRecords).getByRole('button', { name: evidenceIds[0] }));
    expect(screen.getByTestId('location')).toHaveTextContent(`/app/asset-history/1#${evidenceIds[0]}`);
  });

  it('shows a subtle unchanged state when ranking and evidence do not change', async () => {
    client.maintenanceAPI.copilotTurn.mockResolvedValue({
      data: {
        ...baseTurn,
        ranking_delta: { moved_up: [], moved_down: [], new: [], dropped: [], newly_cited_records: [] },
      },
    });

    renderPage();
    await send('no new observation');
    const updates = await screen.findByRole('region', { name: 'Investigation Updates' });
    expect(within(updates).getByText('No rank change')).toBeDefined();
    expect(within(updates).getByText('Ranking unchanged after this update.')).toBeDefined();
  });

  it('shows model-unavailable output and retries a network failure without a blank success', async () => {
    client.maintenanceAPI.copilotTurn
      .mockRejectedValueOnce({ code: 'ERR_NETWORK', message: 'Network Error', request: {} })
      .mockResolvedValueOnce({ data: { ...baseTurn, reply: null, llm_status: 'unavailable' } });

    renderPage();
    await send('crack found');
    await screen.findByText('Cannot reach the Halite API');
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByText('Language model unavailable');
    expect(screen.getByText(/No narrative was invented/)).toBeDefined();
    expect(screen.getAllByText(/DRAG ANGLE/).length).toBeGreaterThan(0);
    expect(client.maintenanceAPI.copilotTurn).toHaveBeenCalledTimes(2);
  });

  it('saves, resumes, and deletes a local session', async () => {
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: baseTurn });
    renderPage();
    await send('crack found on drag angle');
    await screen.findByText(/Inspect the drag angle/);

    fireEvent.click(screen.getByRole('button', { name: 'Save session' }));
    expect(screen.getByRole('button', { name: 'crack found on drag angle' })).toBeDefined();
    fireEvent.click(screen.getByRole('button', { name: 'New investigation' }));
    expect(screen.getByText(/Start an evidence-grounded investigation/)).toBeDefined();

    fireEvent.click(screen.getByRole('button', { name: 'crack found on drag angle' }));
    expect(screen.getByText(/Inspect the drag angle/)).toBeDefined();
    fireEvent.click(screen.getByRole('button', { name: 'Delete crack found on drag angle' }));
    expect(screen.queryByRole('button', { name: 'crack found on drag angle' })).toBeNull();
  });

  it('deep-links evidence to the matching aircraft history record', async () => {
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: baseTurn });
    renderPage(true);
    await waitFor(() => expect(client.maintenanceAPI.assets).toHaveBeenCalled());
    await send('crack found');
    await screen.findByText(/Inspect the drag angle/);

    fireEvent.click(screen.getByText('View 1 evidence record ID'));
    fireEvent.click(screen.getAllByRole('button', { name: 'SWIA2024010100001' })[0]);
    expect(screen.getByTestId('location')).toHaveTextContent('/app/asset-history/1#SWIA2024010100001');
  });
});
