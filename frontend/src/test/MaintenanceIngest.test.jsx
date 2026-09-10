import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import MaintenanceIngest from '../pages/MaintenanceIngest';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    ingest: vi.fn(),
    ingestFile: vi.fn(),
    submitRecord: vi.fn()
  }
}));

describe('MaintenanceIngest', () => {
  it('renders corpus ingest and processes result', async () => {
    client.maintenanceAPI.ingest.mockResolvedValue({
      data: {
        assets_created: 10,
        records_created: 20,
        rows_skipped_no_tail: 0,
        rows_skipped_bad_date: 1,
        duplicates_skipped: 2
      }
    });

    render(
      <MemoryRouter>
        <MaintenanceIngest />
      </MemoryRouter>
    );

    const ingestBtn = screen.getByText('Ingest Corpus');
    act(() => {
      ingestBtn.click();
    });

    await waitFor(() => {
      expect(screen.getByText('10')).toBeInTheDocument(); // assets
      expect(screen.getByText('20')).toBeInTheDocument(); // records
    });
  });
});
