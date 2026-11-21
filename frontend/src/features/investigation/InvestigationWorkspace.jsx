import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { sessionsAPI } from './api';
import { clearLegacyInvestigations } from './privacy';
import { ErrorCard, investigationError, PageHeader } from './feedback';
import { BeliefBars, DecisionBadge, GroundedReply, QuestionCard } from './DecisionView';
import CloseSessionDialog from './CloseSessionDialog';
import SourceNarrative from './SourceNarrative';

function SavedEvidence({ response, highlighted, onHighlight, sourceSelection }) {
  const checks = response?.ranked_checks || [];
  const evidence = response?.evidence || [];
  return <div className="space-y-4">
    <section className="halite-card p-4" aria-label="Historical ranking">
      <h2 className="font-brand text-lg text-primary">Historical ranking</h2>
      <p className="mt-1 text-xs text-secondary">Rank scores describe the retrieved history. They do not establish a fault cause.</p>
      {!checks.length && <p className="mt-3 text-sm text-secondary">No ranked checks were found.</p>}
      <ol className="mt-3 space-y-3">{checks.map(check => <li key={check.part_name} className="min-w-0 border-t border-theme pt-3 text-sm">
        <div className="flex justify-between gap-3 text-primary"><strong>{check.rank}. {check.part_name}</strong><span>Score {check.score}</span></div>
        <p className="mt-1 text-xs text-secondary">{check.evidence_count} records · {(check.sources || []).join(', ')}</p>
        <div className="mt-2 flex flex-wrap gap-2">{(check.evidence_record_ids || []).map(id => <button type="button" key={id}
          className="break-all text-xs text-accent underline" onClick={() => onHighlight(id)}>{id}</button>)}</div>
      </li>)}</ol>
    </section>
    <section className="halite-card p-4" aria-label="Saved evidence">
      <h2 className="font-brand text-lg text-primary">Saved evidence</h2>
      <p className="mt-1 text-xs text-secondary">Original record text saved with this turn.</p>
      {highlighted && !evidence.some(record => record.record_id === highlighted) && <p role="status" className="mt-2 text-xs text-secondary">{highlighted} is referenced by the ranking but its narrative is absent from this turn’s saved evidence.</p>}
      {!evidence.length && <p className="mt-3 text-sm text-secondary">No records were retrieved for this turn.</p>}
      <div className="mt-3 space-y-3">{evidence.map(record => <details key={record.record_id} open={highlighted === record.record_id || undefined}
        className={`min-w-0 rounded border p-3 ${highlighted === record.record_id ? 'border-accent' : 'border-theme'}`}>
        <summary className="cursor-pointer break-all text-sm text-accent">{record.record_id} · {record.part_name || 'Unnamed part'}</summary>
        <p className="mt-2 text-xs text-secondary">{record.asset_id ? `Aircraft identifier: ${record.asset_id} · ` : ''}{record.occurred_at}</p>
        {record.is_superseded && <p className="mt-2 text-xs text-amber-500">Superseded — historical context only</p>}
        <SourceNarrative text={response.grounding?.evidence?.find(source => source.record_id === record.record_id)?.text ?? record.text} annotation={sourceSelection?.recordId === record.record_id ? sourceSelection.sentence.candidates?.find(candidate => candidate.record_id === record.record_id)?.source_matches : undefined} selected={sourceSelection?.recordId === record.record_id} />
      </details>)}</div>
    </section>
  </div>;
}

