import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AssetHistory from '../pages/AssetHistory';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    assetHistory: vi.fn(),
  }
}));

const history = {
  count: 3,
  records: [
    { id: 'u1', record_id: 'R1', asset_key: '813SK', occurred_at: '2025-01-01T00:00:00Z', status: 'auto_accepted', part_name: 'ENGINE', text: 'first' },
    { id: 'u2', record_id: 'R2', asset_key: '813SK', occurred_at: '2025-02-01T00:00:00Z', status: 'auto_accepted', part_name: 'WING', text: 'second' },
    { id: 'u3', record_id: 'R3', asset_key: '813SK', occurred_at: '2025-03-01T00:00:00Z', status: 'auto_accepted', part_name: 'DRAG ANGLE', text: 'third' },
  ],
};

const renderAt = (url) =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/app/asset-history/:assetId" element={<AssetHistory />} />
      </Routes>
    </MemoryRouter>
  );

describe('AssetHistory deep links to a record', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
  });

  it('scrolls to the linked record and marks it', async () => {
    client.maintenanceAPI.assetHistory.mockResolvedValue({ data: history });
    renderAt('/app/asset-history/813SK#R2');

    await screen.findByText('WING');

    const card = document.getElementById('record-R2');
    expect(card).toHaveAttribute('data-linked', 'true');
    expect(screen.getAllByText('Linked record')).toHaveLength(1);
    expect(document.getElementById('record-R1')).not.toHaveAttribute('data-linked');
    expect(document.getElementById('record-R3')).not.toHaveAttribute('data-linked');

    await waitFor(() => expect(Element.prototype.scrollIntoView).toHaveBeenCalledTimes(1));
    expect(Element.prototype.scrollIntoView.mock.contexts[0].id).toBe('record-R2');
  });

  it('decodes a URL-encoded record id in the hash', async () => {
    client.maintenanceAPI.assetHistory.mockResolvedValue({
      data: { count: 1, records: [{ id: 'u', record_id: 'AB 12', asset_key: '813SK', occurred_at: '2025-01-01T00:00:00Z', status: 'accepted', part_name: 'PUMP' }] },
    });
    renderAt('/app/asset-history/813SK#AB%2012');

    await screen.findByText('PUMP');
    expect(document.getElementById('record-AB 12')).toHaveAttribute('data-linked', 'true');
  });

  it('says so when the linked record is not in this aircraft history', async () => {
    client.maintenanceAPI.assetHistory.mockResolvedValue({ data: history });
    renderAt('/app/asset-history/813SK#NOPE99');

    await screen.findByText('WING');
    expect(screen.getByRole('status')).toHaveTextContent('NOPE99');
    expect(screen.getByRole('status')).toHaveTextContent(/not part of this aircraft/i);
    expect(screen.queryByText('Linked record')).toBeNull();
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();
  });

  it('does nothing special without a hash', async () => {
    client.maintenanceAPI.assetHistory.mockResolvedValue({ data: history });
    renderAt('/app/asset-history/813SK');

    await screen.findByText('WING');
    expect(screen.queryByText('Linked record')).toBeNull();
    expect(screen.queryByRole('status')).toBeNull();
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();
  });
});

