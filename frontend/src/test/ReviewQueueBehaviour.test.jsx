import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ReviewQueue from '../features/integrity/ReviewQueue';
import * as client from '../api/client';
import { integrityAPI } from '../features/integrity/api';

vi.mock('../features/integrity/api', () => ({ integrityAPI: { proposal: vi.fn() } }));

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    assets: vi.fn(),
    reviewQueue: vi.fn(),
    assetHistory: vi.fn(),
    accept: vi.fn(),
    reject: vi.fn(),
    analysisStatus: vi.fn(),
    corrections: vi.fn(),
  },
}));

// Supervisor so the decision bar is active.
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ hasRole: () => true, user: { role: 'supervisor' } }),
}));

const api = client.maintenanceAPI;

const queueItem = (record_id, extra = {}) => ({
  record_id,
  asset_key: 'N123',
  occurred_at: '2025-01-01T00:00:00Z',
  part_name: 'Engine',
  text: `text of ${record_id}`,
  ...extra,
});

const detail = {
  data: {
    record: { record_id: 'R1', candidates_considered: 5 },
    confidence: 0.4,
    label: 'partial_supersedes',
    rationale: 'Partly resolved.',
    method: 'llm',
    link: null,
    changed_fields: [],
    proposal_source: 'stored',
    proposed_prior: { record_id: 'R0', occurred_at: '2024-01-01T00:00:00Z', part_name: 'Engine', text: 'Old' },
  },
};

const correctionsPage = (next, id) => ({
  data: {
    total: 2,
    next,
    summary: { total_corrections: 2, component_changed: 0, component_changed_pct: 0 },
    items: [{
      aircraft: { id: 'asset-1', tail_number: '105NN' },
      older_record: { id: `OLD${id}`, part_name: 'PUMP' },
      newer_record: { id: `NEW${id}`, part_name: 'PUMP' },
      component_changed: false,
      classification_label: 'supersedes',
      rationale: 'Corrected.',
      review_status: 'needs_review',
    }],
  },
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <ReviewQueue />
    </MemoryRouter>
  );

beforeEach(() => {
  vi.resetAllMocks();
  api.assets.mockResolvedValue({ data: [{ id: 'uuid-N123', tail_number: 'N123' }] });
  api.analysisStatus.mockResolvedValue({ data: { unscored: 0, scored: 1, reviewed: 0 } });
  api.assetHistory.mockResolvedValue({ data: { count: 10 } });
  api.reviewQueue.mockResolvedValue({ data: [queueItem('R1')] });
  integrityAPI.proposal.mockResolvedValue(detail);
});

describe('review changed event', () => {
  it('is dispatched after a successful accept', async () => {
    api.accept.mockResolvedValue({ data: {} });
    const heard = vi.fn();
    window.addEventListener('halite:review-changed', heard);
    renderPage();
    await screen.findByText('Partly resolved.');

    fireEvent.click(screen.getByRole('button', { name: /^accept$/i }));
    await screen.findByText('Accepted record R1');
    expect(heard).toHaveBeenCalledTimes(1);
    window.removeEventListener('halite:review-changed', heard);
  });

  it('is dispatched after a successful reject', async () => {
    api.reject.mockResolvedValue({ data: {} });
    const heard = vi.fn();
    window.addEventListener('halite:review-changed', heard);
    renderPage();
    await screen.findByText('Partly resolved.');

    fireEvent.change(screen.getByPlaceholderText(/review note/i), { target: { value: 'No' } });
    fireEvent.click(screen.getByRole('button', { name: /^reject$/i }));
    await screen.findByText('Rejected record R1');
    expect(heard).toHaveBeenCalledTimes(1);
    window.removeEventListener('halite:review-changed', heard);
  });

  it('is not dispatched when the server refuses', async () => {
    api.accept.mockRejectedValue({ response: { status: 409, data: { detail: 'cannot accept' } } });
    const heard = vi.fn();
    window.addEventListener('halite:review-changed', heard);
    renderPage();
    await screen.findByText('Partly resolved.');

    fireEvent.click(screen.getByRole('button', { name: /^accept$/i }));
    await screen.findByText('cannot accept');
    expect(heard).not.toHaveBeenCalled();
    window.removeEventListener('halite:review-changed', heard);
  });
});

describe('finding labels and history count', () => {
  it('shows the label in words', async () => {
    renderPage();
    await screen.findByText('Partly resolved.');
    expect(screen.getAllByText('Partially supersedes')).toHaveLength(2);
    expect(screen.queryByText('partial_supersedes')).toBeNull();
  });

  it('looks the history count up by asset UUID, not tail number', async () => {
    renderPage();
    await screen.findByText('Examined 5 of 10 records on this asset.');
    expect(api.assetHistory).toHaveBeenCalledWith('uuid-N123');
  });

  it('hides the count when the asset UUID cannot be resolved', async () => {
    api.assets.mockResolvedValue({ data: [] });
    renderPage();
    await screen.findByText('Examined 5 records on this asset.');
    expect(api.assetHistory).not.toHaveBeenCalled();
  });
});

describe('corrections tab', () => {
  const openTab = async () => {
    api.reviewQueue.mockResolvedValue({ data: [] });
    renderPage();
    fireEvent.click(screen.getByRole('tab', { name: 'Detected corrections' }));
  };

  it('shows readable labels and the new disclaimer', async () => {
    api.corrections.mockResolvedValue(correctionsPage(null, 1));
    await openTab();
    await screen.findByText('OLD1');
    expect(screen.getAllByText('Supersedes').length).toBeGreaterThan(0);
    expect(screen.getByText('Needs Review')).toBeInTheDocument();
    expect(screen.getByText('Linked by citation or proposed by the model. Results are not exhaustive.')).toBeInTheDocument();
    expect(screen.queryByText(/0\.66/)).toBeNull();
  });

  it('keeps the rows and offers a retry when Load more fails', async () => {
    api.corrections
      .mockResolvedValueOnce(correctionsPage(50, 1))
      .mockRejectedValueOnce({ code: 'ERR_NETWORK', message: 'Network Error', request: {} });
    await openTab();
    await screen.findByText('OLD1');

    fireEvent.click(screen.getByRole('button', { name: /load more/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Could not load more corrections.');
    expect(screen.getByText('OLD1')).toBeInTheDocument();

    api.corrections.mockResolvedValueOnce(correctionsPage(null, 2));
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));
    await screen.findByText('OLD2');
    expect(screen.getByText('OLD1')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull());
  });
});
