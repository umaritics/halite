import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ServiceRecords from '../pages/ServiceRecords';
import ConfidenceBar from '../components/ConfidenceBar';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    assets: vi.fn(),
    assetHistory: vi.fn(),
  }
}));

const api = client.maintenanceAPI;

describe('ConfidenceBar', () => {
  it('renders above and below threshold properly', () => {
    const { container: container1 } = render(<ConfidenceBar confidence={0.8} threshold={0.5} />);
    // Bar opacity is 1 (doesn't have opacity-40)
    expect(container1.querySelector('.bg-accent')).not.toHaveClass('opacity-40');
    expect(screen.getByText('0.80')).toBeInTheDocument();

    const { container: container2 } = render(<ConfidenceBar confidence={0.3} threshold={0.5} />);
    expect(container2.querySelector('.bg-accent')).toHaveClass('opacity-40');
    expect(screen.getByText('0.30')).toBeInTheDocument();
  });
});

describe('ServiceRecords', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('filters and renders records', async () => {
    api.assets.mockResolvedValue({
      data: [{ id: '1', tail_number: 'N123' }]
    });
    api.assetHistory.mockResolvedValue({
      data: {
        asset_id: '1',
        records: [
          { record_id: 'R1', occurred_at: '2025-01-01T00:00:00Z', status: 'accepted', part_name: 'Engine', text: 'broken' },
          { record_id: 'R2', occurred_at: '2025-01-02T00:00:00Z', status: 'needs_review', part_name: 'Wing', text: 'cracked' }
        ]
      }
    });

    render(
      <MemoryRouter>
        <ServiceRecords />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Engine')).toBeInTheDocument();
      expect(screen.getByText('Wing')).toBeInTheDocument();
    });

    // Filtering test could be simulated with userEvent, but standard query logic is covered
  });
});

