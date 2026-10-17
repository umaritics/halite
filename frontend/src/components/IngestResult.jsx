import { Link } from 'react-router-dom';

// The backend's own counts, labelled for what they actually count (backend/agents/maintenance_agent.py).
const FIELDS = [
  ['records_created', 'New records', 'ServiceRecord nodes created by this run.'],
  ['duplicates_skipped', 'Already in graph', 'Rows whose record ID was already stored; skipped, not changed.'],
  [
    'assets_created',
    'Aircraft in file',
    'Distinct aircraft among the valid rows. Includes aircraft that already existed, so it is not the number of new aircraft.',
  ],
  ['rows_skipped_no_tail', 'Skipped: no tail number', 'Rows with a blank RegistryNNumber.'],
  [
    'rows_skipped_bad_date',
    'Skipped: bad date or no record ID',
    'Rows whose DifficultyDate is not MM/DD/YYYY, or whose OperatorControlNumber is blank.',
  ],
];

const show = (v) => (v === undefined || v === null ? '—' : v);

// Says nothing the counts do not support.
function summary(result) {
  const created = result.records_created;
  const dupes = result.duplicates_skipped;
  if (created === 0 && !dupes) {
    return 'No records were created. Check the file: it needs RegistryNNumber, DifficultyDate (MM/DD/YYYY) and OperatorControlNumber columns, as in the FAA SDR export.';
  }
  if (created === 0 && dupes > 0) {
    return `Nothing new: all ${dupes} valid rows were already in the graph.`;
  }
  return null;
}

export default function IngestResult({ result }) {
  const note = summary(result);
  return (
    <div id="ingest-result" className="mt-6 rounded border border-theme bg-surface-dark/5 p-4">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        {FIELDS.map(([key, label, hint]) => (
          <div key={key} className="flex flex-col" title={hint}>
            <span className="font-sans text-xs text-secondary">{label}</span>
            <span
              className={`font-mono text-lg ${key.startsWith('rows_skipped') ? 'text-amber-500' : 'text-primary'}`}
            >
              {show(result[key])}
            </span>
          </div>
        ))}
      </div>
      {note && <p role="status" className="mt-4 font-sans text-sm text-amber-500">{note}</p>}
      {result.records_created > 0 && (
        <p className="mt-4 font-sans text-sm text-secondary">
          New records are not analysed yet.{' '}
          <Link to="/app/records?analysis_state=unscored" className="text-accent hover:underline">
            View them in Service Records →
          </Link>
        </p>
      )}
    </div>
  );
}
