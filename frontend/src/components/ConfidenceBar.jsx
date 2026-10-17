import React from 'react';

export default function ConfidenceBar({
  confidence,
  threshold = 0.50,
  analysisState,
  classification,
  candidateCount,
  status,
}) {
  if (status === 'superseded') return null;
  if (analysisState === 'unscored' || confidence === undefined || confidence === null) {
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
        title="The conflict engine found no correction relationship in the comparisons it performed."
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
      title="Conflict-check score: a heuristic routing score, not a probability."
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
