import { Button, ErrorCard, Skeleton } from '../../components/ui';
import Finding from './Finding';
import RecordCard from './RecordCard';

// Left side: the record waiting for a decision, with Prev/Next.
export function IncomingRecordPanel({ record, tail, assetUuid, position, total, onPrev, onNext }) {
  return (
    <div className="halite-card flex flex-col p-6">
      <span className="eyebrow mb-4">INCOMING RECORD</span>
      <div className="flex-1">
        <RecordCard record={record} tail={tail} assetUuid={assetUuid} showJasc />
      </div>
      <div className="mt-6 flex items-center justify-between border-t border-theme pt-4">
        <span className="text-xs text-secondary">Record {position} of {total}</span>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={onPrev} disabled={position === 1}>
            ← Prev
          </Button>
          <Button variant="ghost" size="sm" onClick={onNext} disabled={position === total}>
            Next →
          </Button>
        </div>
      </div>
    </div>
  );
}

function LoadedFinding({ details, historyCount, assetUuid }) {
  return (
    <div className="min-h-0 flex-1 space-y-6 overflow-y-auto pr-1">
      {details.best_prior ? (
        <div>
          <span className="eyebrow mb-4 block">RETRIEVED PRIOR RECORD</span>
          <RecordCard record={details.best_prior} assetUuid={assetUuid} />
        </div>
      ) : (
        <div className="mb-6 font-sans text-sm text-secondary">
          No relevant prior record retrieved.
        </div>
      )}
      <Finding
        label={details.classification?.label}
        rationale={details.classification?.rationale}
        confidence={details.confidence}
        considered={details.candidates_considered}
        historyCount={historyCount}
      />
    </div>
  );
}

function FailedFinding({ error, stored, onRetry }) {
  return (
    <div className="min-h-0 flex-1 space-y-6 overflow-y-auto pr-1">
      <ErrorCard
        retryLabel="Retry"
        onRetry={onRetry}
        message={
          <>
            <span className="block font-medium">Finding details unavailable</span>
            <span className="mt-1 block text-xs">
              {error?.message || 'The prior record could not be retrieved.'}
            </span>
          </>
        }
      />
      {stored && (
        <div>
          <span className="eyebrow mb-1 block">
            STORED FINDING (recorded when this record was ingested)
          </span>
          <Finding {...stored} />
        </div>
      )}
    </div>
  );
}

// Right side: the retrieved prior record and the engine's finding. `footer` holds
// the decision bar.
export function FindingPanel({ state, stored, assetUuid, onRetry, footer }) {
  const { details, error, loading, historyCount } = state;
  let body;
  if (loading) {
    body = (
      <div className="flex-1 space-y-3">
        <p className="text-sm text-secondary">Loading finding details...</p>
        <Skeleton lines={4} />
      </div>
    );
  } else if (details) {
    body = <LoadedFinding details={details} historyCount={historyCount} assetUuid={assetUuid} />;
  } else {
    body = <FailedFinding error={error} stored={stored} onRetry={onRetry} />;
  }

  return (
    <div className="halite-card relative flex flex-col overflow-hidden p-6">
      {body}
      {!loading && footer}
    </div>
  );
}
