import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import QuickDiagnose from '../features/investigation/QuickDiagnose';
import { sessionsAPI } from '../features/investigation/api';
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: { id: 'owner', organization_id: 'org' } }) }));
vi.mock('../features/investigation/api', () => ({ sessionsAPI: { assets: vi.fn(), diagnose: vi.fn() } }));
beforeEach(() => {
  vi.resetAllMocks();
  sessionsAPI.assets.mockResolvedValue({ data: [{ id: 'asset', tail_number: 'N123', record_count: 1 }] });
});
describe('Model-off quick diagnosis', () => {
  it('shows the deterministic explanation, ranking and evidence when the model is unavailable', async () => {
    sessionsAPI.diagnose.mockResolvedValue({ data: {
      ranked_checks: [{ rank: 1, part_name: 'PUMP', score: .4, evidence_count: 1, sources: ['asset_history'], evidence_record_ids: ['REC123456'] }],
      evidence: [{ record_id: 'REC123456', part_name: 'PUMP', asset_id: 'N123' }], rare_cases: [],
      explanation: null, fallback_explanation: 'Saved history points to a pump check.', llm_status: 'unavailable',
      citation_validation: { valid_ids: [], invalid_ids: [], all_valid: true }, warnings: ['Model unavailable'], context_size: {},
    } });
    render(<MemoryRouter><QuickDiagnose /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: /Select aircraft/i }));
    fireEvent.click(await screen.findByRole('button', { name: /N123/i }));
    fireEvent.change(screen.getByRole('textbox', { name: /symptom/i }), { target: { value: 'pump leak' } });
    fireEvent.click(screen.getByRole('button', { name: 'Run diagnostic', exact: true }));
    expect(await screen.findByText('Saved history points to a pump check.')).toBeInTheDocument();
    expect(screen.getByText(/ranking and evidence remain available with a deterministic explanation/i)).toBeInTheDocument();
    expect(sessionsAPI.diagnose).toHaveBeenCalledWith('asset', 'pump leak');
    expect(screen.getAllByText('PUMP').length).toBeGreaterThan(0);
  });
  it('shows aircraft-loading errors and never fabricates an aircraft option', async () => {
    sessionsAPI.assets.mockRejectedValue(new Error('offline'));
    render(<MemoryRouter><QuickDiagnose /></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent('Aircraft options could not be loaded');
    expect(sessionsAPI.diagnose).not.toHaveBeenCalled();
  });
});
