import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ReviewQueue from '../pages/ReviewQueue';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    assets: vi.fn(),
    reviewQueue: vi.fn(),
    submitRecord: vi.fn(),
    getRecord: vi.fn(),
    assetHistory: vi.fn(),
    accept: vi.fn(),
    reject: vi.fn(),
  }
}));

const api = client.maintenanceAPI;

const conflictDetail = (overrides = {}) => ({
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
    },
    ...overrides,
  }
});

const queueItem = (record_id, extra = {}) => ({
  record_id,
  asset_key: 'N123',
  occurred_at: '2025-01-01T00:00:00Z',
  part_name: 'Engine',
  text: `text of ${record_id}`,
  ...extra,
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <ReviewQueue />
    </MemoryRouter>
  );

describe('ReviewQueue', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.assetHistory.mockResolvedValue({ data: { count: 10 } });
    api.assets.mockResolvedValue({ data: [{ id: 'uuid-N123', tail_number: 'N123' }] });
  });

  it('renders queued item and pruning line', async () => {
    api.reviewQueue.mockResolvedValue({
      data: [{
        record_id: 'R1',
        asset_key: 'N123',
        occurred_at: '2025-01-01T00:00:00Z',
        part_name: 'Engine',
        text: 'Broken'
      }]
    });

    // Same conflict payload shape for the dry-run detail fetch
    // (GET /maintenance/records/{id}) and the submit call.
    const detail = conflictDetail();
    api.submitRecord.mockResolvedValue(detail);
    api.getRecord.mockResolvedValue(detail);

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

  describe('loading the queue', () => {
    it('a failed fetch is reported as a failure, never as an empty queue', async () => {
      api.reviewQueue.mockRejectedValueOnce({ code: 'ERR_NETWORK', message: 'Network Error', request: {} });
      renderPage();

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent('Could not load the review queue');
      expect(screen.queryByText(/nothing is awaiting review/i)).toBeNull();

      api.reviewQueue.mockResolvedValue({ data: [queueItem('R1')] });
      api.getRecord.mockResolvedValue(conflictDetail());
      fireEvent.click(screen.getByRole('button', { name: /try again/i }));
      await screen.findByText('INCOMING RECORD');
    });

    it('a genuinely empty queue says nothing is awaiting review', async () => {
      api.reviewQueue.mockResolvedValue({ data: [] });
      renderPage();
      await screen.findByText(/nothing is awaiting review/i);
    });

    it('uses the backend history_size and skips the extra history request', async () => {
      api.reviewQueue.mockResolvedValue({ data: [queueItem('R1', { history_size: 153 })] });
      api.getRecord.mockResolvedValue(conflictDetail());
      renderPage();

      await screen.findByText('Examined 5 of 153 records on this asset.');
      expect(api.assetHistory).not.toHaveBeenCalled();
    });

    it('explains what the conflict label means', async () => {
      api.reviewQueue.mockResolvedValue({ data: [queueItem('R1')] });
      api.getRecord.mockResolvedValue(conflictDetail({ classification: { label: 'contradicts', rationale: 'They disagree.' } }));
      renderPage();

      await screen.findByText(/mutually exclusive claims about the same part or event/i);
    });

    it('links the incoming and prior record to the asset history by asset UUID', async () => {
      api.reviewQueue.mockResolvedValue({ data: [queueItem('R1')] });
      api.getRecord.mockResolvedValue(conflictDetail());
      renderPage();

      await waitFor(() => expect(screen.getAllByRole('link', { name: /open in asset history/i })).toHaveLength(2));
      const hrefs = screen.getAllByRole('link', { name: /open in asset history/i }).map(a => a.getAttribute('href'));
      // The history endpoint is keyed by UUID; a tail-number URL would 404.
      expect(hrefs).toContain('/app/asset-history/uuid-N123#R1');
      expect(hrefs).toContain('/app/asset-history/uuid-N123#R0');
      expect(hrefs.some(h => h.includes('/N123#'))).toBe(false);
    });

    it('shows no history link rather than a broken one when the asset cannot be resolved', async () => {
      api.assets.mockRejectedValue({ code: 'ERR_NETWORK', message: 'Network Error', request: {} });
      api.reviewQueue.mockResolvedValue({ data: [queueItem('R1')] });
      api.getRecord.mockResolvedValue(conflictDetail());
      renderPage();

      await screen.findByText('LLM said so');
      expect(screen.queryByRole('link', { name: /open in asset history/i })).toBeNull();
    });
  });

  describe('finding details', () => {
    it('never shows the previous record\'s finding when the next one fails to load', async () => {
      api.reviewQueue.mockResolvedValue({
        data: [
          queueItem('R1', { occurred_at: '2025-02-01T00:00:00Z', classification_label: 'contradicts' }),
          queueItem('R2', {
            occurred_at: '2025-01-01T00:00:00Z',
            classification_label: 'partial_supersedes',
            classification_rationale: 'Stored rationale for R2',
            confidence: 0.3,
            candidates_considered: 7,
            history_size: 40,
          }),
        ],
      });
      api.getRecord.mockImplementation((id) =>
        id === 'R1'
          ? Promise.resolve(conflictDetail({ classification: { label: 'contradicts', rationale: 'FINDING FOR R1' } }))
          : Promise.reject({ response: { status: 503, data: { detail: 'model unavailable' } } })
      );

      renderPage();
      await screen.findByText('FINDING FOR R1');

      fireEvent.click(screen.getByRole('button', { name: /next/i }));

      await screen.findByText('Finding details unavailable');
      expect(screen.queryByText('FINDING FOR R1')).toBeNull();
      // The stored finding for R2 (real data from the queue) is shown, labelled as stored.
      expect(screen.getByText('Stored rationale for R2')).toBeDefined();
      expect(screen.getByText(/stored finding/i)).toBeDefined();
      expect(screen.getByText('Examined 7 of 40 records on this asset.')).toBeDefined();
    });

    it('Retry re-requests the finding', async () => {
      api.reviewQueue.mockResolvedValue({ data: [queueItem('R1')] });
      api.getRecord.mockRejectedValueOnce({ response: { status: 503, data: { detail: 'model unavailable' } } });
      renderPage();

      await screen.findByText('Finding details unavailable');
      api.getRecord.mockResolvedValue(conflictDetail({ classification: { label: 'supersedes', rationale: 'Recovered.' } }));
      fireEvent.click(screen.getByRole('button', { name: /retry/i }));

      await screen.findByText('Recovered.');
      expect(api.getRecord).toHaveBeenCalledTimes(2);
    });
  });

  describe('accept and reject change real data, so the UI waits for the server', () => {
    beforeEach(() => {
      api.reviewQueue.mockResolvedValue({ data: [queueItem('R1')] });
      api.getRecord.mockResolvedValue(conflictDetail());
    });

    it('does not remove the record or announce success until the server confirms', async () => {
      let confirm;
      api.accept.mockReturnValue(new Promise((r) => { confirm = r; }));
      renderPage();
      await screen.findByText('LLM said so');

      fireEvent.click(screen.getByRole('button', { name: /^accept$/i }));

      // Pending: still in the queue, no success message, buttons locked.
      await screen.findByRole('button', { name: /accepting/i });
      expect(screen.getByText('INCOMING RECORD')).toBeDefined();
      expect(screen.queryByText(/Accepted record R1/)).toBeNull();
      expect(screen.getByRole('button', { name: /accepting/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /^reject$/i })).toBeDisabled();

      // A second click while pending must not send a second request.
      fireEvent.click(screen.getByRole('button', { name: /accepting/i }));
      expect(api.accept).toHaveBeenCalledTimes(1);

      confirm({ data: { record_id: 'R1', status: 'accepted' } });
      await screen.findByText('Accepted record R1');
      expect(screen.getByText(/nothing is awaiting review/i)).toBeDefined();
    });

    it('keeps the record in the queue and shows the server reason when accept fails', async () => {
      api.accept.mockRejectedValue({ response: { status: 409, data: { detail: "Record 'R1' is in status 'rejected', cannot accept" } } });
      renderPage();
      await screen.findByText('LLM said so');

      fireEvent.click(screen.getByRole('button', { name: /^accept$/i }));

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent("cannot accept");
      expect(screen.getByText('INCOMING RECORD')).toBeDefined();
      expect(screen.queryByText(/Accepted record/)).toBeNull();
      expect(screen.getByRole('button', { name: /^accept$/i })).not.toBeDisabled();
    });

    it('requires a note to reject and sends nothing without one', async () => {
      renderPage();
      await screen.findByText('LLM said so');

      fireEvent.click(screen.getByRole('button', { name: /^reject$/i }));
      expect(await screen.findByRole('alert')).toHaveTextContent('A note is required to reject a record.');
      expect(api.reject).not.toHaveBeenCalled();
    });

    it('rejects with the note once the server confirms', async () => {
      api.reject.mockResolvedValue({ data: { record_id: 'R1', status: 'rejected' } });
      renderPage();
      await screen.findByText('LLM said so');

      fireEvent.change(screen.getByPlaceholderText(/review note/i), { target: { value: 'Superseded by field report' } });
      fireEvent.click(screen.getByRole('button', { name: /^reject$/i }));

      await screen.findByText('Rejected record R1');
      expect(api.reject).toHaveBeenCalledWith('R1', 'Superseded by field report');
    });

    it('a stray key press cannot accept or reject a record', async () => {
      renderPage();
      await screen.findByText('LLM said so');

      fireEvent.keyDown(window, { key: 'a' });
      fireEvent.keyDown(window, { key: 'A' });
      fireEvent.keyDown(window, { key: 'r' });
      fireEvent.keyDown(window, { key: 'R' });

      expect(api.accept).not.toHaveBeenCalled();
      expect(api.reject).not.toHaveBeenCalled();
    });

    it('says plainly that neither action deletes the record', async () => {
      renderPage();
      await screen.findByText('LLM said so');
      expect(screen.getByText(/neither action deletes the record/i)).toBeDefined();
    });
  });
});
