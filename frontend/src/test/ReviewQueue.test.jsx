import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import ReviewQueue from '../pages/ReviewQueue';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    reviewQueue: vi.fn(),
    submitRecord: vi.fn(),
    assetHistory: vi.fn(),
    accept: vi.fn(),
    reject: vi.fn(),
  }
}));

describe('ReviewQueue', () => {
  it('renders queued item and pruning line', async () => {
    client.maintenanceAPI.reviewQueue.mockResolvedValue({
      data: [{
        record_id: 'R1', 
        asset_key: 'N123',
        occurred_at: '2025-01-01T00:00:00Z',
        part_name: 'Engine',
        text: 'Broken'
      }]
    });

    client.maintenanceAPI.submitRecord.mockResolvedValue({
      data: {
        record_id: 'R1',
        candidates_considered: 5,
        confidence: 0.4,
        classification: { label: 'supersedes', rationale: 'LLM said so' },
        best_prior: {
          record_id: 'R0',
          occurred_at: '2024-01-01T00:00:00Z',
          part_name: 'Engine',
          text: 'Old Broken'
        }
      }
    });

    client.maintenanceAPI.assetHistory.mockResolvedValue({
      data: { count: 10 }
    });

    render(
      <MemoryRouter>
        <ReviewQueue />
      </MemoryRouter>
    );

    // Initial load
    expect(screen.getByText('Loading queue...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('INCOMING RECORD')).toBeInTheDocument();
      expect(screen.getByText('Examined 5 of 10 records on this asset.')).toBeInTheDocument();
      expect(screen.getByText('LLM said so')).toBeInTheDocument();
    });
  });
});