// Mid-I performance acceptance (docs/mid1/10_perf_assets_api_handoff.md):
// Service Records initial load must use at most 2 API calls, not one per aircraft.
describe('ServiceRecords request volume', () => {
  const fleet = Array.from({ length: 118 }, (_, i) => ({
    id: `uuid-${i}`,
    tail_number: `T${String(i).padStart(3, '0')}`,
    record_count: i === 7 ? 153 : 5,
  }));

  const history = (assetId, tail, records) => ({
    data: {
      asset_id: assetId,
      count: records.length,
      records: records.map((r, i) => ({
        id: `${assetId}-${i}`,
        asset_key: tail,
        occurred_at: '2025-01-01T00:00:00Z',
        status: 'auto_accepted',
        ...r,
      })),
    },
  });

  beforeEach(() => {
    vi.resetAllMocks();
    api.assets.mockResolvedValue({ data: fleet });
    api.assetHistory.mockImplementation((id) =>
      Promise.resolve(history(id, fleet.find(a => a.id === id).tail_number, [
        { record_id: `REC-${id}`, part_name: `PART OF ${id}` },
      ]))
    );
  });

  const renderAt = (url = '/app/records') =>
    render(
      <MemoryRouter initialEntries={[url]}>
        <ServiceRecords />
      </MemoryRouter>
    );

  it('first load makes exactly 2 API calls for a 118-aircraft fleet', async () => {
    renderAt();
    await screen.findByText('PART OF uuid-7');

    expect(api.assets).toHaveBeenCalledTimes(1);
    expect(api.assetHistory).toHaveBeenCalledTimes(1);
    // Defaults to the aircraft with the most records, and fetches nobody else's history.
    expect(api.assetHistory).toHaveBeenCalledWith('uuid-7');
  });

  it('switching aircraft loads only that aircraft', async () => {
    renderAt();
    await screen.findByText('PART OF uuid-7');

    fireEvent.change(screen.getByLabelText('Aircraft'), { target: { value: 'uuid-3' } });

    await screen.findByText('PART OF uuid-3');
    expect(screen.queryByText('PART OF uuid-7')).toBeNull();
    expect(api.assetHistory).toHaveBeenCalledTimes(2);
    expect(api.assetHistory).toHaveBeenLastCalledWith('uuid-3');
  });

  it('honours ?asset=<uuid> from the link', async () => {
    renderAt('/app/records?asset=uuid-11');
    await screen.findByText('PART OF uuid-11');
    expect(api.assetHistory).toHaveBeenCalledTimes(1);
    expect(api.assetHistory).toHaveBeenCalledWith('uuid-11');
  });

  it('says so and falls back when the linked aircraft does not exist', async () => {
    renderAt('/app/records?asset=nope');
    await screen.findByText('PART OF uuid-7');
    expect(screen.getByRole('status')).toHaveTextContent(/not found/i);
    expect(api.assetHistory).toHaveBeenCalledTimes(1);
  });

  it('shows the records of the latest selection even if an earlier request finishes last', async () => {
    let releaseSlow;
    api.assetHistory.mockImplementation((id) => {
      if (id === 'uuid-7') {
        return new Promise((resolve) => {
          releaseSlow = () => resolve(history('uuid-7', 'T007', [{ record_id: 'SLOW', part_name: 'STALE PART' }]));
        });
      }
      return Promise.resolve(history(id, 'x', [{ record_id: `REC-${id}`, part_name: `PART OF ${id}` }]));
    });

    renderAt();
    await waitFor(() => expect(api.assetHistory).toHaveBeenCalledWith('uuid-7'));
    fireEvent.change(screen.getByLabelText('Aircraft'), { target: { value: 'uuid-3' } });
    await screen.findByText('PART OF uuid-3');

    releaseSlow();
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByText('STALE PART')).toBeNull();
    expect(screen.getByText('PART OF uuid-3')).toBeDefined();
  });

  it('links each record to its asset history by asset UUID', async () => {
    renderAt();
    await screen.findByText('PART OF uuid-7');
    const link = screen.getByRole('link', { name: /REC-uuid-7/ });
    expect(link.getAttribute('href')).toBe('/app/asset-history/uuid-7#REC-uuid-7');
  });

  it('is honest that records are per aircraft and fleet-wide search is not available', async () => {
    renderAt();
    await screen.findByText('PART OF uuid-7');
    expect(screen.getByText(/maintenance records for one aircraft at a time/i)).toBeDefined();
    expect(screen.getByText(/searching across the whole fleet is not available yet/i)).toBeDefined();
  });
});

