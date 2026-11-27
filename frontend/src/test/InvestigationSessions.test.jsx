import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import InvestigationsPage from '../features/investigation/InvestigationsPage';
import InvestigationWorkspace from '../features/investigation/InvestigationWorkspace';
import HomePage from '../features/home/HomePage';
import { GroundedReply, QuestionCard } from '../features/investigation/DecisionView';
import { clearLegacyInvestigations, LEGACY_INVESTIGATION_KEYS } from '../features/investigation/privacy';
import { sessionsAPI } from '../features/investigation/api';
import api from '../api/client';

const auth = vi.hoisted(() => ({ user: null }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => auth }));
vi.mock('../features/investigation/api', () => ({ sessionsAPI: {
  assets: vi.fn(), list: vi.fn(), get: vi.fn(), create: vi.fn(), turn: vi.fn(), close: vi.fn(), report: vi.fn(), summary: vi.fn(),
} }));
vi.mock('../api/client', () => ({ default: { get: vi.fn() } }));

const owner = { id: 'owner', organization_id: 'org', role: 'technician' };
const saved = (overrides = {}) => ({
  id: 'session-one', user_id: 'owner', title: 'Pump investigation', asset_tail: 'N123', status: 'open',
  turn_count: 0, can_write: true, turns: [], created_at: '2024-01-01T00:00:00Z', ...overrides,
});
const reply = (overrides = {}) => ({
  turn_id: 'turn-1', turn_index: 1, session_id: 'session-one', reply: 'Pump leak in AALA2024010100001.',
  llm_status: 'unavailable', policy_status: 'not_configured', decision: 'abstain', warnings: [],
  case_state: { symptoms: ['pump leak'], observations: [], checks_done: [], ruled_out: [], open_questions: [] },
  ranked_checks: [{ rank: 1, part_name: 'PUMP', score: .4, evidence_count: 1, evidence_record_ids: ['AALA2024010100001'], sources: ['asset_history'] }],
  evidence: [{ record_id: 'AALA2024010100001', part_name: 'PUMP', text: 'Original pump leak narrative', occurred_at: '2024-01-01', asset_id: 'N123' }],
  ...overrides,
});
function renderPage(path = '/app/investigations') {
  return render(<MemoryRouter initialEntries={[path]}><Routes>
    <Route path="/app/home" element={<HomePage />} />
    <Route path="/app/investigations" element={<InvestigationsPage />} />
    <Route path="/app/investigations/:id" element={<InvestigationWorkspace />} />
  </Routes></MemoryRouter>);
}

beforeEach(() => {
  vi.resetAllMocks();
  auth.user = { ...owner };
  localStorage.clear();
  sessionsAPI.assets.mockResolvedValue({ data: [{ id: 'asset', tail_number: 'N123' }] });
  sessionsAPI.list.mockResolvedValue({ data: { items: [], next_cursor: null } });
  sessionsAPI.get.mockResolvedValue({ data: saved() });
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value() { this.setAttribute('open', ''); } });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value() { this.removeAttribute('open'); } });
});

