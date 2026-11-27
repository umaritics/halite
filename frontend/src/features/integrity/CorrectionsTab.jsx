import { Button, ErrorCard, Skeleton } from '../../components/ui';
import CorrectionsTable from './CorrectionsTable';
import useCorrections from './useCorrections';

function SummaryCard({ label, value }) {
  return (
    <div className="halite-card p-4">
      <p className="text-xs text-secondary">{label}</p>
      <p className="text-2xl text-primary">{value}</p>
    </div>
  );
}

function Filters({ corrections }) {
  const { assets, assetId, setAssetId, changed, setChanged } = corrections;
  return (
    <div className="flex flex-wrap gap-3">
      <select
        aria-label="Corrections aircraft"
        className="halite-input"
        value={assetId}
        onChange={(event) => setAssetId(event.target.value)}
      >
        <option value="">All aircraft</option>
        {assets.map((asset) => (
          <option key={asset.id} value={asset.id}>{asset.tail_number}</option>
        ))}
      </select>
      <select
        aria-label="Component change"
        className="halite-input"
        value={changed}
        onChange={(event) => setChanged(event.target.value)}
      >
        <option value="">All corrections</option>
        <option value="yes">Component changed</option>
        <option value="no">Same component</option>
      </select>
    </div>
  );
}

function Results({ corrections }) {
  const { data, loading, error } = corrections;
  if (loading) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-secondary">Loading detected corrections…</p>
        <Skeleton variant="card" lines={4} />
      </div>
    );
  }
  if (error) return <ErrorCard message={error.message} />;
  return <CorrectionsTable items={data.items} />;
}

export default function CorrectionsTab() {
  const corrections = useCorrections();
  const { data, loading, error, loadMore, loadingMore, moreError } = corrections;
  const summary = data.summary || {};

  return (
    <div className="space-y-5">
      <Filters corrections={corrections} />
      <div className="grid gap-3 sm:grid-cols-3">
        <SummaryCard label="Detected corrections" value={summary.total_corrections ?? 0} />
        <SummaryCard label="Component changed" value={summary.component_changed ?? 0} />
        <SummaryCard label="Component-change rate" value={`${summary.component_changed_pct ?? 0}%`} />
      </div>
      <Results corrections={corrections} />
      {moreError && (
        <ErrorCard
          message={`Could not load more corrections. ${moreError.message}`}
          onRetry={loadMore}
        />
      )}
      {!loading && !error && data.next != null && !moreError && (
        <Button variant="outline" onClick={loadMore} loading={loadingMore}>
          Load more
        </Button>
      )}
      <p className="text-xs text-secondary">
        Linked by citation or proposed by the model. Results are not exhaustive.
      </p>
    </div>
  );
}
