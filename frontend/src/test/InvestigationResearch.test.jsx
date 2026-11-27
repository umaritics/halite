import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import question from '../../../backend/investigation/experiments/results/question_selection_2024_v2/results.json';
import decision from '../../../backend/investigation/experiments/results/decision_selection_2024_v2/selection.json';
import held from '../../../backend/investigation/experiments/results/held_out_2025_v1/results.json';
import verification from '../../../backend/investigation/experiments/results/held_out_2025_v1/verification.json';
import stopping from '../../../backend/investigation/experiments/results/policy_selection_2024_v1/selection.json';
import manifest from '../../../backend/investigation/experiments/results/publication.json';
import ResearchPage from '../features/investigation/ResearchPage';
import { sessionsAPI } from '../features/investigation/api';
import { decisionSeries, frozenSeries, publicationData, questionSeries, stoppingSeries } from '../features/investigation/research';

const auth = vi.hoisted(() => ({ user: { id: 'owner', organization_id: 'org' } }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => auth }));
vi.mock('../features/investigation/api', () => ({ sessionsAPI: { experiments: vi.fn() } }));
// Component tests inspect exact chart inputs; the hosted browser verifies actual SVG.
vi.mock('../components/ui/ResearchChart', async importOriginal => {
  const original = await importOriginal();
  return { ...original, default: props => <figure aria-label={props.title}><p>{props.title}</p><output data-testid={props.title}>{JSON.stringify(props.series)}</output><p>{props.caption}</p></figure> };
});
const saved = { schema_version: 'investigation-results-v2', state: 'available', question_selection: question, decision_selection: decision, held_out: held, held_out_verification: verification, selected_policy: held.policy, stopping_selection: { ...stopping, tables: stopping.tables.filter(row => row.g_min === held.policy.parameters.g_min) }, artifacts: manifest.artifacts, publication_sha256: 'test-manifest-hash' };
function mount() { return render(<MemoryRouter><ResearchPage /></MemoryRouter>); }
beforeEach(() => { vi.resetAllMocks(); auth.user = { id: 'owner', organization_id: 'org' }; });

describe('Published research page', () => {
  it('shows frozen held-out measurements, acceptance and uncertain proxy wording', async () => {
    let resolve;
    sessionsAPI.experiments.mockReturnValue(new Promise(done => { resolve = done; }));
    mount();
    expect(screen.getByRole('status')).toHaveTextContent('Loading verified');
    await act(async () => resolve({ data: saved }));
    const chart = JSON.parse(screen.getByTestId('Top-1 accuracy after follow-up questions').textContent);
    expect(chart).toEqual(questionSeries(held.question_budget_summaries.all_attributes['primary_all/all'], 'top1'));
    expect(chart).toHaveLength(3);
    expect(screen.getByText(/Accepted on 2024/)).toHaveTextContent('answer threshold 0.80, minimum gain 0.50');
    expect(screen.getByTestId('paired-difference')).toHaveTextContent('interval includes zero');
    expect(screen.getByText(/not a sentence hallucination/)).toBeInTheDocument();
    expect(screen.getByText(/7 answers, 5 top-one matches, 150 abstentions/)).toBeInTheDocument();
    expect(screen.getByTestId('held-out-ece')).toHaveTextContent('0.184 (95% CI 0.131 to 0.246');
    expect(screen.getAllByText(/999 valid draws/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Publication SHA-256/)).toHaveTextContent('test-manifest-hash');
  });
  it('changes attribute control, correction cohort and metric using committed values', async () => {
    sessionsAPI.experiments.mockResolvedValue({ data: saved }); mount();
    await screen.findByTestId('Top-1 accuracy after follow-up questions');
    fireEvent.change(screen.getByLabelText('Attribute control'), { target: { value: 'coded_fields_only' } });
    const key = Object.keys(question.summaries.coded_fields_only.by_part_change)[0];
    fireEvent.change(screen.getByLabelText('Correction cohort'), { target: { value: key } });
    fireEvent.change(screen.getByLabelText('Question metric'), { target: { value: 'entropy' } });
    expect(JSON.parse(screen.getByTestId('Belief entropy (bits) after follow-up questions').textContent)).toEqual(questionSeries(held.question_budget_summaries.coded_fields_only[`primary_all/${key}`], 'entropy'));
    fireEvent.change(screen.getByLabelText('Answered-case accuracy'), { target: { value: 'accuracy_top3' } });
    expect(JSON.parse(screen.getByTestId('Accuracy against coverage').textContent)).toEqual(frozenSeries(held.stopping.filter(row => row.cohort === 'coded_fields_only' && row.availability === 'primary_all' && row.stratum === key), 'accuracy_top3', false));
  });
  it('marks only the accepted question-conditioned selection row and preserves the earlier study', async () => {
    sessionsAPI.experiments.mockResolvedValue({ data: saved }); mount();
    await screen.findByTestId('Accuracy against coverage');
    fireEvent.change(screen.getByLabelText('Evidence set'), { target: { value: 'stopping_selection' } });
    const rows = saved.stopping_selection.tables.filter(row => row.cohort === 'all_attributes' && row.stratum === 'all');
    let plotted = JSON.parse(screen.getByTestId('Accuracy against coverage').textContent);
    expect(plotted).toEqual(stoppingSeries(rows, 'accuracy_top1', held.policy, true));
    expect(plotted.find(row => row.id === 'accepted').points[0].x).toBe(held.policy.selected_2024_row.coverage);
    fireEvent.change(screen.getByLabelText('Attribute control'), { target: { value: 'coded_fields_only' } });
    plotted = JSON.parse(screen.getByTestId('Accuracy against coverage').textContent);
    expect(plotted.some(row => row.id === 'accepted')).toBe(false);
    fireEvent.change(screen.getByLabelText('Evidence set'), { target: { value: 'pre_question' } });
    expect(JSON.parse(screen.getByTestId('Accuracy against coverage').textContent)).toEqual(decisionSeries(decision.selection, 'accuracy_top1'));
    expect(screen.getByText(/Historical study before questioning/)).toBeInTheDocument();
  });
  it('keeps zero-answer control accuracy null and supports the predeclared timing view', async () => {
    sessionsAPI.experiments.mockResolvedValue({ data: saved }); mount();
    await screen.findByTestId('Accuracy against coverage');
    fireEvent.change(screen.getByLabelText('Attribute control'), { target: { value: 'coded_fields_only' } });
    const before = JSON.parse(screen.getByTestId('Accuracy against coverage').textContent);
    expect(before[0].points[0].y).toBeNull();
    expect(screen.getAllByText('Undefined (no answered cases)').length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText('Time-availability check'), { target: { value: 'after_selection_labels' } });
    expect(JSON.parse(screen.getByTestId('Accuracy against coverage').textContent)).toEqual(before);
  });
  it('rejects a false held-out status or an incompatible accepted policy', () => {
    expect(() => publicationData({ ...saved, held_out: { ...held, selection_or_tuning_performed: true } })).toThrow();
    expect(() => publicationData({ ...saved, selected_policy: { ...held.policy, file_sha256: 'wrong' } })).toThrow();
  });
  it('shows explicit empty and failure states, retries, and rejects malformed publication', async () => {
    sessionsAPI.experiments.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ data: { nonsense: true } }).mockResolvedValueOnce({ data: { schema_version: 'investigation-results-v2', state: 'empty' } });
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
    sessionsAPI.experiments.mockReturnValueOnce(new Promise(done => { resolve = done; })).mockResolvedValueOnce({ data: { schema_version: 'investigation-results-v2', state: 'empty' } });
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
