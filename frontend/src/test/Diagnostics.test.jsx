import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Diagnostics from '../pages/Diagnostics';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    assets: vi.fn(),
    diagnose: vi.fn()
  }
}));

const mockAssets = [
  { id: '1', tail_number: '813SK', record_count: 50 },
  { id: '2', tail_number: '508AE', record_count: 20 }
];

const mockResult = {
  ranked_checks: [
    { part_name: 'DRAG ANGLE', evidence_count: 4, sources: ['asset_history'], rank: 1 }
  ],
  explanation: 'DRAG ANGLE is top-ranked...',
  evidence: [
    { record_id: 'DEMO1', asset_id: '813SK', occurred_at: '2025-12-28', part_name: 'DRAG ANGLE', is_superseded: false },
    { record_id: 'DEMO2', asset_id: '813SK', occurred_at: '2025-12-01', part_name: 'DRAG ANGLE', is_superseded: true }
  ],
  rare_cases: [
    { record_id: 'RARE1', asset_id: 'AALA', occurred_at: '2024-01-01', part_name: 'DRAG ANGLE', resolution_text: 'Fixed.' }
  ],
  context_size: { asset_records: 30, fleet_records: 20, fleet_assets: 18 }
};

const renderPage = () =>
  render(
    <MemoryRouter>
      <Diagnostics />
    </MemoryRouter>
  );

// Pick the first asset, type a symptom and press "Run diagnostic".
async function runDiagnostic(symptom = 'crack at drag angle') {
  fireEvent.click(screen.getByRole('button', { name: /select aircraft/i }));
  await waitFor(() => screen.getByText('813SK'));
  fireEvent.click(screen.getByText('813SK'));
  fireEvent.change(screen.getByRole('textbox'), { target: { value: symptom } });
  fireEvent.click(screen.getByRole('button', { name: /run diagnostic/i }));
}

const httpError = (status, detail) => ({
  response: { status, data: detail === undefined ? {} : { detail } },
  message: `Request failed with status code ${status}`,
});

