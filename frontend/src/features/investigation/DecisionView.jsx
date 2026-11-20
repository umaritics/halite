import { useState } from 'react';
import CopilotMarkdown from '../../components/CopilotMarkdown';

export function DecisionBadge({ response }) {
  const pending = response?.policy_status === 'not_configured';
  const experimental = response?.policy_status === 'experimental';
  const labels = { answer: 'Answer', ask: 'Clarification needed', abstain: 'Insufficient evidence', report: 'Record summary' };
  return <div role="status" className="rounded-md border border-theme p-3 text-sm text-primary">
    <strong>{pending ? 'Decision policy pending' : (labels[response?.decision] || 'Historical evidence')}</strong>
    {experimental && <p className="mt-1 text-xs text-secondary">Experimental guidance — decision settings are still being evaluated.</p>}
    {response?.decision_reason && <p className="mt-1 text-secondary">{response.decision_reason}</p>}
  </div>;
}

export function BeliefBars({ beliefs }) {
  if (!Array.isArray(beliefs?.hypotheses)) return null;
  const items = beliefs.hypotheses.map(item => ({ ...item, key: `part:${item.part_name}` }));
  if (Number.isFinite(beliefs.other)) items.push({ key: 'other-bucket', part_name: 'Other / outside ranking', belief: beliefs.other });
  return <section className="halite-card p-4" aria-label="Relative support">
    <h2 className="font-brand text-lg text-primary">Relative support</h2>
    <p className="mb-3 text-xs text-secondary">
      {beliefs.calibrated ? 'Fitted historical support.' : 'Uncalibrated historical support.'} Other covers outcomes outside this ranking.
    </p>
    {items.map((item) => Number.isFinite(item.belief) && <div key={item.key} className="mb-3">
      <div className="flex justify-between gap-3 text-sm text-primary"><span>{item.part_name}</span><span>{(item.belief * 100).toFixed(1)}%</span></div>
      <div role="meter" aria-label={item.part_name} aria-valuemin={0} aria-valuemax={1} aria-valuenow={item.belief}
        aria-valuetext={`${(item.belief * 100).toFixed(1)}% relative support`}
        className="mt-1 h-2 overflow-hidden rounded bg-page">
        <div className="h-full bg-accent transition-[width] motion-reduce:transition-none" style={{ width: `${Math.max(0, Math.min(1, item.belief)) * 100}%` }} />
      </div>
    </div>)}
    {Number.isFinite(beliefs.entropy) && <p className="text-xs text-secondary">Uncertainty: {beliefs.entropy.toFixed(2)} bits, including other.</p>}
  </section>;
}

export function QuestionCard({ question, disabled, onAnswer }) {
  if (!question) return null;
  return <QuestionForm key={question.id || question.attribute} question={question} disabled={disabled} onAnswer={onAnswer} />;
}

function QuestionForm({ question, disabled, onAnswer }) {
  const [value, setValue] = useState('');
  const options = question.options || [];
  return <form className="halite-card p-4" onSubmit={(event) => { event.preventDefault(); if (options.some(option => option.value === value) || value === 'not_sure') onAnswer({ attribute: question.attribute, value, ...(question.id ? { question_id: question.id } : {}) }); }}>
    <fieldset disabled={disabled}>
      <legend className="font-brand text-lg text-primary">{question.text}</legend>
      {question.reason && <p className="mt-2 text-sm text-secondary">Why this question: {question.reason}</p>}
      <label className="mt-3 block text-sm text-primary" htmlFor="investigation-answer">Your answer</label>
      <select id="investigation-answer" className="halite-input mt-1" value={value} onChange={event => setValue(event.target.value)} required>
        <option value="">Choose an answer</option>
        {options.map(option => <option key={option.value} value={option.value}>{option.label || option.value}</option>)}
        <option value="not_sure">Not sure</option>
      </select>
      <button className="halite-btn-primary mt-3 disabled:opacity-50" disabled={!value || disabled}>Submit answer</button>
    </fieldset>
  </form>;
}

export function GroundedReply({ reply, grounding, onCitationFocus }) {
  if (!grounding?.sentences?.length) return <div>
    {reply ? <CopilotMarkdown>{reply}</CopilotMarkdown> : <p className="text-sm text-secondary">No written explanation was returned.</p>}
    <p className="mt-2 text-xs text-secondary">Sentence support has not been checked for this reply.</p>
  </div>;
  const supported = grounding.sentences.filter(s => s.level === 'supported').length;
  return <section aria-label="Checked explanation">
    <p className="mb-2 text-xs text-secondary">{supported} of {grounding.sentences.length} sentences supported · {grounding.checked_with}</p>
    {grounding.sentences.map((sentence, index) => <p key={index} className="mb-2 text-sm text-primary">
      <span title={`Sentence check: ${sentence.level}`} className={sentence.level === 'unsupported' ? 'opacity-60' : ''}>{sentence.text}</span>{' '}
      <span className="rounded border border-theme px-1 text-xs">{sentence.level}</span>
      {(sentence.citations || []).map(id => <button type="button" key={id} className="ml-2 break-all text-xs text-accent underline"
        onMouseEnter={() => onCitationFocus?.(id)} onFocus={() => onCitationFocus?.(id)} onClick={() => onCitationFocus?.(id)}>{id}</button>)}
    </p>)}
  </section>;
}
