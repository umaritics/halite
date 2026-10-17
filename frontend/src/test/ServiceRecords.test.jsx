import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ServiceRecords from '../pages/ServiceRecords';
import ConfidenceBar from '../components/ConfidenceBar';
import StatusChip from '../components/StatusChip';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  maintenanceAPI: { assets: vi.fn(), records: vi.fn() },
}));

const api = client.maintenanceAPI;
const assets = [
  { id: 'a1', tail_number: '105NN', record_count: 2 },
  { id: 'a2', tail_number: '813SK', record_count: 1 },
];
const records = [
  { record_id: 'R1', asset_id: 'a1', tail_number: '105NN', occurred_at: '2025-02-01', part_name: 'DRAG ANGLE', status: 'no_action', analysis_state: 'scored', confidence: 0, classification_label: 'no_conflict', candidate_count: 2 },
  { record_id: 'R2', asset_id: 'a2', tail_number: '813SK', occurred_at: '2025-01-01', part_name: 'PUMP', status: 'unscored', analysis_state: 'unscored', confidence: null },
];

const page = (items = records, overrides = {}) => ({ data: { items, total: items.length, next: null, ...overrides } });
const renderAt = (url = '/app/records') => render(<MemoryRouter initialEntries={[url]}><ServiceRecords /></MemoryRouter>);

describe('confidence and status states', () => {
  it('renders unscored without a numeric score', () => {
    render(<><ConfidenceBar analysisState="unscored" confidence={null} /><StatusChip analysisState="unscored" status="unscored" /></>);
    expect(screen.getAllByText('Not analysed')).toHaveLength(2);
    expect(screen.queryByText(/0\.00|1\.00/)).toBeNull();
  });

  it('renders a flagged legacy 1.00 placeholder as not analysed', () => {
    render(<><ConfidenceBar legacyPlaceholder confidence={1} /><StatusChip legacyPlaceholder status="auto_accepted" /></>);
    expect(screen.getAllByText('Not analysed')).toHaveLength(2);
    expect(screen.queryByText('1.00')).toBeNull();
    expect(screen.queryByText('Auto Accepted')).toBeNull();
  });

  it('renders no-conflict comparisons without a numeric score', () => {
    render(<ConfidenceBar analysisState="scored" confidence={0} classification="no_conflict" candidateCount={3} />);
    expect(screen.getByText('No conflict found (3 comparisons)')).toBeInTheDocument();
    expect(screen.queryByText('0.00')).toBeNull();
  });

  it('renders a relation as a heuristic score', () => {
    render(<ConfidenceBar analysisState="scored" confidence={0.8} classification="supersedes" candidateCount={1} />);
    expect(screen.getByText('supersedes')).toBeInTheDocument();
    expect(screen.getByText('Conflict-check score (heuristic, not a probability)')).toBeInTheDocument();
    expect(screen.getByText('0.80').closest('[title]')).toHaveAttribute('title', expect.stringContaining('not a probability'));
  });

  it('hides confidence for superseded records', () => {
    const { container } = render(<ConfidenceBar analysisState="scored" confidence={0.9} classification="supersedes" status="superseded" />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('ServiceRecords fleet view', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.assets.mockResolvedValue({ data: assets });
    api.records.mockResolvedValue(page());
  });

  it('defaults to All aircraft', async () => {
    renderAt();
    expect(await screen.findByRole('option', { name: 'All aircraft' })).toBeInTheDocument();
    expect(screen.getByLabelText('Aircraft')).toHaveValue('');
    expect(screen.getByText('All aircraft — fleet-wide records')).toBeInTheDocument();
  });

  it('makes exactly two page-initiated calls on first load', async () => {
    renderAt();
    await screen.findByText('DRAG ANGLE');
    expect(api.assets).toHaveBeenCalledTimes(1);
    expect(api.records).toHaveBeenCalledTimes(1);
  });

  it('renders tail number on every row and the fleet total', async () => {
    renderAt();
    await screen.findByText('Showing 2 of 2 records');
    expect(screen.getAllByText('105NN')).toHaveLength(2);
    expect(screen.getAllByText('813SK')).toHaveLength(2);
  });

  it('keeps record deep links on the asset UUID and record ID', async () => {
    renderAt();
    expect((await screen.findByText('R1')).closest('a')).toHaveAttribute('href', '/app/asset-history/a1#R1');
  });

  it('preselects an asset from a shareable URL', async () => {
    renderAt('/app/records?asset=a1');
    await waitFor(() => expect(api.records).toHaveBeenCalledWith(expect.objectContaining({ asset_id: 'a1' })));
    expect(screen.getByLabelText('Aircraft')).toHaveValue('a1');
  });

  it('highlights a linked record from a shareable URL', async () => {
    renderAt('/app/records?asset=a1&record=R1');
    const row = (await screen.findByText('R1')).closest('[id="record-R1"]');
    expect(row).toHaveClass('ring-accent');
  });

  it('sends aircraft filter changes to the fleet endpoint', async () => {
    renderAt();
    await screen.findByText('R1');
    fireEvent.change(screen.getByLabelText('Aircraft'), { target: { value: 'a2' } });
    await waitFor(() => expect(api.records).toHaveBeenLastCalledWith(expect.objectContaining({ asset_id: 'a2' })));
  });

  it.each([
    ['Search records', 'q', 'crack'],
    ['Status', 'status', 'needs_review'],
    ['Analysis state', 'analysis_state', 'reviewed'],
    ['Component', 'part', 'PUMP'],
    ['Date from', 'date_from', '2025-01-01'],
    ['Date to', 'date_to', '2025-12-31'],
  ])('sends the %s filter through URL-backed params', async (label, key, value) => {
    renderAt();
    await screen.findByText('R1');
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
    await waitFor(() => expect(api.records).toHaveBeenLastCalledWith(expect.objectContaining({ [key]: value })));
  });

  it('loads the next page and appends records', async () => {
    api.records
      .mockResolvedValueOnce(page([records[0]], { total: 2, next: 1 }))
      .mockResolvedValueOnce(page([records[1]], { total: 2, next: null }));
    renderAt();
    fireEvent.click(await screen.findByRole('button', { name: 'Load more' }));
    expect(await screen.findByText('PUMP')).toBeInTheDocument();
    expect(api.records).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 1, limit: 50 }));
  });

  it('shows a corrected-by banner with a link', async () => {
    api.records.mockResolvedValue(page([{
      ...records[0], status: 'superseded', part_name: 'PUMP',
      corrected_by: { record_id: 'R9', part_name: 'PRESSURE SWITCH' },
    }]));
    renderAt();
    expect(await screen.findByText(/component changed PUMP → PRESSURE SWITCH/)).toBeInTheDocument();
    expect(screen.getByText('R9')).toHaveAttribute('href', '/app/asset-history/a1#R9');
  });

  it('reports a records failure and can retry', async () => {
    api.records.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(page());
    renderAt();
    expect(await screen.findByText('Could not load service records')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('DRAG ANGLE')).toBeInTheDocument();
  });
});
