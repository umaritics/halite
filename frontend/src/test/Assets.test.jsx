import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Assets from '../pages/Assets';
import AssetHistory from '../pages/AssetHistory';
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
          { record_id: 'R2', occurred_at: '2025-01-02T00:00:00Z', status: 'superseded', superseding_record: 'R3', supersede_rationale: 'Testing', part_name: 'Wing' }
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
      expect(screen.getByText(/Superseded by R3/)).toBeInTheDocument();
    });
  });
});
