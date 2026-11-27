import { Link } from 'react-router-dom';
import { formatDate } from '../../utils/format';
import historyLink from './historyLink';

// One maintenance record: ids, date, part details and free text. Used for both the
// incoming record and the retrieved prior record.
export default function RecordCard({ record, tail, assetUuid, showJasc = false }) {
  return (
    <div className="space-y-4 font-sans text-sm">
      <div>
        <span className="text-secondary">Record ID:</span>{' '}
        <span className="font-mono text-primary">{record.record_id}</span>
      </div>
      {tail && (
        <div>
          <span className="text-secondary">Tail Number:</span>{' '}
          <span className="text-primary">{tail}</span>
        </div>
      )}
      <div>
        <span className="text-secondary">Date:</span>{' '}
        <span className="text-primary">{formatDate(record.occurred_at)}</span>
      </div>

      <div className="rounded border border-theme bg-black/5 p-3 dark:bg-white/5">
        <div className="mb-1 font-semibold text-primary">{record.part_name}</div>
        <div className="mb-2 space-x-3 text-xs text-secondary">
          {record.part_condition && <span>Condition: {record.part_condition}</span>}
          {record.part_location && <span>Location: {record.part_location}</span>}
          {showJasc && record.jasc_code && <span>JASC: {record.jasc_code}</span>}
        </div>
        <div className="mt-3 whitespace-pre-wrap text-primary">{record.text}</div>
      </div>

      {assetUuid && record.record_id && (
        <Link
          to={historyLink(assetUuid, record.record_id)}
          className="inline-block text-xs text-accent hover:underline"
        >
          Open in asset history →
        </Link>
      )}
    </div>
  );
}
