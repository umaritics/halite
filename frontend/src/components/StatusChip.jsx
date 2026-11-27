import React from 'react';
import { Badge } from './ui';
import { describeLabel } from '../lib/reviewLabels';

// Shows a record status or an analysis label in words, in both themes.
export default function StatusChip({ status, analysisState, legacyPlaceholder = false }) {
  const isUnscored =
    legacyPlaceholder || analysisState === 'unscored' || status === 'unscored';
  const { text, tone } = describeLabel(isUnscored ? 'unscored' : status);
  const extra = status === 'superseded' && !isUnscored ? 'line-through opacity-70' : '';

  return (
    <Badge tone={tone} className={extra}>
      {text}
    </Badge>
  );
}
