import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import question from '../../../backend/investigation/experiments/results/question_selection_2024_v2/results.json';
import decision from '../../../backend/investigation/experiments/results/decision_selection_2024_v2/selection.json';
import manifest from '../../../backend/investigation/experiments/results/publication.json';
import ResearchPage from '../features/investigation/ResearchPage';
import { sessionsAPI } from '../features/investigation/api';
import { decisionSeries, questionSeries } from '../features/investigation/research';

const auth = vi.hoisted(() => ({ user: { id: 'owner', organization_id: 'org' } }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => auth }));
vi.mock('../features/investigation/api', () => ({ sessionsAPI: { experiments: vi.fn() } }));
// Component tests inspect exact chart inputs; the hosted browser verifies actual SVG.
vi.mock('../components/ui/ResearchChart', async importOriginal => {
  const original = await importOriginal();
  return { ...original, default: props => <figure aria-label={props.title}><p>{props.title}</p><output data-testid={props.title}>{JSON.stringify(props.series)}</output><p>{props.caption}</p></figure> };
});
const saved = { schema_version: 'investigation-results-v1', state: 'available', question_selection: question, decision_selection: decision, artifacts: manifest.artifacts, publication_sha256: 'test-manifest-hash' };
function mount() { return render(<MemoryRouter><ResearchPage /></MemoryRouter>); }
beforeEach(() => { vi.resetAllMocks(); auth.user = { id: 'owner', organization_id: 'org' }; });

describe('Published research page', () => {
  it('shows loading then all three policies, saved measurements and pending acceptance honestly', async () => {
    let resolve;
    sessionsAPI.experiments.mockReturnValue(new Promise(done => { resolve = done; }));
    mount();
    expect(screen.getByRole('status')).toHaveTextContent('Loading verified');
    await act(async () => resolve({ data: saved }));
    const chart = JSON.parse(screen.getByTestId('Top-1 accuracy after follow-up questions').textContent);
    expect(chart).toEqual(questionSeries(question.summaries.all_attributes.all, 'top1'));
    expect(chart).toHaveLength(3);
    expect(screen.getByText(/No operating point has been accepted/)).toBeInTheDocument();
    expect(screen.getByTestId('paired-difference')).toHaveTextContent('interval includes zero');
    expect(screen.getByText(/not a sentence hallucination/)).toBeInTheDocument();
    expect(screen.getByText(/2025 held-out set has not been evaluated/)).toBeInTheDocument();
    expect(screen.getByText(/Publication SHA-256/)).toHaveTextContent('test-manifest-hash');
  });
  it('changes attribute control, correction cohort and metric using committed values', async () => {
    sessionsAPI.experiments.mockResolvedValue({ data: saved }); mount();
    await screen.findByTestId('Top-1 accuracy after follow-up questions');
    fireEvent.change(screen.getByLabelText('Attribute control'), { target: { value: 'coded_fields_only' } });
    const key = Object.keys(question.summaries.coded_fields_only.by_part_change)[0];
    fireEvent.change(screen.getByLabelText('Correction cohort'), { target: { value: key } });
    fireEvent.change(screen.getByLabelText('Question metric'), { target: { value: 'entropy' } });
    expect(JSON.parse(screen.getByTestId('Belief entropy (bits) after follow-up questions').textContent)).toEqual(questionSeries(question.summaries.coded_fields_only.by_part_change[key], 'entropy'));
    fireEvent.change(screen.getByLabelText('Answered-case accuracy'), { target: { value: 'accuracy_top3' } });
    expect(JSON.parse(screen.getByTestId('Accuracy against coverage').textContent)).toEqual(decisionSeries(decision.selection, 'accuracy_top3'));
  });
  it('shows explicit empty and failure states, retries, and rejects malformed publication', async () => {
    sessionsAPI.experiments.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ data: { nonsense: true } }).mockResolvedValueOnce({ data: { schema_version: 'investigation-results-v1', state: 'empty' } });
    mount(); await screen.findByRole('alert');
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await waitFor(() => expect(sessionsAPI.experiments).toHaveBeenCalledTimes(2));
    await screen.findByRole('alert');
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('No experiments published yet')).toBeInTheDocument();
    expect(screen.queryByTestId('Accuracy against coverage')).not.toBeInTheDocument();
  });
  it('aborts and clears previous-account results across identity changes', async () => {
    let resolve;
    sessionsAPI.experiments.mockReturnValueOnce(new Promise(done => { resolve = done; })).mockResolvedValueOnce({ data: { schema_version: 'investigation-results-v1', state: 'empty' } });
    const view = mount(); const signal = sessionsAPI.experiments.mock.calls[0][0];
    auth.user = { id: 'different', organization_id: 'other-org' };
    view.rerender(<MemoryRouter><ResearchPage /></MemoryRouter>);
    expect(signal.aborted).toBe(true);
    await screen.findByText('No experiments published yet');
    await act(async () => resolve({ data: saved }));
    expect(screen.queryByTestId('Accuracy against coverage')).not.toBeInTheDocument();
  });
  it('does not request data for a signed-out user', () => {
    auth.user = null; mount(); expect(sessionsAPI.experiments).not.toHaveBeenCalled();
    expect(screen.getByText('Sign in to view research results.')).toBeInTheDocument();
  });
});
