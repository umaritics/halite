import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import Diagnostics from '../pages/Diagnostics';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    assets: vi.fn(),
    diagnose: vi.fn()
  }
}));

const mockAssets = [
  { id: '1', tail_number: '813SK', record_count: 50 },
  { id: '2', tail_number: '508AE', record_count: 20 }
];

const mockResult = {
  ranked_checks: [
    { part_name: 'DRAG ANGLE', evidence_count: 4, sources: ['asset_history'], rank: 1 }
  ],
  explanation: 'DRAG ANGLE is top-ranked...',
  evidence: [
    { record_id: 'DEMO1', asset_id: '813SK', occurred_at: '2025-12-28', part_name: 'DRAG ANGLE', is_superseded: false },
    { record_id: 'DEMO2', asset_id: '813SK', occurred_at: '2025-12-01', part_name: 'DRAG ANGLE', is_superseded: true }
  ],
  rare_cases: [
    { record_id: 'RARE1', asset_id: 'AALA', occurred_at: '2024-01-01', part_name: 'DRAG ANGLE', resolution_text: 'Fixed.' }
  ],
  context_size: { asset_records: 30, fleet_records: 20, fleet_assets: 18 }
};

describe('Diagnostics', () => {
  it('renders ranked list, evidence links, and handles rare-case expansion', async () => {
    client.maintenanceAPI.assets.mockResolvedValue({ data: mockAssets });
    client.maintenanceAPI.diagnose.mockResolvedValue({ data: mockResult });

    render(
      <MemoryRouter>
        <Diagnostics />
      </MemoryRouter>
    );

    // Select asset
    fireEvent.click(screen.getByRole('button', { name: /select aircraft/i }));
    await waitFor(() => screen.getByText('813SK'));
    fireEvent.click(screen.getByText('813SK'));

    // Input symptom
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'crack at drag angle' } });

    // Submit
    fireEvent.click(screen.getByRole('button', { name: /run diagnostic/i }));

    // Wait for ranked list
    await waitFor(() => screen.getByText('Ranked Inspection Order'));
    expect(screen.getByText('DRAG ANGLE')).toBeDefined();
    expect(screen.getByText(/seen in 4 prior cases/)).toBeDefined();

    // Check evidence citation links
    expect(screen.getByText('DEMO1')).toBeDefined();
    expect(screen.getByText('DEMO2')).toBeDefined();
    expect(screen.getByText('superseded')).toBeDefined();

    // Check context line
    expect(screen.getByText(/Answered from/)).toBeDefined();
    expect(screen.getByText('30')).toBeDefined(); // asset_records
    expect(screen.getAllByText('20')[0]).toBeDefined(); // fleet_records
    expect(screen.getByText('18')).toBeDefined(); // fleet_assets

    // Check rare cases expansion
    const expandBtn = screen.getByText(/1 occurrence in the corpus/);
    expect(expandBtn).toBeDefined();
    
    // Rare case should not be visible before click
    expect(screen.queryByText('RARE1')).toBeNull();
    
    // Click expand
    fireEvent.click(expandBtn);
    expect(screen.getByText('RARE1')).toBeDefined();
  });

  it('renders error state on API failure', async () => {
    client.maintenanceAPI.assets.mockResolvedValue({ data: mockAssets });
    client.maintenanceAPI.diagnose.mockRejectedValue({ response: { data: { detail: 'Something went wrong' } } });

    render(
      <MemoryRouter>
        <Diagnostics />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: /select aircraft/i }));
    await waitFor(() => screen.getByText('813SK'));
    fireEvent.click(screen.getByText('813SK'));

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'bad symptom' } });
    fireEvent.click(screen.getByRole('button', { name: /run diagnostic/i }));

    await waitFor(() => screen.getByText('Something went wrong'));
  });
});
