import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ReviewQueue from '../features/integrity/ReviewQueue';
import * as client from '../api/client';
import { integrityAPI } from '../features/integrity/api';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    assets: vi.fn(),
    reviewQueue: vi.fn(),
    getRecord: vi.fn(),
    assetHistory: vi.fn(),
    accept: vi.fn(),
    reject: vi.fn(),
    analysisStatus: vi.fn(),
    corrections: vi.fn(),
  },
}));
vi.mock('../features/integrity/api', () => ({ integrityAPI: { proposal: vi.fn() } }));
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ hasRole: () => true, user: { role: 'supervisor' } }),
}));

const api = client.maintenanceAPI;

const proposal = (overrides = {}) => ({
  data: {
    record: { record_id: 'R1', candidates_considered: 3, history_size: 9 },
    proposed_prior: { record_id: 'R0', occurred_at: '2024-01-01T00:00:00Z', part_name: 'FUEL PUMP', text: 'Old' },
    proposal_source: 'stored',
    label: 'supersedes',
    rationale: 'Corrects the part.',
    confidence: 0.8,
    method: 'llm',
    link: null,
    changed_fields: [],
    ...overrides,
  },
});

const renderPage = () => render(<MemoryRouter><ReviewQueue /></MemoryRouter>);

beforeEach(() => {
  vi.resetAllMocks();
  api.assets.mockResolvedValue({ data: [] });
  api.analysisStatus.mockResolvedValue({ data: { unscored: 0, scored: 1, reviewed: 0 } });
  api.corrections.mockResolvedValue({ data: { items: [], total: 0, next: null, summary: {} } });
  api.reviewQueue.mockResolvedValue({
    data: [{ record_id: 'R1', asset_key: 'N1', occurred_at: '2025-01-01T00:00:00Z', part_name: 'X', text: 't', history_size: 9 }],
  });
  integrityAPI.proposal.mockResolvedValue(proposal());
});

describe('review queue reads the stored proposal', () => {
  it('calls proposal for the open item and never getRecord', async () => {
    renderPage();
    await screen.findByText('Corrects the part.');
    expect(integrityAPI.proposal).toHaveBeenCalledWith('R1');
    expect(api.getRecord).not.toHaveBeenCalled();
  });

  it('lists the changed fields', async () => {
    integrityAPI.proposal.mockResolvedValue(proposal({
      changed_fields: [{ field: 'part_name', prior: 'UNKNOWN', new: 'FUEL PUMP' }],
    }));
    renderPage();
    await screen.findByText('Part: UNKNOWN → FUEL PUMP');
  });

  it('says so when nothing changed', async () => {
    renderPage();
    await screen.findByText(/no tracked fields changed/i);
  });

  it.each([
    [{ method: 'llm' }, 'Model proposal'],
    [{ method: 'llm', link: { method: 'explicit_citation' } }, 'Linked by citation'],
    [{ method: 'llm', link: { method: 'human' } }, 'Human decision'],
  ])('labels how the pair was proposed: %j', async (extra, text) => {
    integrityAPI.proposal.mockResolvedValue(proposal(extra));
    renderPage();
    await screen.findByText(text);
  });

  it('notes a recomputed prior', async () => {
    integrityAPI.proposal.mockResolvedValue(proposal({ proposal_source: 'recomputed' }));
    renderPage();
    await screen.findByText(/re-derived just now/i);
  });

  it('does not show the recomputed note for a stored prior', async () => {
    renderPage();
    await screen.findByText('Corrects the part.');
    expect(screen.queryByText(/re-derived/i)).toBeNull();
  });

  it('explains a missing prior in a sentence', async () => {
    integrityAPI.proposal.mockResolvedValue(proposal({ proposed_prior: null, proposal_source: 'none' }));
    renderPage();
    await screen.findByText(/no earlier record was proposed/i);
  });

  it('shows the error state and retries', async () => {
    integrityAPI.proposal.mockRejectedValueOnce({ response: { status: 503, data: { detail: 'down' } } });
    renderPage();
    await screen.findByText('Finding details unavailable');
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await screen.findByText('Corrects the part.');
    expect(integrityAPI.proposal).toHaveBeenCalledTimes(2);
  });
});

describe('confirmation after a decision', () => {
  it('names the prior after accept created a link', async () => {
    api.accept.mockResolvedValue({ data: { link: 'created', prior_record_id: 'R0' } });
    renderPage();
    await screen.findByText('Corrects the part.');
    fireEvent.click(screen.getByRole('button', { name: /^accept$/i }));
    await screen.findByText('Link created to R0');
    await screen.findByText('Accepted record R1');
  });

  it('says a link was confirmed', async () => {
    api.accept.mockResolvedValue({ data: { link: 'confirmed', prior_record_id: 'R0' } });
    renderPage();
    await screen.findByText('Corrects the part.');
    fireEvent.click(screen.getByRole('button', { name: /^accept$/i }));
    await screen.findByText('Link confirmed');
  });

  it('says a link was removed after reject', async () => {
    api.reject.mockResolvedValue({ data: { link: 'removed', prior_record_id: 'R0' } });
    renderPage();
    await screen.findByText('Corrects the part.');
    fireEvent.change(screen.getByPlaceholderText(/review note/i), { target: { value: 'No' } });
    fireEvent.click(screen.getByRole('button', { name: /^reject$/i }));
    await screen.findByText('Link removed');
  });

  it('adds nothing when no link was touched', async () => {
    api.accept.mockResolvedValue({ data: { link: 'none', prior_record_id: '' } });
    renderPage();
    await screen.findByText('Corrects the part.');
    fireEvent.click(screen.getByRole('button', { name: /^accept$/i }));
    await screen.findByText('Accepted record R1');
    expect(screen.queryByText(/^Link /)).toBeNull();
  });
});
