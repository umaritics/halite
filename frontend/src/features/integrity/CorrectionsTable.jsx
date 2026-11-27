import { Link } from 'react-router-dom';
import StatusChip from '../../components/StatusChip';
import { EmptyState } from '../../components/ui';
import { labelText } from '../../lib/reviewLabels';
import historyLink from './historyLink';

const GRID = 'grid grid-cols-[6rem_1fr_3rem_1fr_10rem] gap-3';

function CorrectionRow({ row }) {
  const { aircraft, older_record: older, newer_record: newer } = row;
  return (
    <div className={`${GRID} border-b border-theme px-4 py-4 text-sm`}>
      <span className="text-primary">{aircraft.tail_number}</span>
      <Link className="text-primary hover:underline" to={historyLink(aircraft.id, older.id)}>
        <span className="block font-mono text-xs">{older.id}</span>
        {older.part_name}
      </Link>
      <span className={row.component_changed ? 'text-amber-600 dark:text-amber-400' : 'text-secondary'}>
        →
      </span>
      <Link className="text-primary hover:underline" to={historyLink(aircraft.id, newer.id)}>
        <span className="block font-mono text-xs">{newer.id}</span>
        {newer.part_name}
        {row.component_changed && (
          <span className="mt-1 block text-xs text-amber-600 dark:text-amber-400">
            {older.part_name} → {newer.part_name}
          </span>
        )}
        <span className="mt-1 block text-xs text-secondary">{row.rationale}</span>
      </Link>
      <div>
        <StatusChip status={row.review_status} analysisState={row.review_status} />
        <p className="mt-1 text-xs text-secondary">{labelText(row.classification_label)}</p>
      </div>
    </div>
  );
}

export default function CorrectionsTable({ items }) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No detected corrections"
        body="No detected corrections match these filters."
      />
    );
  }

  return (
    <div className="halite-card overflow-hidden">
      <div className={`${GRID} border-b border-theme px-4 py-3 text-xs text-secondary`}>
        <span>Aircraft</span>
        <span>Older finding</span>
        <span></span>
        <span>Newer finding</span>
        <span>Review</span>
      </div>
      {items.map((row) => (
        <CorrectionRow key={`${row.newer_record.id}-${row.older_record.id}`} row={row} />
      ))}
    </div>
  );
}
