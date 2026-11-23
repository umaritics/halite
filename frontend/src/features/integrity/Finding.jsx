import StatusChip from '../../components/StatusChip';
import ConfidenceBar from '../../components/ConfidenceBar';
import { labelText } from '../../lib/reviewLabels';

// What the engine means by each label (see backend/services/conflict_engine.py).
// These describe the classification, not a verdict on which record is right.
const LABEL_MEANING = {
  supersedes: 'The incoming record explicitly updates or closes the prior record.',
  partial_supersedes: 'The incoming record addresses the same issue but only partially resolves it.',
  contradicts: 'The records make mutually exclusive claims about the same part or event.',
};

const CONFLICT_LABELS = Object.keys(LABEL_MEANING);

function examinedText(considered, historyCount) {
  const examined = considered ?? '?';
  if (historyCount === null || historyCount === undefined) {
    return `Examined ${examined} records on this asset.`;
  }
  return `Examined ${examined} of ${historyCount} records on this asset.`;
}

export default function Finding({ label, rationale, confidence, considered, historyCount }) {
  return (
    <div className="border-t border-theme pt-6">
      <div className="mb-3 flex items-start justify-between">
        <StatusChip status={label || 'no_conflict'} />
        <ConfidenceBar
          confidence={confidence}
          analysisState="needs_review"
          classification={label}
          classificationText={label ? labelText(label) : undefined}
          candidateCount={considered}
        />
      </div>
      {LABEL_MEANING[label] && (
        <p className="mb-3 font-sans text-xs text-secondary">{LABEL_MEANING[label]}</p>
      )}
      {!CONFLICT_LABELS.includes(label) && (
        <div className="mb-3 rounded border border-theme/50 bg-black/5 p-2 font-sans text-xs text-secondary dark:bg-white/5">
          Low-confidence no-detection held back as a miss-safety net, not a conflict awaiting adjudication.
        </div>
      )}
      <p className="mb-3 font-sans text-sm text-primary">
        {rationale || 'No rationale provided.'}
      </p>
      <p className="font-sans text-xs italic text-secondary">
        {examinedText(considered, historyCount)}
      </p>
    </div>
  );
}
