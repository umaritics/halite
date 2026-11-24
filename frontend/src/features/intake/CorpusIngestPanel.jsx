import { useState } from 'react';
import { maintenanceAPI } from '../../api/client';
import { describeLoadError } from '../../utils/loadError';
import { Button, ConfirmDialog } from '../../components/ui';
import IngestResult from './IngestResult';

// Admin-only: the path is read on the API server and written to the graph, so the
// run needs an explicit confirmation.
export default function CorpusIngestPanel() {
  const [path, setPath] = useState('data/processed/sdr_poc_corpus.csv');
  const [limit, setLimit] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const runIngest = async () => {
    setConfirming(false);
    setRunning(true);
    setResult(null);
    setError(null);
    try {
      const payload = { csv_path: path };
      if (limit) payload.limit = parseInt(limit, 10);
      const { data } = await maintenanceAPI.ingest(payload);
      setResult(data);
    } catch (err) {
      setError(describeLoadError(err).message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <section className="halite-card p-6">
      <h3 className="font-brand text-primary">Corpus Ingest (server file)</h3>
      <p className="mb-4 mt-1 font-sans text-sm text-secondary">
        Import a CSV that is already on the API server. The path is read on the server, not on your computer.
      </p>

      <div className="mb-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="ingest-path" className="font-sans text-sm text-secondary">CSV Path</label>
          <input
            id="ingest-path"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            className="halite-input mt-1 w-full"
            placeholder="data/processed/sdr_poc_corpus.csv"
          />
        </div>
        <div>
          <label htmlFor="ingest-limit" className="font-sans text-sm text-secondary">Row Limit (Optional)</label>
          <input
            id="ingest-limit"
            type="number"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            className="halite-input mt-1 w-full"
            placeholder="e.g. 150"
          />
        </div>
      </div>

      <Button onClick={() => setConfirming(true)} loading={running}>
        {running ? 'Ingesting...' : 'Ingest Corpus'}
      </Button>

      {error && (
        <p role="alert" className="mt-4 rounded-md bg-red-500/10 px-3 py-2 font-sans text-sm text-red-400">
          {error}
        </p>
      )}
      {result && <IngestResult result={result} />}

      <ConfirmDialog
        open={confirming}
        title="Ingest this server file?"
        confirmLabel="Run ingest"
        onConfirm={runIngest}
        onCancel={() => setConfirming(false)}
      >
        <p>
          This reads <span className="font-mono">{path || '(no path)'}</span> on the API server
          {limit ? ` (first ${limit} rows)` : ''} and writes its records to the connected graph.
        </p>
      </ConfirmDialog>
    </section>
  );
}