describe('AssetHistory honesty and failure states', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
  });

  it('does not invent a superseding record or rationale the backend did not provide', async () => {
    client.maintenanceAPI.assetHistory.mockResolvedValue({
      data: {
        count: 1,
        records: [{ id: 'u', record_id: 'R1', asset_key: '813SK', occurred_at: '2025-01-01T00:00:00Z', status: 'superseded', superseding_record: null, supersede_rationale: null, part_name: 'FRAME' }],
      },
    });
    renderAt('/app/asset-history/813SK');

    await screen.findByText('FRAME');
    expect(screen.queryByText(/Corrected by/i)).toBeNull();
    expect(screen.queryByText(/unknown/i)).toBeNull();
    expect(screen.queryByText(/invalidated/i)).toBeNull();
  });

  it('shows a missing date plainly and puts undated records last', async () => {
    client.maintenanceAPI.assetHistory.mockResolvedValue({
      data: {
        count: 2,
        records: [
          { id: 'a', record_id: 'NODATE', asset_key: '813SK', status: 'accepted', part_name: 'UNDATED PART' },
          { id: 'b', record_id: 'DATED', asset_key: '813SK', occurred_at: '2025-01-01T00:00:00Z', status: 'accepted', part_name: 'DATED PART' },
        ],
      },
    });
    renderAt('/app/asset-history/813SK');

    await screen.findByText('DATED PART');
    expect(screen.getByText('Date not recorded')).toBeDefined();
    expect(screen.queryByText(/invalid date/i)).toBeNull();

    const order = [...document.querySelectorAll('h4')].map(h => h.textContent.trim());
    expect(order[0]).toContain('DATED PART');
    expect(order[1]).toContain('UNDATED PART');
  });

  it('404: says the aircraft was not found (not "no records"), no retry', async () => {
    client.maintenanceAPI.assetHistory.mockRejectedValue({ response: { status: 404, data: { detail: "Asset 'X' not found" } } });
    renderAt('/app/asset-history/X');

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Aircraft not found');
    expect(screen.queryByText('No records for this asset yet.')).toBeNull();
    expect(screen.queryByRole('button', { name: /try again/i })).toBeNull();
  });

  it('network failure: reports it, and Try again recovers', async () => {
    client.maintenanceAPI.assetHistory.mockRejectedValueOnce({ code: 'ERR_NETWORK', message: 'Network Error', request: {} });
    renderAt('/app/asset-history/813SK');

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Could not load service history');
    expect(screen.queryByText('No records for this asset yet.')).toBeNull();

    client.maintenanceAPI.assetHistory.mockResolvedValue({ data: history });
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));

    await screen.findByText('WING');
    expect(client.maintenanceAPI.assetHistory).toHaveBeenCalledTimes(2);
  });

  it('still shows the empty state when the aircraft genuinely has no records', async () => {
    client.maintenanceAPI.assetHistory.mockResolvedValue({ data: { records: [] } });
    renderAt('/app/asset-history/813SK');
    await screen.findByText('No records for this asset yet.');
  });
});

describe('AssetHistory shows the conflict-engine and ingest fields the backend returns', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
  });

  it('shows confidence, JASC code and source on each record', async () => {
    client.maintenanceAPI.assetHistory.mockResolvedValue({
      data: {
        count: 1,
        records: [{
          id: 'u', record_id: 'R1', asset_key: '813SK', occurred_at: '2025-01-01T00:00:00Z', status: 'auto_accepted',
          part_name: 'FRAME', text: 'cracked', confidence: 0.62, jasc_code: '5240', source: 'FAA SDR',
        }],
      },
    });
    renderAt('/app/asset-history/813SK');

    await screen.findByText('FRAME');
    expect(screen.getByText('0.62')).toBeDefined();
    expect(screen.getByText('JASC 5240')).toBeDefined();
    expect(screen.getByText('Source: FAA SDR')).toBeDefined();
  });

  it('shows nothing extra for fields the backend did not send', async () => {
    client.maintenanceAPI.assetHistory.mockResolvedValue({
      data: {
        count: 1,
        records: [{ id: 'u', record_id: 'R1', asset_key: '813SK', occurred_at: '2025-01-01T00:00:00Z', status: 'accepted', part_name: 'PUMP' }],
      },
    });
    renderAt('/app/asset-history/813SK');

    await screen.findByText('PUMP');
    expect(screen.queryByText(/JASC/)).toBeNull();
    expect(screen.queryByText(/Source:/)).toBeNull();
    expect(screen.queryByText('Conf')).toBeNull();
  });

  it('never renders a numeric confidence for an unscored record', async () => {
    client.maintenanceAPI.assetHistory.mockResolvedValue({
      data: {
        count: 1,
        records: [{ id: 'u', record_id: 'R1', asset_key: '813SK', occurred_at: '2025-01-01T00:00:00Z', status: 'unscored', analysis_state: 'unscored', part_name: 'PUMP', confidence: null }],
      },
    });
    renderAt('/app/asset-history/813SK');
    await screen.findByText('PUMP');
    expect(screen.getAllByText('Not analysed').length).toBeGreaterThan(0);
    expect(screen.queryByText('1.00')).toBeNull();
  });
});