describe('ServiceRecords states', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  const renderPage = () =>
    render(
      <MemoryRouter>
        <ServiceRecords />
      </MemoryRouter>
    );

  it('an aircraft-list failure is shown as a failure, never as "no records", and retry recovers', async () => {
    api.assets.mockRejectedValueOnce({ code: 'ERR_NETWORK', message: 'Network Error', request: {} });
    renderPage();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Could not load the aircraft list');
    expect(screen.queryByText(/no records/i)).toBeNull();

    api.assets.mockResolvedValue({ data: [{ id: 'a', tail_number: 'N1', record_count: 1 }] });
    api.assetHistory.mockResolvedValue({ data: { asset_id: 'a', records: [{ record_id: 'R1', occurred_at: '2025-01-01T00:00:00Z', status: 'accepted', part_name: 'ENGINE' }] } });
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));
    await screen.findByText('ENGINE');
  });

  it('a history failure is shown as a failure for that aircraft, and retry recovers', async () => {
    api.assets.mockResolvedValue({ data: [{ id: 'a', tail_number: 'N1', record_count: 1 }] });
    api.assetHistory.mockRejectedValueOnce({ response: { status: 500, data: {} } });
    renderPage();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Could not load records for this aircraft');
    expect(screen.queryByText('No records for this aircraft.')).toBeNull();

    api.assetHistory.mockResolvedValue({ data: { asset_id: 'a', records: [{ record_id: 'R1', occurred_at: '2025-01-01T00:00:00Z', status: 'accepted', part_name: 'ENGINE' }] } });
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));
    await screen.findByText('ENGINE');
  });

  it('says plainly when an aircraft genuinely has no records', async () => {
    api.assets.mockResolvedValue({ data: [{ id: 'a', tail_number: 'N1', record_count: 0 }] });
    api.assetHistory.mockResolvedValue({ data: { asset_id: 'a', records: [] } });
    renderPage();
    await screen.findByText('No records for this aircraft.');
  });

  it('says so when the corpus has no aircraft at all', async () => {
    api.assets.mockResolvedValue({ data: [] });
    renderPage();
    await screen.findByText('No aircraft in the loaded corpus.');
    expect(api.assetHistory).not.toHaveBeenCalled();
  });

  it('shows a missing date plainly and lists undated records last', async () => {
    api.assets.mockResolvedValue({ data: [{ id: 'a', tail_number: 'N1', record_count: 2 }] });
    api.assetHistory.mockResolvedValue({
      data: {
        asset_id: 'a',
        records: [
          { record_id: 'NODATE', status: 'accepted', part_name: 'UNDATED PART' },
          { record_id: 'DATED', occurred_at: '2025-01-01T00:00:00Z', status: 'accepted', part_name: 'DATED PART' },
        ],
      },
    });
    renderPage();

    await screen.findByText('DATED PART');
    expect(screen.getByText('Date not recorded')).toBeDefined();
    expect(screen.queryByText(/invalid date/i)).toBeNull();
    const order = screen.getAllByRole('link').map(a => a.textContent);
    expect(order.findIndex(t => t.includes('DATED PART'))).toBeLessThan(order.findIndex(t => t.includes('UNDATED PART')));
  });

  it('filters by status and by search text within the selected aircraft', async () => {
    api.assets.mockResolvedValue({ data: [{ id: 'a', tail_number: 'N1', record_count: 2 }] });
    api.assetHistory.mockResolvedValue({
      data: {
        asset_id: 'a',
        records: [
          { record_id: 'R1', occurred_at: '2025-01-01T00:00:00Z', status: 'accepted', part_name: 'ENGINE', text: 'broken' },
          { record_id: 'R2', occurred_at: '2025-01-02T00:00:00Z', status: 'needs_review', part_name: 'WING', text: 'cracked' },
        ],
      },
    });
    renderPage();
    await screen.findByText('ENGINE');

    fireEvent.click(screen.getByRole('button', { name: 'Needs Review' }));
    expect(screen.queryByText('ENGINE')).toBeNull();
    expect(screen.getByText('WING')).toBeDefined();

    fireEvent.click(screen.getByRole('button', { name: 'All' }));
    fireEvent.change(screen.getByPlaceholderText(/search discrepancy/i), { target: { value: 'broken' } });
    expect(screen.getByText('ENGINE')).toBeDefined();
    expect(screen.queryByText('WING')).toBeNull();
  });
});

describe('ServiceRecords shows the JASC code the backend returns', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('shows JASC next to the part when present and nothing when absent', async () => {
    api.assets.mockResolvedValue({ data: [{ id: 'a', tail_number: 'N1', record_count: 2 }] });
    api.assetHistory.mockResolvedValue({
      data: {
        asset_id: 'a',
        records: [
          { record_id: 'R1', occurred_at: '2025-01-02T00:00:00Z', status: 'accepted', part_name: 'ENGINE', jasc_code: '7200' },
          { record_id: 'R2', occurred_at: '2025-01-01T00:00:00Z', status: 'accepted', part_name: 'WING' },
        ],
      },
    });
    render(
      <MemoryRouter>
        <ServiceRecords />
      </MemoryRouter>
    );

    await screen.findByText('JASC 7200');
    expect(screen.getAllByText(/JASC/)).toHaveLength(1);
  });
});
