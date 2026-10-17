import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MaintenanceIngest from '../pages/MaintenanceIngest';
import { MAX_UPLOAD_MB } from '../components/CsvUploader';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    ingest: vi.fn(),
    ingestFile: vi.fn(),
    submitRecord: vi.fn(),
  },
}));

const api = client.maintenanceAPI;
const counts = {
  assets_created: 10,
  records_created: 20,
  rows_skipped_no_tail: 0,
  rows_skipped_bad_date: 1,
  duplicates_skipped: 2,
};
const csv = (name = 'sdr.csv', type = 'text/csv') => new File(['RegistryNNumber,DifficultyDate\n1,01/10/2025'], name, { type });
const renderPage = () => render(<MemoryRouter><MaintenanceIngest /></MemoryRouter>);
const choose = async (file) => {
  fireEvent.change(screen.getByLabelText('CSV file'), { target: { files: [file] } });
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.spyOn(window, 'alert').mockImplementation(() => {});
});
afterEach(() => vi.restoreAllMocks());

describe('Corpus ingest (server file)', () => {
  it('renders corpus ingest and processes result', async () => {
    api.ingest.mockResolvedValue({ data: counts });
    renderPage();
    act(() => {
      screen.getByText('Ingest Corpus').click();
    });
    await waitFor(() => {
      expect(screen.getByText('10')).toBeInTheDocument(); // aircraft in file
      expect(screen.getByText('20')).toBeInTheDocument(); // records
    });
  });

  it('sends the path and limit it was given', async () => {
    api.ingest.mockResolvedValue({ data: counts });
    renderPage();
    fireEvent.change(screen.getByLabelText('CSV Path'), { target: { value: 'data/x.csv' } });
    fireEvent.change(screen.getByLabelText('Row Limit (Optional)'), { target: { value: '5' } });
    fireEvent.click(screen.getByText('Ingest Corpus'));
    await screen.findByText('New records');
    expect(api.ingest).toHaveBeenCalledWith({ csv_path: 'data/x.csv', limit: 5 });
  });

  it('shows a failure inline and never as a browser alert', async () => {
    api.ingest.mockRejectedValue({ response: { status: 404, data: { detail: 'CSV file not found: data/x.csv.' } } });
    renderPage();
    fireEvent.click(screen.getByText('Ingest Corpus'));
    expect(await screen.findByRole('alert')).toHaveTextContent('CSV file not found: data/x.csv.');
    expect(window.alert).not.toHaveBeenCalled();
  });
});

