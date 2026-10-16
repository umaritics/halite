import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
    await screen.findByText(/Inspect the drag angle/);
    expect(screen.getByText('new')).toBeDefined();

    await send('hydraulic leak observed');
    await screen.findByText(/pump moved up/i);
    expect(screen.getByText('moved up')).toBeDefined();
    expect(client.maintenanceAPI.copilotTurn).toHaveBeenLastCalledWith(expect.objectContaining({
      session_id: 'session-1',
      message: 'hydraulic leak observed',
      case_state: baseTurn.case_state,
    }));
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
    expect(screen.getByText(/DRAG ANGLE/)).toBeDefined();
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

    fireEvent.click(screen.getAllByRole('button', { name: 'SWIA2024010100001' })[0]);
    expect(screen.getByTestId('location')).toHaveTextContent('/app/asset-history/1#SWIA2024010100001');
  });
});
