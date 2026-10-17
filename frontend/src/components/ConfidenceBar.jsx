import React from 'react';

export default function ConfidenceBar({
  confidence,
  threshold = 0.50,
  analysisState,
  classification,
  candidateCount,
  status,
  legacyPlaceholder = false,
  analysisMethod,
  analysisPasses,
  voteAgreement,
}) {
  const methodDetail = (() => {
    if (analysisMethod === 'screen') {
      return classification === 'no_candidates'
        ? 'Candidate screen; no model request.'
        : 'Text-overlap screen; no model request.';
    }
    if (analysisMethod === 'llm-escalated') {
      const agreeing = Math.round((voteAgreement ?? 0) * (analysisPasses ?? 5));
      return `Model, escalated ${agreeing}/${analysisPasses ?? 5} votes agree.`;
    }
    if (analysisMethod === 'llm' && analysisPasses) {
      return `Model, ${analysisPasses} passes agree.`;
    }
    return '';
  })();

  if (status === 'superseded') return null;
  if (legacyPlaceholder || analysisState === 'unscored' || confidence === undefined || confidence === null) {
    return (
      <div className="flex flex-col gap-1 w-full max-w-[120px]">
        <div className="text-xs font-medium text-secondary">Not analysed</div>
      </div>
    );
  }

  if (['no_candidates', 'no_conflict', 'scope_disjoint'].includes(classification)) {
    return (
      <div
        className="text-xs text-secondary"
        title={`The conflict engine found no correction relationship in the comparisons it performed.${methodDetail ? ` ${methodDetail}` : ''}`}
      >
        No conflict found ({candidateCount ?? 0} comparisons)
      </div>
    );
  }

  const value = Math.max(0, Math.min(1, confidence));
  const percent = (value * 100).toFixed(0);
  const belowThreshold = value < threshold;

  return (
    <div
      className="flex flex-col gap-1 w-full max-w-[150px]"
      title={`Conflict-check score: a heuristic routing score, not a probability.${methodDetail ? ` ${methodDetail}` : ''}`}
    >
      <div className="flex justify-between items-center text-xs font-mono text-secondary">
        <span>{classification || 'Conflict check'}</span>
        <span>{value.toFixed(2)}</span>
      </div>
      <div className="text-[10px] leading-tight text-secondary">
        Conflict-check score (heuristic, not a probability)
      </div>
      <div className="h-1.5 w-full bg-surface-dark/10 rounded-full overflow-hidden">
        <div 
          className={`h-full bg-accent transition-all ${belowThreshold ? 'opacity-40' : ''}`}
          style={{ width: `${percent}%` }}
        ></div>
      </div>
    </div>
  );
}
