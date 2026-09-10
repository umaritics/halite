import React from 'react';

export default function ConfidenceBar({ confidence, threshold = 0.50 }) {
  if (confidence === undefined || confidence === null) {
    return (
      <div className="flex flex-col gap-1 w-full max-w-[120px]">
        <div className="flex justify-between items-center text-xs font-mono text-secondary">
          <span>Conf</span>
          <span className="italic">null</span>
        </div>
        <div className="text-[10px] text-secondary/60 uppercase tracking-wider">Not evaluated</div>
      </div>
    );
  }

  const value = Math.max(0, Math.min(1, confidence));
  const percent = (value * 100).toFixed(0);
  const belowThreshold = value < threshold;

  return (
    <div className="flex flex-col gap-1 w-full max-w-[120px]" title={belowThreshold ? "Below threshold" : ""}>
      <div className="flex justify-between items-center text-xs font-mono text-secondary">
        <span>Conf</span>
        <span>{value.toFixed(2)}</span>
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