describe('Saved investigation history', () => {
  it('loads server history and clears unowned browser copies without importing them', async () => {
    LEGACY_INVESTIGATION_KEYS.forEach(key => localStorage.setItem(key, JSON.stringify([{ title: 'Other user secret' }])));
    sessionsAPI.list.mockResolvedValue({ data: { items: [saved()], next_cursor: null } });
    renderPage();
    expect(await screen.findByRole('link', { name: 'Pump investigation' })).toBeInTheDocument();
    expect(screen.queryByText('Other user secret')).not.toBeInTheDocument();
    LEGACY_INVESTIGATION_KEYS.forEach(key => expect(localStorage.getItem(key)).toBeNull());
    expect(sessionsAPI.list).toHaveBeenCalledWith({ status: undefined, mine: true, limit: 20 }, expect.any(AbortSignal));
    fireEvent.click(screen.getByRole('link', { name: 'Pump investigation' }));
    expect(await screen.findByLabelText('Symptom, observation or check result')).toBeInTheDocument();
    expect(sessionsAPI.get).toHaveBeenCalledWith('session-one', expect.any(AbortSignal));
  });

  it('creates only on explicit submission, sends the chosen graph UUID and opens the saved session', async () => {
    sessionsAPI.create.mockResolvedValue({ data: saved() });
    renderPage();
    expect(await screen.findByText('No investigations in this view')).toBeInTheDocument();
    expect(sessionsAPI.create).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText('Investigation title (optional)'), { target: { value: 'Pressure loss' } });
    fireEvent.change(screen.getByLabelText('Aircraft'), { target: { value: 'asset' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create investigation' }));
    await screen.findByLabelText('Symptom, observation or check result');
    expect(sessionsAPI.create).toHaveBeenCalledWith({ title: 'Pressure loss', asset_id: 'asset' });
  });

  it('shows list failures as errors, supports retry and preserves backend cursor pagination', async () => {
    sessionsAPI.list.mockRejectedValueOnce({ response: { status: 503 } }).mockResolvedValueOnce({ data: { items: [saved()], next_cursor: 'cursor' } })
      .mockResolvedValueOnce({ data: { items: [saved({ id: 'second', title: 'Second investigation' })], next_cursor: null } });
    renderPage();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText('No investigations in this view')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByText('Pump investigation');
    fireEvent.click(screen.getByRole('button', { name: 'Load more investigations' }));
    expect(await screen.findByText('Second investigation')).toBeInTheDocument();
    expect(sessionsAPI.list).toHaveBeenLastCalledWith({ status: undefined, mine: true, cursor: 'cursor', limit: 20 });
  });

  it('keeps fleet creation available when aircraft options fail and does not invent aircraft', async () => {
    sessionsAPI.assets.mockRejectedValue(new Error('offline'));
    renderPage();
    expect(await screen.findByText(/Aircraft options could not be loaded/)).toBeInTheDocument();
    expect(within(screen.getByLabelText('Aircraft')).getAllByRole('option')).toHaveLength(1);
  });

  it('hides another identity’s state immediately on account change', async () => {
    sessionsAPI.list.mockResolvedValueOnce({ data: { items: [saved()], next_cursor: null } });
    const { rerender } = render(<MemoryRouter><InvestigationsPage /></MemoryRouter>);
    await screen.findByText('Pump investigation');
    auth.user = { ...owner, id: 'other' };
    sessionsAPI.list.mockResolvedValueOnce({ data: { items: [], next_cursor: null } });
    rerender(<MemoryRouter><InvestigationsPage /></MemoryRouter>);
    expect(screen.queryByText('Pump investigation')).not.toBeInTheDocument();
    await screen.findByText('No investigations in this view');
  });
});

describe('Persisted workspace', () => {
  it('replays saved turns without inference, then posts only the new message', async () => {
    const response = reply();
    sessionsAPI.get.mockResolvedValue({ data: saved({ turn_count: 1, turns: [{ id: 'turn-1', idx: 1, user_text: 'pump leak', response }] }) });
    sessionsAPI.turn.mockResolvedValue({ data: reply({ turn_id: 'turn-2', turn_index: 2, reply: 'A second saved response.' }) });
    renderPage('/app/investigations/session-one');
    expect(await screen.findByText('Pump leak in AALA2024010100001.')).toBeInTheDocument();
    expect(sessionsAPI.turn).not.toHaveBeenCalled();
    expect(screen.getByText('Sentence support has not been checked for this reply.')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Symptom, observation or check result'), { target: { value: 'smoke observed' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send observation' }));
    expect(await screen.findByText('A second saved response.')).toBeInTheDocument();
    expect(sessionsAPI.turn).toHaveBeenCalledWith('session-one', { message: 'smoke observed' });
    expect(screen.getAllByText('Decision policy pending')).toHaveLength(2);
    expect(screen.getByText('Original pump leak narrative')).toBeInTheDocument();
  });

  it('preserves the user draft after a conflict and reloads instead of silently resending', async () => {
    sessionsAPI.turn.mockRejectedValue({ response: { status: 409, data: { detail: 'Investigation changed during this turn.' } } });
    renderPage('/app/investigations/session-one');
    const draft = await screen.findByLabelText('Symptom, observation or check result');
    fireEvent.change(draft, { target: { value: 'pump leak' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send observation' }));
    expect(await screen.findByText('Investigation changed during this turn.')).toBeInTheDocument();
    expect(draft).toHaveValue('pump leak');
    expect(screen.getByRole('button', { name: 'Send observation' })).toBeDisabled();
    expect(sessionsAPI.turn).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Reload saved investigation' }));
    await waitFor(() => expect(sessionsAPI.get).toHaveBeenCalledTimes(2));
    expect(sessionsAPI.turn).toHaveBeenCalledTimes(1);
  });

  it('reloads an uncertain write and clears a draft only when the server proves it was saved', async () => {
    sessionsAPI.get.mockResolvedValueOnce({ data: saved() }).mockResolvedValueOnce({ data: saved({ turn_count: 1, turns: [
      { id: 'turn-1', idx: 1, user_text: 'pump leak', response: reply() },
    ] }) });
    sessionsAPI.turn.mockRejectedValue({ code: 'ECONNABORTED' });
    renderPage('/app/investigations/session-one');
    fireEvent.change(await screen.findByLabelText('Symptom, observation or check result'), { target: { value: 'pump leak' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send observation' }));
    await screen.findByText('Reload the saved investigation before sending another observation.');
    expect(screen.getByRole('button', { name: 'Send observation' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Reload saved investigation' }));
    await screen.findByText('Pump leak in AALA2024010100001.');
    expect(screen.getByLabelText('Symptom, observation or check result')).toHaveValue('');
    expect(sessionsAPI.turn).toHaveBeenCalledTimes(1);
  });

  it('closes only with a nonblank outcome after server confirmation', async () => {
    let confirm;
    sessionsAPI.close.mockImplementation(() => new Promise(resolve => { confirm = resolve; }));
    renderPage('/app/investigations/session-one');
    fireEvent.click(await screen.findByRole('button', { name: 'Close investigation' }));
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByRole('button', { name: 'Close with outcome' })).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText('Finding or outcome (required)'), { target: { value: 'Worn seal found' } });
    fireEvent.change(within(dialog).getByLabelText('Part found (optional)'), { target: { value: 'SEAL' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Close with outcome' }));
    expect(screen.queryByText('Closed investigation — read only.')).not.toBeInTheDocument();
    await act(async () => confirm({ data: saved({ status: 'closed', outcome_note: 'Worn seal found', outcome_part: 'SEAL' }) }));
    expect(await screen.findByText('Closed investigation — read only.')).toBeInTheDocument();
    expect(screen.queryByLabelText('Symptom, observation or check result')).not.toBeInTheDocument();
    expect(sessionsAPI.close).toHaveBeenCalledWith('session-one', { outcome_note: 'Worn seal found', outcome_part: 'SEAL', outcome_jasc: null });
  });

  it('makes supervisor views read only and never exposes a submit action', async () => {
    auth.user = { ...owner, id: 'supervisor', role: 'supervisor' };
    sessionsAPI.get.mockResolvedValue({ data: saved({ can_write: false }) });
    renderPage('/app/investigations/session-one');
    expect(await screen.findByText(/Supervisor view/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Close investigation' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Send observation' })).not.toBeInTheDocument();
  });

  it('prints only the authenticated server report and handles blocked pop-ups', async () => {
    sessionsAPI.get.mockResolvedValue({ data: saved({ status: 'closed', can_write: false, outcome_note: 'Finding recorded' }) });
    const popup = { opener: {}, document: { body: {}, open: vi.fn(), write: vi.fn(), close: vi.fn() }, focus: vi.fn(), print: vi.fn(), close: vi.fn() };
    vi.spyOn(window, 'open').mockReturnValueOnce(null).mockReturnValueOnce(popup);
    sessionsAPI.report.mockResolvedValue({ data: '<!doctype html><p>Escaped saved report</p>' });
    renderPage('/app/investigations/session-one');
    const print = await screen.findByRole('button', { name: 'Print investigation report' });
    fireEvent.click(print);
    expect(await screen.findByText(/browser blocked the report window/)).toBeInTheDocument();
    expect(sessionsAPI.report).not.toHaveBeenCalled();
    fireEvent.click(print);
    await waitFor(() => expect(popup.print).toHaveBeenCalledTimes(1));
    expect(sessionsAPI.report).toHaveBeenCalledWith('session-one');
    expect(popup.document.write).toHaveBeenCalledWith('<!doctype html><p>Escaped saved report</p>');
    expect(popup.opener).toBeNull();
  });

  it('keeps a past turn’s narrative when selecting its saved evidence', async () => {
    const old = reply();
    const newer = reply({ turn_id: 'turn-2', turn_index: 2, evidence: [{ record_id: 'NEW2024010100002', part_name: 'SEAL', text: 'New narrative' }] });
    sessionsAPI.get.mockResolvedValue({ data: saved({ turn_count: 2, turns: [
      { id: 'turn-1', idx: 1, user_text: 'first', response: old }, { id: 'turn-2', idx: 2, user_text: 'second', response: newer },
    ] }) });
    renderPage('/app/investigations/session-one');
    await screen.findByText('New narrative');
    fireEvent.click(screen.getByRole('button', { name: 'View evidence for turn 1' }));
    expect(screen.getByText('Original pump leak narrative')).toBeInTheDocument();
    expect(screen.queryByText('New narrative')).not.toBeInTheDocument();
  });

  it('does not display a slow previous account response after sign-out', async () => {
    let finish;
    sessionsAPI.get.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    const { rerender } = render(<MemoryRouter><InvestigationWorkspace sessionId="session-one" /></MemoryRouter>);
    auth.user = null;
    rerender(<MemoryRouter><InvestigationWorkspace sessionId="session-one" /></MemoryRouter>);
    await act(async () => finish({ data: saved() }));
    expect(screen.queryByText('Pump investigation')).not.toBeInTheDocument();
    expect(screen.getByText('Sign in to view this investigation.')).toBeInTheDocument();
  });
});

describe('Dashboard and future response views', () => {
  it('hides a failed vertical widget and renders only values supplied by successful summaries', async () => {
    api.get.mockImplementation(path => path === '/integrity/summary' ? Promise.reject(new Error('offline')) : Promise.resolve({ data: {
      title: path === '/sessions/summary' ? 'Investigation sessions' : 'Retrieval', link: '/app/investigations', stats: [{ label: 'Open', value: 7 }],
    } }));
    renderPage('/app/home');
    expect(await screen.findByText('Investigation sessions')).toBeInTheDocument();
    expect(screen.queryByText('Record integrity')).not.toBeInTheDocument();
    expect(screen.getAllByText('7')).toHaveLength(2);
    expect(api.get).toHaveBeenCalledTimes(3);
  });

  it('labels all-widget failure and retries without substituting zero statistics', async () => {
    api.get.mockRejectedValue(new Error('offline'));
    renderPage('/app/home');
    expect(await screen.findByRole('alert')).toHaveTextContent('Workspace summaries are unavailable.');
    expect(screen.queryByText('0')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(6));
  });

  it('shows the backend sentence labels and focuses the cited saved record', () => {
    const focus = vi.fn();
    render(<GroundedReply reply="ignored" onCitationFocus={focus} grounding={{ checked_with: 'lexical', sentences: [
      { text: 'Pump leak.', citations: ['REC123456'], level: 'supported' },
      { text: 'Invented cause.', citations: [], level: 'unsupported' },
    ] }} />);
    expect(screen.getByText('1 of 2 sentences supported · lexical')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'REC123456' }));
    expect(focus).toHaveBeenCalledWith('REC123456');
    expect(screen.getByText('unsupported')).toBeInTheDocument();
  });

  it('submits only an offered question value or the explicit not-sure value', () => {
    const answer = vi.fn();
    render(<QuestionCard question={{ attribute: 'part_condition', text: 'What condition?', reason: 'Expected to reduce uncertainty.', options: [{ value: 'CRACKED', label: 'Cracked' }] }} onAnswer={answer} />);
    fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: 'not_sure' } });
    fireEvent.click(screen.getByRole('button', { name: 'Submit answer' }));
    expect(answer).toHaveBeenCalledWith({ attribute: 'part_condition', value: 'not_sure' });
  });

  it('handles denied storage without turning it into a failed server session', () => {
    expect(clearLegacyInvestigations({ removeItem() { throw new Error('denied'); } })).toBe(false);
  });
});

describe('Saved structured questions', () => {
  const question = { id: 'question-1', attribute: 'stage_of_operation', text: 'At what stage?', reason: 'Expected to remove 0.400 of 1.000 bits of uncertainty.',
    options: [{ value: 'CL', label: 'CLIMB (CL)' }, { value: 'CR', label: 'CRUISE (CR)' }] };

  it('sends the saved question identity and resets the selection for the next question', () => {
    const answer = vi.fn();
    const { rerender } = render(<QuestionCard question={question} onAnswer={answer} />);
    fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: 'CL' } });
    fireEvent.click(screen.getByRole('button', { name: 'Submit answer' }));
    expect(answer).toHaveBeenCalledWith({ attribute: 'stage_of_operation', value: 'CL', question_id: 'question-1' });
    rerender(<QuestionCard question={{ ...question, id: 'question-2' }} onAnswer={answer} />);
    expect(screen.getByLabelText('Your answer')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Submit answer' })).toBeDisabled();
  });

  it('keeps an in-flight question disabled', () => {
    render(<QuestionCard question={question} disabled onAnswer={vi.fn()} />);
    expect(screen.getByLabelText('Your answer')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Submit answer' })).toBeDisabled();
  });

  it('submits through the workspace and displays only the confirmed updated beliefs', async () => {
    const initial = reply({ question, decision: 'ask', policy_status: 'experimental', beliefs: {
      calibrated: true, hypotheses: [{ part_name: 'PUMP', belief: .4 }], other: .6, entropy: .97,
    } });
    sessionsAPI.get.mockResolvedValue({ data: saved({ turn_count: 1, turns: [{ id: 'turn-1', idx: 1, user_text: 'pressure loss', response: initial }] }) });
    let resolve;
    sessionsAPI.turn.mockImplementation(() => new Promise(r => { resolve = r; }));
    renderPage('/app/investigations/session-one');
    expect(await screen.findByText('At what stage?')).toBeInTheDocument();
    expect(screen.getByText('Experimental guidance — decision settings are still being evaluated.')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: 'CL' } });
    fireEvent.click(screen.getByRole('button', { name: 'Submit answer' }));
    expect(sessionsAPI.turn).toHaveBeenCalledWith('session-one', { message: 'Answer to stage_of_operation: CL',
      answer: { attribute: 'stage_of_operation', value: 'CL', question_id: 'question-1' } });
    expect(screen.getByText('40.0%')).toBeInTheDocument();
    expect(screen.getByLabelText('Your answer')).toBeDisabled();
    resolve({ data: reply({ turn_id: 'turn-2', turn_index: 2, decision: 'abstain', question: null, policy_status: 'experimental',
      beliefs: { calibrated: true, hypotheses: [{ part_name: 'PUMP', belief: .8 }], other: .2, entropy: .72 } }) });
    expect(await screen.findByText('80.0%')).toBeInTheDocument();
    expect(screen.queryByText('At what stage?')).not.toBeInTheDocument();
  });
});

describe('Sentence score transparency', () => {
  it('does not turn pending thresholds into a supported-sentence claim', () => {
    render(<GroundedReply reply="Pump leak." grounding={{ status: 'thresholds_pending', checked_with: 'lexical', sentences: [
      { text: '**Pump** leak.', citations: [], level: 'unrated', score: 1, reason: 'Thresholds require validation.' },
    ] }} />);
    expect(screen.getByText('Sentence ratings await validation · lexical')).toBeInTheDocument();
    expect(screen.queryByText(/of 1 sentences supported/)).not.toBeInTheDocument();
    expect(screen.getByLabelText('Sentence check: unrated. Thresholds require validation.')).toHaveAttribute('title', 'Thresholds require validation.');
    expect(screen.getByText('Pump')).toHaveProperty('tagName', 'STRONG');
  });

  it('labels experimental settings and exact allowed safety templates separately', () => {
    render(<GroundedReply reply="Provisional." grounding={{ status: 'configured', checked_with: 'lexical', configuration: { status: 'experimental' }, sentences: [
      { text: 'Provisional.', citations: [], level: 'uncited', acceptable_uncited: true },
    ] }} />);
    expect(screen.getByText('Experimental sentence ratings — settings have not been accepted.')).toBeInTheDocument();
    expect(screen.getByText('uncited · allowed template')).toBeInTheDocument();
  });
});
