import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Assets from '../features/assets/Assets';
import AssetHistory from '../features/assets/AssetHistory';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    assets: vi.fn(),
    assetHistory: vi.fn(),
  }
}));

describe('Assets', () => {
  it('renders assets', async () => {
    client.maintenanceAPI.assets.mockResolvedValue({
      data: [{ id: '1', tail_number: 'N123', record_count: 5 }]
    });

    render(
      <MemoryRouter>
        <Assets />
      </MemoryRouter>
    );
    
    expect(screen.getByText('Loading assets...')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByText('N123')).toBeInTheDocument();
    });
  });
});

describe('Assets error and empty states', () => {
  beforeEach(() => vi.resetAllMocks());

  const renderAssets = () => render(<MemoryRouter><Assets /></MemoryRouter>);

  it('shows an error with retry instead of a blank page when the request fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    client.maintenanceAPI.assets
      .mockRejectedValueOnce({ code: 'ERR_NETWORK', message: 'Network Error', request: {} })
      .mockResolvedValueOnce({ data: [{ id: '1', tail_number: 'N123', record_count: 5 }] });
    renderAssets();

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load assets');
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('N123')).toBeInTheDocument();
    expect(client.maintenanceAPI.assets).toHaveBeenCalledTimes(2);
  });

  it('shows an empty state when there are no assets', async () => {
    client.maintenanceAPI.assets.mockResolvedValue({ data: [] });
    renderAssets();
    expect(await screen.findByText('No assets yet')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('shows an empty state when the search matches nothing', async () => {
    client.maintenanceAPI.assets.mockResolvedValue({
      data: [{ id: '1', tail_number: 'N123', record_count: 5 }],
    });
    renderAssets();
    await screen.findByText('N123');
    fireEvent.change(screen.getByLabelText('Search assets by tail number'), { target: { value: 'ZZZ' } });
    expect(screen.getByText('No assets match your search')).toBeInTheDocument();
    expect(screen.getByLabelText('Sort assets')).toBeInTheDocument();
  });
});

describe('AssetHistory', () => {
  it('renders empty state', async () => {
    client.maintenanceAPI.assetHistory.mockResolvedValue({
      data: { records: [] }
    });

    render(
      <MemoryRouter>
        <AssetHistory />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No records for this asset yet.')).toBeInTheDocument();
    });
  });

  it('renders populated and superseded records', async () => {
    client.maintenanceAPI.assetHistory.mockResolvedValue({
      data: {
        count: 2,
        records: [
          { record_id: 'R1', occurred_at: '2025-01-01T00:00:00Z', status: 'accepted', part_name: 'Engine' },
          { record_id: 'R2', occurred_at: '2025-01-02T00:00:00Z', status: 'superseded', corrected_by: { record_id: 'R3', part_name: 'Bracket' }, part_name: 'Wing' }
        ]
      }
    });

    render(
      <MemoryRouter>
        <AssetHistory />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Engine')).toBeInTheDocument();
      expect(screen.getByText('Superseded')).toBeInTheDocument();
      expect(screen.getByText(/component changed Wing → Bracket/)).toBeInTheDocument();
      expect(screen.getByText('R3').getAttribute('href')).toMatch(/#R3$/);
    });
  });
});
