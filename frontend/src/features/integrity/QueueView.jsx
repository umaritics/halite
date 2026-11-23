import { useEffect } from 'react';
import { EmptyState, ErrorCard, Skeleton } from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import DecisionBar from './DecisionBar';
import { FindingPanel, IncomingRecordPanel } from './RecordPanels';
import useRecordDetails from './useRecordDetails';
import useReviewDecision from './useReviewDecision';

function emptyMessage(analysisStatus) {
  if (analysisStatus?.unscored > 0) {
    const count = analysisStatus.unscored;
    return `Analysis has not run for ${count} record${count === 1 ? '' : 's'}.`;
  }
  const analysed = (analysisStatus?.scored ?? 0) + (analysisStatus?.reviewed ?? 0);
  return `${analysed} analysed, none need review.`;
}

function Toast({ message }) {
  if (!message) return null;
  return (
    <div
      role="status"
      className="mb-4 rounded bg-accent px-4 py-2 text-center font-sans text-sm font-medium text-black"
    >
      {message}
    </div>
  );
}

function storedFinding(record) {
  if (!record.classification_label) return null;
  return {
    label: record.classification_label,
    rationale: record.classification_rationale,
    confidence: record.confidence,
    considered: record.candidates_considered,
    historyCount: record.history_size,
  };
}

// Left/right arrow keys move between records. Accepting or rejecting is never bound
// to a bare key press, so a stray keystroke cannot change a record.
function useArrowKeys(onPrev, onNext) {
  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
      if (event.key === 'ArrowLeft') onPrev();
      if (event.key === 'ArrowRight') onNext();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onPrev, onNext]);
}

export default function QueueView({ review, analysisStatus, assets }) {
  const { hasRole, user } = useAuth();
  const { queue, loading, error, reload, remove, currentIndex, activeRecord, prev, next } = review;
  const decision = useReviewDecision(activeRecord, remove);
  const finding = useRecordDetails(activeRecord, assets.whenLoaded);
  useArrowKeys(prev, next);

  if (loading) {
    return (
      <div className="space-y-3">
        <p className="font-sans text-sm text-secondary">Loading queue...</p>
        <Skeleton variant="card" lines={4} />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorCard
        onRetry={reload}
        message={
          <>
            <span className="block font-medium">Could not load the review queue</span>
            <span className="mt-1 block text-sm">{error.message}</span>
            <span className="mt-1 block text-xs text-secondary">
              This is a loading failure. It does not mean the queue is empty.
            </span>
          </>
        }
      />
    );
  }

  if (queue.length === 0) {
    return (
      <>
        <Toast message={decision.toast} />
        <EmptyState title="Nothing to review" body={emptyMessage(analysisStatus)} />
      </>
    );
  }

  const tail = activeRecord.asset_key || activeRecord.tail_number;
  const assetUuid = assets.idByTail[tail];

  return (
    <div>
      <div className="mb-4 font-sans text-xs text-secondary">
        Keyboard: <kbd className="rounded bg-black/10 px-1 dark:bg-white/10">←/→</kbd>{' '}
        navigate between records
      </div>
      <Toast message={decision.toast} />
      {decision.error && (
        <div
          role="alert"
          className="mb-4 rounded border border-red-500/30 bg-red-500/10 px-4 py-2 font-sans text-sm text-red-700 dark:text-red-400"
        >
          {decision.error}
        </div>
      )}
      <div className="grid gap-6 lg:grid-cols-[1fr_1.15fr]">
        <IncomingRecordPanel
          record={activeRecord}
          tail={tail}
          assetUuid={assetUuid}
          position={currentIndex + 1}
          total={queue.length}
          onPrev={prev}
          onNext={next}
        />
        <FindingPanel
          state={finding}
          stored={storedFinding(activeRecord)}
          assetUuid={assetUuid}
          onRetry={finding.retry}
          footer={
            <DecisionBar
              canAdjudicate={hasRole('supervisor', 'admin')}
              role={user?.role}
              decision={decision}
            />
          }
        />
      </div>
    </div>
  );
}