function Workspace({ sessionId, user }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [needsReload, setNeedsReload] = useState(false);
  const messageRef = useRef('');
  const [error, setError] = useState(null);
  const [message, setMessage] = useState('');
  const [closeOpen, setCloseOpen] = useState(false);
  const [closeError, setCloseError] = useState(null);
  const [selectedTurnId, setSelectedTurnId] = useState(null);
  const [highlighted, setHighlighted] = useState(null);
  const [sourceSelection, setSourceSelection] = useState(null);
  const [reload, setReload] = useState(0);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    clearLegacyInvestigations();
    const abort = new AbortController();
    setLoading(true); setError(null); setSession(null); setNeedsReload(false); setSourceSelection(null);
    sessionsAPI.get(sessionId, abort.signal).then(({ data }) => {
      if (!abort.signal.aborted) {
        setSession(data);
        if (messageRef.current.trim() && data.turns?.at(-1)?.user_text === messageRef.current.trim()) {
          setMessage(''); messageRef.current = '';
        }
      }
    }).catch(err => { if (!abort.signal.aborted) setError(investigationError(err)); })
      .finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => { alive.current = false; abort.abort(); clearLegacyInvestigations(); };
  }, [sessionId, reload]);
  const turns = session?.turns || [];
  const latest = turns.at(-1)?.response;
  const selectedTurn = turns.find(turn => turn.id === selectedTurnId) || turns.at(-1);
  const selectedResponse = selectedTurn?.response;
  const canWrite = Boolean(session?.can_write && session?.status === 'open' && session?.user_id === user.id);

  async function send(answer) {
    const text = answer ? `Answer to ${answer.attribute}: ${answer.value}` : message.trim();
    if (!text || pending || needsReload || !canWrite) return;
    setPending(true); setError(null);
    try {
      const { data } = await sessionsAPI.turn(sessionId, { message: text, ...(answer ? { answer } : {}) });
      if (!alive.current) return;
      setSession(previous => ({ ...previous, turn_count: data.turn_index, turns: [
        ...previous.turns, { id: data.turn_id, idx: data.turn_index, user_text: text, response: data },
      ] }));
      setMessage(''); messageRef.current = ''; setSelectedTurnId(data.turn_id); setHighlighted(null); setSourceSelection(null);
    } catch (err) {
      if (alive.current) {
        setError(investigationError(err));
        setNeedsReload(!err?.response || err.response.status === 409 || err.response.status >= 500);
      }
    }
    finally { if (alive.current) setPending(false); }
  }
  async function close(outcome) {
    if (!canWrite || pending || needsReload) return;
    setPending(true); setCloseError(null);
    try {
      const { data } = await sessionsAPI.close(sessionId, outcome);
      if (!alive.current) return;
      setSession(previous => ({ ...previous, ...data, can_write: false }));
      setCloseOpen(false);
    } catch (err) {
      if (alive.current) {
        if (!err?.response || err.response.status === 409 || err.response.status >= 500) {
          setError(investigationError(err)); setNeedsReload(true); setCloseOpen(false);
        } else setCloseError(investigationError(err));
      }
    }
    finally { if (alive.current) setPending(false); }
  }
  async function printReport() {
    const popup = window.open('', '_blank');
    if (!popup) { setError('Your browser blocked the report window. Allow pop-ups for Halite, then try again.'); return; }
    popup.opener = null;
    popup.document.body.textContent = 'Loading investigation report…';
    try {
      const { data } = await sessionsAPI.report(sessionId);
      if (!alive.current) { popup.close(); return; }
      popup.document.open(); popup.document.write(data); popup.document.close();
      popup.focus(); popup.print();
    } catch (err) { popup.close(); if (alive.current) setError(investigationError(err)); }
  }

  if (loading) return <p role="status" className="p-6 text-secondary">Loading saved investigation…</p>;
  return <div className="h-full overflow-y-auto p-4 sm:p-6">
    <div className="mx-auto max-w-[96rem] space-y-5">
      <Link className="text-sm text-accent underline" to="/app/investigations">Back to investigations</Link>
      <ErrorCard message={error} retryLabel="Reload saved investigation" onRetry={() => setReload(n => n + 1)} />
      {session && <>
        <PageHeader title={session.title} description={`${session.asset_tail || 'All fleet'} · ${session.status} · ${session.turn_count} turns`}>
          <div className="flex flex-wrap gap-2">
            {canWrite && <button type="button" className="halite-btn-outline disabled:opacity-50" disabled={pending || needsReload} onClick={() => setCloseOpen(true)}>Close investigation</button>}
            {session.status === 'closed' && <button type="button" className="halite-btn-outline" onClick={printReport}>Print investigation report</button>}
          </div>
        </PageHeader>
        {!canWrite && <p role="status" className="text-sm text-secondary">{session.status === 'closed' ? 'Closed investigation — read only.' : 'Supervisor view — only the owner can change this investigation.'}</p>}
        {session.status === 'closed' && <section className="halite-card p-4" aria-label="Recorded outcome">
          <h2 className="font-brand text-lg text-primary">Recorded outcome</h2>
          {session.outcome_part && <p className="mt-2 text-sm text-primary">Part: {session.outcome_part}{session.outcome_jasc ? ` · JASC ${session.outcome_jasc}` : ''}</p>}
          <p className="mt-2 whitespace-pre-wrap text-sm text-primary">{session.outcome_note}</p>
        </section>}
        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(20rem,1fr)]">
          <div className="min-w-0 space-y-4">
            {!turns.length && <div className="halite-card p-6 text-sm text-secondary">Describe the symptom or what you have observed to begin.</div>}
            <ol aria-label="Investigation conversation" className="space-y-4">{turns.map(turn => <li key={turn.id} className="halite-card min-w-0 p-4">
              <div className="flex flex-wrap justify-between gap-2"><h2 className="font-brand text-base text-primary">Turn {turn.idx}</h2><button type="button" className="text-xs text-accent underline" onClick={() => { setSelectedTurnId(turn.id); setHighlighted(null); setSourceSelection(null); }}>View evidence for turn {turn.idx}</button></div>
              <p className="mt-2 whitespace-pre-wrap break-words text-sm text-primary">{turn.user_text}</p>
              <div className="mt-4 space-y-3 border-t border-theme pt-4">
                <DecisionBadge response={turn.response} />
                {turn.response.llm_status === 'unavailable' && <p role="status" className="text-xs text-secondary">Model unavailable · deterministic explanation</p>}
                <GroundedReply reply={turn.response.reply} grounding={turn.response.grounding} onCitationFocus={id => { setSelectedTurnId(turn.id); setHighlighted(id); }} onSentenceFocus={(id, sentence) => setSourceSelection({ turnId: turn.id, recordId: id, sentence })} />
                {(turn.response.warnings || []).length > 0 && <details><summary className="cursor-pointer text-xs text-secondary">Turn notices</summary><ul className="mt-2 space-y-1 text-xs text-secondary">{turn.response.warnings.map((notice, i) => <li key={i}>{notice}</li>)}</ul></details>}
              </div>
            </li>)}</ol>
            {latest?.question && canWrite && <QuestionCard key={latest.turn_id} question={latest.question} disabled={pending || needsReload} onAnswer={send} />}
            {canWrite && <form className="halite-card p-4" onSubmit={event => { event.preventDefault(); send(); }}>
              <label htmlFor="investigation-message" className="block text-sm text-primary">Symptom, observation or check result</label>
              <textarea id="investigation-message" className="halite-input mt-2 min-h-24" maxLength={4000} value={message} disabled={pending} onChange={event => { setMessage(event.target.value); messageRef.current = event.target.value; }} />
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3"><span className="text-xs text-secondary">{message.length}/4000</span><button className="halite-btn-primary disabled:opacity-50" disabled={!message.trim() || pending || needsReload}>{pending ? 'Saving turn…' : 'Send observation'}</button></div>
              {needsReload && <p role="status" className="mt-2 text-xs text-secondary">Reload the saved investigation before sending another observation.</p>}
              {pending && <p role="status" className="mt-2 text-xs text-secondary">The server is processing and saving this turn. Keep this page open.</p>}
            </form>}
            <p className="text-xs text-secondary">Decision support only. Approved maintenance documentation and qualified personnel remain authoritative.</p>
          </div>
          <aside className="min-w-0 space-y-4">
            <p className="text-xs text-secondary">{selectedTurn ? `Saved snapshot from turn ${selectedTurn.idx}` : 'No saved turn yet'}</p>
            <BeliefBars beliefs={selectedResponse?.beliefs} />
            {selectedResponse?.case_state && <section className="halite-card p-4" aria-label="Reported case information"><h2 className="font-brand text-lg text-primary">Case information</h2>
              {Object.entries(selectedResponse.case_state).map(([field, values]) => Array.isArray(values) && values.length > 0 && <div key={field} className="mt-3"><h3 className="text-xs uppercase text-secondary">{field.replaceAll('_', ' ')}</h3><ul className="mt-1 list-inside list-disc text-sm text-primary">{values.map((value, i) => <li key={i}>{value}</li>)}</ul></div>)}
            </section>}
            {selectedResponse && <SavedEvidence response={selectedResponse} highlighted={highlighted} onHighlight={id => { setHighlighted(id); setSourceSelection(null); }} sourceSelection={sourceSelection?.turnId === selectedTurn?.id ? sourceSelection : null} />}
          </aside>
        </div>
        {closeOpen && <CloseSessionDialog pending={pending} onCancel={() => setCloseOpen(false)} onSubmit={close} error={closeError} />}
      </>}
    </div>
  </div>;
}

export default function InvestigationWorkspace({ sessionId: suppliedId }) {
  const { user } = useAuth();
  const { id } = useParams();
  const sessionId = suppliedId || id;
  if (!user) return <p className="p-6 text-primary">Sign in to view this investigation.</p>;
  return <Workspace key={`${user.id}:${user.organization_id}:${sessionId}`} user={user} sessionId={sessionId} />;
}