describe('Diagnostics', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    client.maintenanceAPI.assets.mockResolvedValue({ data: mockAssets });
  });

  it('renders ranked list, evidence links, and handles rare-case expansion', async () => {
    client.maintenanceAPI.diagnose.mockResolvedValue({ data: mockResult });

    renderPage();

    // Select asset
    fireEvent.click(screen.getByRole('button', { name: /select aircraft/i }));
    await waitFor(() => screen.getByText('813SK'));
    fireEvent.click(screen.getByText('813SK'));

    // Input symptom
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'crack at drag angle' } });

    // Submit
    fireEvent.click(screen.getByRole('button', { name: /run diagnostic/i }));

    // Wait for ranked list
    await waitFor(() => screen.getByText('Ranked Inspection Order'));
    expect(screen.getByText('DRAG ANGLE')).toBeDefined();
    expect(screen.getByText(/seen in 4 prior cases/)).toBeDefined();

    // Check evidence citation links
    expect(screen.getByText('DEMO1')).toBeDefined();
    expect(screen.getByText('DEMO2')).toBeDefined();
    expect(screen.getByText('superseded')).toBeDefined();

    // Check context line
    expect(screen.getByText(/Answered from/)).toBeDefined();
    expect(screen.getByText('30')).toBeDefined(); // asset_records
    expect(screen.getAllByText('20')[0]).toBeDefined(); // fleet_records
    expect(screen.getByText('18')).toBeDefined(); // fleet_assets

    // Check rare cases expansion
    const expandBtn = screen.getByText(/1 occurrence in the corpus/);
    expect(expandBtn).toBeDefined();

    // Rare case should not be visible before click
    expect(screen.queryByText('RARE1')).toBeNull();

    // Click expand
    fireEvent.click(expandBtn);
    expect(screen.getByText('RARE1')).toBeDefined();
  });

  it('renders error state on API failure', async () => {
    client.maintenanceAPI.diagnose.mockRejectedValue({ response: { data: { detail: 'Something went wrong' } } });

    renderPage();

    fireEvent.click(screen.getByRole('button', { name: /select aircraft/i }));
    await waitFor(() => screen.getByText('813SK'));
    fireEvent.click(screen.getByText('813SK'));

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'bad symptom' } });
    fireEvent.click(screen.getByRole('button', { name: /run diagnostic/i }));

    await waitFor(() => screen.getByText('Something went wrong'));
  });

  describe('loading and submission', () => {
    it('shows a progress state and blocks duplicate submissions', async () => {
      let resolve;
      client.maintenanceAPI.diagnose.mockReturnValue(new Promise((r) => { resolve = r; }));

      renderPage();
      await runDiagnostic();

      await waitFor(() => screen.getByText(/Querying graph and fleet records/));
      const button = screen.getByRole('button', { name: /analysing/i });
      expect(button).toBeDisabled();

      fireEvent.click(button);
      fireEvent.submit(button.closest('form'));
      expect(client.maintenanceAPI.diagnose).toHaveBeenCalledTimes(1);
      expect(client.maintenanceAPI.diagnose).toHaveBeenCalledWith('1', 'crack at drag angle');

      resolve({ data: mockResult });
      await waitFor(() => screen.getByText('Ranked Inspection Order'));
      expect(screen.queryByText(/Querying graph and fleet records/)).toBeNull();
    });

    it('keeps Run disabled until an aircraft and a symptom are present', async () => {
      renderPage();
      const run = screen.getByRole('button', { name: /run diagnostic/i });
      expect(run).toBeDisabled();

      fireEvent.change(screen.getByRole('textbox'), { target: { value: 'some symptom' } });
      expect(run).toBeDisabled();
      expect(screen.getByText(/select an aircraft to run the diagnostic/i)).toBeDefined();
    });

    it('names the asset and symptom the result belongs to', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({ data: mockResult });
      renderPage();
      await runDiagnostic('crack at drag angle');
      await waitFor(() => screen.getByText(/Diagnosis for/));
      expect(screen.getByText(/crack at drag angle/, { selector: 'p' })).toBeDefined();
    });

    it('clears the symptom and result with the Clear button', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({ data: mockResult });
      renderPage();
      await runDiagnostic();
      await waitFor(() => screen.getByText('Ranked Inspection Order'));

      fireEvent.click(screen.getByRole('button', { name: /^clear$/i }));

      expect(screen.queryByText('Ranked Inspection Order')).toBeNull();
      expect(screen.getByRole('textbox')).toHaveValue('');
      expect(screen.getByText('No diagnostic yet')).toBeDefined();
    });
  });

  describe('failure states (no invented diagnosis)', () => {
    it('503: model unavailable, with technical detail and a retry that re-sends the same request', async () => {
      client.maintenanceAPI.diagnose.mockRejectedValue(
        httpError(503, 'Groq LLM is not configured (is_live=False).')
      );

      renderPage();
      await runDiagnostic();

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent('Diagnostic model unavailable');
      expect(alert).toHaveTextContent(/no diagnosis is shown/i);
      expect(alert).toHaveTextContent('Groq LLM is not configured');
      expect(screen.queryByText('Ranked Inspection Order')).toBeNull();
      expect(screen.queryByText('Analysis')).toBeNull();

      client.maintenanceAPI.diagnose.mockResolvedValue({ data: mockResult });
      fireEvent.click(screen.getByRole('button', { name: /try again/i }));
      await waitFor(() => screen.getByText('Ranked Inspection Order'));
      expect(client.maintenanceAPI.diagnose).toHaveBeenCalledTimes(2);
      expect(client.maintenanceAPI.diagnose).toHaveBeenLastCalledWith('1', 'crack at drag angle');
    });

    it('404: aircraft has no history; offers no retry', async () => {
      client.maintenanceAPI.diagnose.mockRejectedValue(httpError(404, 'No history found for asset_id=1.'));

      renderPage();
      await runDiagnostic();

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent('No service history for this aircraft');
      expect(screen.queryByRole('button', { name: /try again/i })).toBeNull();
    });

    it('429: rate limited, retryable', async () => {
      client.maintenanceAPI.diagnose.mockRejectedValue(httpError(429, 'rate limit'));

      renderPage();
      await runDiagnostic();

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent('Model rate limit reached');
      expect(screen.getByRole('button', { name: /try again/i })).toBeDefined();
    });

    it('500: reports a server error with the status, retryable', async () => {
      client.maintenanceAPI.diagnose.mockRejectedValue(httpError(500));

      renderPage();
      await runDiagnostic();

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent('The diagnostic service hit an error');
      expect(alert).toHaveTextContent('HTTP 500');
      expect(screen.getByRole('button', { name: /try again/i })).toBeDefined();
    });

    it('422: flattens FastAPI validation detail (an array) instead of crashing', async () => {
      client.maintenanceAPI.diagnose.mockRejectedValue(
        httpError(422, [{ type: 'missing', loc: ['body', 'symptom_text'], msg: 'Field required' }])
      );

      renderPage();
      await runDiagnostic();

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent('Check the request');
      expect(alert).toHaveTextContent('symptom_text: Field required');
    });

    it('network failure: says the API is unreachable', async () => {
      client.maintenanceAPI.diagnose.mockRejectedValue({ code: 'ERR_NETWORK', message: 'Network Error', request: {} });

      renderPage();
      await runDiagnostic();

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent('Cannot reach the Halite API');
      expect(screen.getByRole('button', { name: /try again/i })).toBeDefined();
    });
  });

  describe('response states', () => {
    it('200 with no evidence: says so, and still shows the model text, labelled as unsupported (never hidden)', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({
        data: {
          ranked_checks: [],
          evidence: [],
          rare_cases: [],
          explanation: 'A confident-sounding paragraph with nothing behind it.',
          context_size: { asset_records: 4, fleet_records: 0, fleet_assets: 0 },
          citation_validation: { valid_ids: [], invalid_ids: [], all_valid: true },
          warnings: [],
        },
      });

      renderPage();
      await runDiagnostic();

      await waitFor(() => screen.getByText('Insufficient evidence'));
      // No ranking exists to show, but nothing the backend returned is withheld.
      expect(screen.queryByText('Ranked Inspection Order')).toBeNull();
      expect(screen.getByText(/confident-sounding paragraph/)).toBeDefined();
      expect(screen.getByText(/not backed by retrieved evidence/i)).toBeDefined();
      expect(screen.queryByText(/verified against the graph/)).toBeNull();
    });

    it('renders the warnings field and the citation-validation status', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({
        data: {
          ...mockResult,
          warnings: ['Only one asset-specific record supports this check.'],
          citation_validation: { valid_ids: ['DEMO1', 'DEMO2'], invalid_ids: [], all_valid: true },
        },
      });

      renderPage();
      await runDiagnostic();

      await waitFor(() => screen.getByText('Warnings'));
      expect(screen.getByText('Only one asset-specific record supports this check.')).toBeDefined();
      expect(screen.getByText(/2 cited record IDs verified against the graph/)).toBeDefined();
    });

    it('flags unverified citations instead of reporting them as verified', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({
        data: {
          ...mockResult,
          explanation: 'See FAKE123 [UNVERIFIED].',
          citation_validation: { valid_ids: ['DEMO1'], invalid_ids: ['FAKE123'], all_valid: false },
        },
      });

      renderPage();
      await runDiagnostic();

      await waitFor(() => screen.getByText(/1 unverified ID\(s\) were flagged/));
      expect(screen.queryByText(/verified against the graph/)).toBeNull();
    });

    it('shows readable text when the backend returns the raw model JSON as the explanation', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({
        data: {
          ...mockResult,
          explanation: '{\n  "explanation": "DRAG ANGLE leads on 3 matching records.",\n  "rare_cases": ["X1"],\n  "warnings": ["Model-side caveat."]\n}',
        },
      });

      renderPage();
      await runDiagnostic();

      await waitFor(() => screen.getByText('DRAG ANGLE leads on 3 matching records.'));
      expect(screen.queryByText(/"rare_cases"/)).toBeNull();
      expect(screen.getByText('Model-side caveat.')).toBeDefined();
    });

    it('tolerates missing optional fields in the response', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({
        data: { ranked_checks: [{ part_name: 'FRAME', evidence_count: 1 }] },
      });

      renderPage();
      await runDiagnostic();

      await waitFor(() => screen.getByText('Ranked Inspection Order'));
      expect(screen.getByText('FRAME')).toBeDefined();
      expect(screen.getByText(/sources: n\/a/)).toBeDefined();
      expect(screen.getByText(/seen in 1 prior case$/)).toBeDefined();
    });

    it('always states that this is decision support', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({ data: mockResult });
      renderPage();
      await runDiagnostic();
      await waitFor(() => screen.getByText(/Decision support only/));
      expect(screen.getByText(/qualified personnel remain authoritative/)).toBeDefined();
    });
  });

  describe('contract with the backend (docs/mid1/12_u4_u5_diagnostics_handoff.md)', () => {
    const withChecks = (checks, extra = {}) => ({
      data: {
        ...mockResult,
        ranked_checks: checks,
        ...extra,
      },
    });

    it('lets a ranked check\'s evidence record ids open the history when the record is known', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue(
        withChecks([
          { part_name: 'DRAG ANGLE', evidence_count: 2, sources: ['asset_history'], evidence_record_ids: ['DEMO1', 'UNKNOWN9'] },
        ])
      );
      renderPage();
      await runDiagnostic();
      await waitFor(() => screen.getByText('Ranked Inspection Order'));

      const list = document.getElementById('ranked-checks-list');
      // DEMO1 is in `evidence` (known aircraft) -> a button; UNKNOWN9 is not -> plain text, never a guessed link.
      const buttons = [...list.querySelectorAll('button')].map(b => b.textContent);
      expect(buttons).toEqual(['DEMO1']);
      expect(list.textContent).toContain('UNKNOWN9');
    });

    it('caps long record lists per check and says how many more there are', async () => {
      const ids = Array.from({ length: 9 }, (_, i) => `ID${i}`);
      client.maintenanceAPI.diagnose.mockResolvedValue(
        withChecks([{ part_name: 'ANGLE', evidence_count: 9, sources: ['fleet_match'], evidence_record_ids: ids }])
      );
      renderPage();
      await runDiagnostic();
      await waitFor(() => screen.getByText('Ranked Inspection Order'));

      const text = document.getElementById('ranked-checks-list').textContent;
      expect(text).toContain('ID4');
      expect(text).not.toContain('ID5');
      expect(text).toContain('+4 more');
    });

    it('shows each check\'s rank score, labelled as a rank score and not a probability', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue(
        withChecks([
          { part_name: 'DRAG ANGLE', evidence_count: 3, sources: ['asset_history'], score: 1.4784, rank: 1 },
          { part_name: 'ANGLE', evidence_count: 17, sources: ['fleet_match'], score: 0.5888, rank: 2 },
        ])
      );
      renderPage();
      await runDiagnostic();
      await waitFor(() => screen.getByText('Ranked Inspection Order'));

      expect(screen.getByText('rank score 1.48')).toBeDefined();
      expect(screen.getByText('rank score 0.59')).toBeDefined();
      expect(screen.getByText('rank score 1.48')).toHaveAttribute('title', expect.stringMatching(/not a probability/i));
      expect(screen.queryByText(/probability of/i)).toBeNull();
    });

    it('omits the rank score when the backend does not send one (no invented number)', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue(
        withChecks([{ part_name: 'FRAME', evidence_count: 1, sources: ['asset_history'] }])
      );
      renderPage();
      await runDiagnostic();
      await waitFor(() => screen.getByText('Ranked Inspection Order'));
      expect(screen.queryByText(/rank score/)).toBeNull();
    });

    it('shows the server time from context_size.wall_clock_s', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({
        data: { ...mockResult, context_size: { asset_records: 30, fleet_records: 20, fleet_assets: 18, wall_clock_s: 2.79 } },
      });
      renderPage();
      await runDiagnostic();
      await waitFor(() => screen.getByText(/Server time 2\.8 s/));
    });

    it('lets the reader expand a check to see every record id, not just the first few', async () => {
      const ids = Array.from({ length: 9 }, (_, i) => `ID${i}`);
      client.maintenanceAPI.diagnose.mockResolvedValue(
        withChecks([{ part_name: 'ANGLE', evidence_count: 9, sources: ['fleet_match'], evidence_record_ids: ids }])
      );
      renderPage();
      await runDiagnostic();
      await waitFor(() => screen.getByText('Ranked Inspection Order'));

      expect(document.getElementById('ranked-checks-list').textContent).not.toContain('ID8');
      fireEvent.click(screen.getByRole('button', { name: '+4 more' }));
      expect(document.getElementById('ranked-checks-list').textContent).toContain('ID8');

      fireEvent.click(screen.getByRole('button', { name: 'show fewer' }));
      expect(document.getElementById('ranked-checks-list').textContent).not.toContain('ID8');
    });

    it('styles [UNVERIFIED:ID] markers as warnings', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({
        data: {
          ...mockResult,
          explanation: 'Seen in SWIA2025000000000 [UNVERIFIED:SWIA2025000000000] and DEMO1.',
          citation_validation: { valid_ids: ['DEMO1'], invalid_ids: ['SWIA2025000000000'], all_valid: false },
        },
      });
      renderPage();
      await runDiagnostic();
      await waitFor(() => screen.getByText('Analysis'));

      const marks = document.querySelectorAll('mark[data-unverified]');
      expect(marks).toHaveLength(1);
      expect(marks[0].textContent).toBe('[UNVERIFIED:SWIA2025000000000]');
    });

    it('does not call citations verified when all_valid is false, even with no invalid ids listed', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({
        data: {
          ...mockResult,
          citation_validation: { valid_ids: ['DEMO1'], invalid_ids: [], all_valid: false },
        },
      });
      renderPage();
      await runDiagnostic();
      await waitFor(() => screen.getByText('Analysis'));

      expect(screen.getByText(/citation check did not pass/i)).toBeDefined();
      expect(screen.queryByText(/verified against the graph/)).toBeNull();
    });

    it('says so when the model returns no explanation but a ranking exists (not a silent omission)', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({
        data: {
          ...mockResult,
          explanation: '',
          evidence: [],
          citation_validation: { valid_ids: [], invalid_ids: [], all_valid: true },
        },
      });
      renderPage();
      await runDiagnostic();

      await waitFor(() => screen.getByText('Ranked Inspection Order'));
      expect(screen.getByText('No written explanation returned')).toBeDefined();
      expect(screen.getByText(/computed from historical records alone/i)).toBeDefined();
      expect(screen.queryByText('Analysis')).toBeNull();
    });

    it('does not show the no-explanation notice when an explanation is present', async () => {
      client.maintenanceAPI.diagnose.mockResolvedValue({ data: mockResult });
      renderPage();
      await runDiagnostic();
      await waitFor(() => screen.getByText('Analysis'));
      expect(screen.queryByText('No written explanation returned')).toBeNull();
    });

    it('warns that a fresh diagnosis can be slow while it is loading', async () => {
      client.maintenanceAPI.diagnose.mockReturnValue(new Promise(() => {}));
      renderPage();
      await runDiagnostic();
      await screen.findByText(/can take up to a minute/i);
    });
  });
});