describe('CSV upload', () => {
  it('selecting a file writes nothing until the user confirms', async () => {
    renderPage();
    await choose(csv());
    expect(await screen.findByText('sdr.csv')).toBeInTheDocument();
    expect(api.ingestFile).not.toHaveBeenCalled();
  });

  it('posts the file as multipart form data under the field name "file"', async () => {
    api.ingestFile.mockResolvedValue({ data: counts });
    renderPage();
    const file = csv();
    await choose(file);
    fireEvent.click(await screen.findByRole('button', { name: 'Ingest this file' }));
    await screen.findByText(/Ingested/);
    expect(api.ingestFile).toHaveBeenCalledTimes(1);
    const body = api.ingestFile.mock.calls[0][0];
    expect(body).toBeInstanceOf(FormData);
    expect(body.get('file').name).toBe('sdr.csv');
  });

  it('shows the backend counts with honest labels and a link to the new records', async () => {
    api.ingestFile.mockResolvedValue({ data: counts });
    renderPage();
    await choose(csv());
    fireEvent.click(await screen.findByRole('button', { name: 'Ingest this file' }));
    const result = await screen.findByText('Aircraft in file');
    expect(result.closest('#ingest-result')).toHaveTextContent('20');
    expect(screen.queryByText('Assets Created')).toBeNull();
    expect(screen.getByRole('link', { name: /View them in Service Records/ })).toHaveAttribute(
      'href',
      '/app/records?analysis_state=unscored'
    );
  });

  it('says so when no record was created', async () => {
    api.ingestFile.mockResolvedValue({ data: { ...counts, records_created: 0, duplicates_skipped: 0, rows_skipped_no_tail: 9 } });
    renderPage();
    await choose(csv());
    fireEvent.click(await screen.findByRole('button', { name: 'Ingest this file' }));
    expect(await screen.findByRole('status')).toHaveTextContent(/No records were created.*DifficultyDate \(MM\/DD\/YYYY\)/);
    expect(screen.queryByRole('link', { name: /Service Records/ })).toBeNull();
  });

  it('says so when everything was already in the graph', async () => {
    api.ingestFile.mockResolvedValue({ data: { ...counts, records_created: 0, duplicates_skipped: 7 } });
    renderPage();
    await choose(csv());
    fireEvent.click(await screen.findByRole('button', { name: 'Ingest this file' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Nothing new: all 7 valid rows were already in the graph.');
  });

  it('rejects a non-CSV file before sending anything', async () => {
    renderPage();
    await choose(new File(['x'], 'notes.pdf', { type: 'application/pdf' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Only .csv files can be ingested.');
    expect(screen.queryByRole('button', { name: 'Ingest this file' })).toBeNull();
    expect(api.ingestFile).not.toHaveBeenCalled();
  });

  it('rejects a file over the size limit before sending anything', async () => {
    renderPage();
    const big = csv('big.csv');
    Object.defineProperty(big, 'size', { value: (MAX_UPLOAD_MB + 1) * 1024 * 1024 });
    await choose(big);
    expect(await screen.findByRole('alert')).toHaveTextContent(`larger than ${MAX_UPLOAD_MB} MB`);
    expect(api.ingestFile).not.toHaveBeenCalled();
  });

  it('shows the backend reason when the server refuses the file', async () => {
    api.ingestFile.mockRejectedValue({ response: { status: 413, data: { detail: 'File exceeds 10MB' } } });
    renderPage();
    await choose(csv());
    fireEvent.click(await screen.findByRole('button', { name: 'Ingest this file' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('File exceeds 10MB');
    expect(screen.queryByText('Aircraft in file')).toBeNull();
  });

  it('reports a server failure honestly and keeps the file so it can be retried', async () => {
    api.ingestFile.mockRejectedValueOnce({ response: { status: 500, data: {} } }).mockResolvedValueOnce({ data: counts });
    renderPage();
    await choose(csv());
    fireEvent.click(await screen.findByRole('button', { name: 'Ingest this file' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/HTTP 500.*CSV with a header row/);
    fireEvent.click(screen.getByRole('button', { name: 'Ingest this file' }));
    expect(await screen.findByText('Aircraft in file')).toBeInTheDocument();
  });

  it('does not blame a stopped API when an upload fails without a readable reply', async () => {
    api.ingestFile.mockRejectedValue({ code: 'ERR_NETWORK', message: 'Network Error', request: {} });
    renderPage();
    await choose(csv());
    fireEvent.click(await screen.findByRole('button', { name: 'Ingest this file' }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/no readable reply/);
    expect(alert).toHaveTextContent(/could not read the file/);
    expect(alert.textContent).not.toMatch(/Check that the API server is running/);
  });

  it('lets the user drop the chosen file', async () => {
    renderPage();
    await choose(csv());
    fireEvent.click(await screen.findByRole('button', { name: 'Choose a different file' }));
    expect(screen.queryByText('sdr.csv')).toBeNull();
    expect(api.ingestFile).not.toHaveBeenCalled();
  });

  it('tells the user the date format the backend accepts', () => {
    renderPage();
    expect(screen.getByText(/DifficultyDate\s+\(MM\/DD\/YYYY\)/)).toBeInTheDocument();
  });

  it('warns that ingesting writes to the graph and is safe to repeat', () => {
    renderPage();
    expect(screen.getByText(/writes to the connected graph/)).toBeInTheDocument();
  });
});

describe('Single record submission', () => {
  it('shows a failure inline and never as a browser alert', async () => {
    api.submitRecord.mockRejectedValue({ response: { status: 503, data: { detail: 'Model unavailable' } } });
    renderPage();
    fireEvent.change(screen.getByLabelText('Tail Number'), { target: { value: '508AE' } });
    fireEvent.change(screen.getByLabelText('Date'), { target: { value: '2025-01-01' } });
    fireEvent.change(screen.getByLabelText('Part Name'), { target: { value: 'PUMP' } });
    fireEvent.change(screen.getByLabelText('Discrepancy Text'), { target: { value: 'leaking' } });
    fireEvent.click(screen.getByRole('button', { name: 'Submit Record' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Model unavailable');
    expect(window.alert).not.toHaveBeenCalled();
  });
});
