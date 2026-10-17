import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { maintenanceAPI } from '../api/client';
import StatusChip from '../components/StatusChip';
import ConfidenceBar from '../components/ConfidenceBar';
import { formatDate, dateValue } from '../utils/format';
import { formatDetail } from '../utils/diagnostics';
import { describeLoadError } from '../utils/loadError';

// What the engine means by each label (see backend/services/conflict_engine.py).
// These are descriptions of the classification, not a verdict on which record is right.
const LABEL_MEANING = {
  supersedes: 'The incoming record explicitly updates or closes the prior record.',
  partial_supersedes: 'The incoming record addresses the same issue but only partially resolves it.',
  contradicts: 'The records make mutually exclusive claims about the same part or event.',
};

const CONFLICT_LABELS = Object.keys(LABEL_MEANING);

// The history endpoint is keyed by the asset's UUID, not its tail number, and review
// queue rows only carry the tail. The UUID is resolved from the asset list; without it
// no link is shown (a link built from the tail would land on "Aircraft not found").
function historyLink(assetUuid, recordId) {
  return `/app/asset-history/${encodeURIComponent(assetUuid)}#${encodeURIComponent(recordId)}`;
}

function Finding({ label, rationale, confidence, considered, historyCount }) {
  return (
    <div className="border-t border-theme pt-6">
      <div className="flex justify-between items-start mb-3">
        <StatusChip status={label || 'no_conflict'} />
        <ConfidenceBar confidence={confidence} analysisState="needs_review" classification={label} candidateCount={considered} />
      </div>
      {LABEL_MEANING[label] && (
        <p className="font-sans text-xs text-secondary mb-3">{LABEL_MEANING[label]}</p>
      )}
      {!CONFLICT_LABELS.includes(label) && (
        <div className="bg-surface-dark/20 text-secondary text-xs p-2 rounded mb-3 border border-theme/50 font-sans">
          Low-confidence no-detection held back as a miss-safety net, not a conflict awaiting adjudication.
        </div>
      )}
      <p className="font-sans text-sm text-primary mb-3">
        {rationale || 'No rationale provided.'}
      </p>
      <p className="font-sans text-xs text-secondary italic">
        Examined {considered ?? '?'} of {historyCount ?? '?'} records on this asset.
      </p>
    </div>
  );
}

function NeedsReviewPanel({ analysisStatus }) {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [queueError, setQueueError] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [details, setDetails] = useState(null);
  const [detailsError, setDetailsError] = useState(null);
  const [detailsNonce, setDetailsNonce] = useState(0);
  const [historyCount, setHistoryCount] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [actionNote, setActionNote] = useState('');
  const [actionError, setActionError] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);
  const [toast, setToast] = useState(null);
  const [assetIdByTail, setAssetIdByTail] = useState({});

  useEffect(() => {
    let cancelled = false;
    maintenanceAPI.assets()
      .then(res => {
        if (cancelled) return;
        const map = {};
        (res.data ?? []).forEach(a => { map[a.tail_number] = a.id; });
        setAssetIdByTail(map);
      })
      .catch(() => {}); // links are optional; the queue works without them
    return () => { cancelled = true; };
  }, []);

  const fetchQueue = useCallback(() => {
    setLoading(true);
    setQueueError(null);
    return maintenanceAPI.reviewQueue()
      .then(res => {
        const rows = Array.isArray(res.data) ? res.data : [];
        const sorted = [...rows].sort((a, b) => {
          const isConfA = ['contradicts', 'partial_supersedes'].includes(a.classification_label);
          const isConfB = ['contradicts', 'partial_supersedes'].includes(b.classification_label);
          if (isConfA && !isConfB) return -1;
          if (!isConfA && isConfB) return 1;
          return dateValue(b.occurred_at) - dateValue(a.occurred_at);
        });
        setQueue(sorted);
        setCurrentIndex(0);
        if (sorted.length === 0) setDetails(null);
      })
      .catch(err => {
        console.error(err);
        setQueueError(describeLoadError(err));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  const activeRecord = queue[currentIndex];
  const activeId = activeRecord?.record_id;

  useEffect(() => {
    if (!activeRecord) return undefined;
    let cancelled = false;

    // Never leave the previous record's finding on screen while (or after) loading this one.
    setDetails(null);
    setDetailsError(null);
    setHistoryCount(null);
    setDetailsLoading(true);
    setActionError(null);
    setActionNote('');

    const tail = activeRecord.asset_key || activeRecord.asset_id;

    maintenanceAPI.getRecord(activeRecord.record_id)
      .then(async (recRes) => {
        const known = recRes.data?.history_size ?? activeRecord.history_size;
        let count = known;
        if (count === undefined || count === null) {
          count = await maintenanceAPI.assetHistory(tail)
            .then(h => h.data.count)
            .catch(() => '?');
        }
        if (cancelled) return;
        setDetails(recRes.data);
        setHistoryCount(count);
      })
      .catch(err => {
        if (cancelled) return;
        console.error(err);
        setDetailsError(describeLoadError(err));
      })
      .finally(() => {
        if (!cancelled) setDetailsLoading(false);
      });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId, detailsNonce]);

  // Accept/Reject change the record's status in the graph. The UI only reflects a
  // change after the server confirms it; on failure the record stays in the queue.
  const handleAction = async (action) => {
    if (!activeRecord || pendingAction) return;
    if (action === 'reject' && !actionNote.trim()) {
      setActionError('A note is required to reject a record.');
      return;
    }

    const rec = activeRecord;
    setPendingAction(action);
    setActionError(null);
    try {
      if (action === 'accept') {
        await maintenanceAPI.accept(rec.record_id, actionNote);
      } else {
        await maintenanceAPI.reject(rec.record_id, actionNote);
      }
      const next = queue.filter(r => r.record_id !== rec.record_id);
      setQueue(next);
      setCurrentIndex(i => Math.min(i, Math.max(0, next.length - 1)));
      setToast(`${action === 'accept' ? 'Accepted' : 'Rejected'} record ${rec.record_id}`);
    } catch (err) {
      console.error(err);
      setActionError(
        formatDetail(err.response?.data?.detail) ||
          `Could not ${action} this record. It is still in the queue; nothing was changed.`
      );
    } finally {
      setPendingAction(null);
    }
  };

  // Navigation only. Accepting or rejecting is never bound to a bare key press, so a
  // stray keystroke during a demo cannot change a record.
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'ArrowLeft') setCurrentIndex(i => Math.max(0, i - 1));
      if (e.key === 'ArrowRight') setCurrentIndex(i => Math.min(queue.length - 1, i + 1));
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [queue.length]);

  if (loading) {
    return <div className="p-6 text-secondary font-sans text-sm">Loading queue...</div>;
  }

  if (queueError) {
    return (
      <div className="flex h-full flex-col">
        <header className="border-b border-theme px-6 py-4">
          <h2 className="font-brand text-xl text-primary">Review Queue</h2>
          <p className="font-sans text-sm text-secondary">Records the system could not resolve confidently</p>
        </header>
        <div className="p-6">
          <div role="alert" className="halite-card border border-red-500/30 bg-red-500/5 p-4 max-w-xl">
            <p className="font-sans text-sm font-medium text-red-400">Could not load the review queue</p>
            <p className="mt-1 font-sans text-sm text-red-300">{queueError.message}</p>
            <p className="mt-1 font-sans text-xs text-secondary">
              This is a loading failure. It does not mean the queue is empty.
            </p>
            <button type="button" onClick={fetchQueue} className="halite-btn mt-3 text-sm">
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (queue.length === 0) {
    return (
      <div className="flex h-full flex-col">
        <header className="border-b border-theme px-6 py-4">
          <h2 className="font-brand text-xl text-primary">Review Queue</h2>
          <p className="font-sans text-sm text-secondary">Records the system could not resolve confidently</p>
        </header>
        {toast && (
          <div role="status" className="bg-accent text-black px-4 py-2 text-sm font-sans font-medium text-center">
            {toast}
          </div>
        )}
        <div className="p-6 font-sans text-secondary">
          {analysisStatus?.unscored > 0
            ? `Analysis has not run for ${analysisStatus.unscored} record${analysisStatus.unscored === 1 ? '' : 's'}.`
            : `${(analysisStatus?.scored ?? 0) + (analysisStatus?.reviewed ?? 0)} analysed, none need review.`}
        </div>
      </div>
    );
  }

  const tail = activeRecord.asset_key || activeRecord.tail_number;
  const assetUuid = assetIdByTail[tail];
  const stored = activeRecord.classification_label
    ? {
        label: activeRecord.classification_label,
        rationale: activeRecord.classification_rationale,
        confidence: activeRecord.confidence,
        considered: activeRecord.candidates_considered,
        historyCount: activeRecord.history_size,
      }
    : null;

  return (
    <div className="flex h-full flex-col">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-theme px-6 py-4">
        <div>
          <h2 className="font-brand text-xl text-primary flex items-center gap-3">
            Review Queue
            <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-accent/20 px-1.5 text-xs font-semibold text-accent ring-1 ring-accent/40">
              {queue.length}
            </span>
          </h2>
          <p className="font-sans text-sm text-secondary">Records the system could not resolve confidently</p>
        </div>
        <div className="text-xs text-secondary font-sans">
          Keyboard: <kbd className="bg-surface-dark/10 px-1 rounded">←/→</kbd> navigate between records
        </div>
      </header>

      {toast && (
        <div role="status" className="bg-accent text-black px-4 py-2 text-sm font-sans font-medium text-center">
          {toast}
        </div>
      )}

      {actionError && (
        <div role="alert" className="bg-red-500/10 text-red-500 border-b border-red-500/20 px-6 py-2 text-sm font-sans">
          {actionError}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid gap-6 lg:grid-cols-[1fr_1.15fr] h-full">

          {/* LEFT: Incoming Record */}
          <div className="halite-card p-6 flex flex-col">
            <span className="eyebrow mb-4">INCOMING RECORD</span>
            <div className="space-y-4 font-sans text-sm flex-1">
              <div><span className="text-secondary">Record ID:</span> <span className="font-mono text-primary">{activeRecord.record_id}</span></div>
              <div><span className="text-secondary">Tail Number:</span> <span className="text-primary">{tail}</span></div>
              <div><span className="text-secondary">Date:</span> <span className="text-primary">{formatDate(activeRecord.occurred_at)}</span></div>

              <div className="bg-surface-dark/5 p-3 rounded border border-theme">
                <div className="font-semibold text-primary mb-1">{activeRecord.part_name}</div>
                <div className="text-secondary text-xs space-x-3 mb-2">
                  {activeRecord.part_condition && <span>Condition: {activeRecord.part_condition}</span>}
                  {activeRecord.part_location && <span>Location: {activeRecord.part_location}</span>}
                  {activeRecord.jasc_code && <span>JASC: {activeRecord.jasc_code}</span>}
                </div>
                <div className="text-primary whitespace-pre-wrap mt-3">{activeRecord.text}</div>
              </div>

              {assetUuid && (
                <Link
                  to={historyLink(assetUuid, activeRecord.record_id)}
                  className="inline-block text-xs text-accent hover:underline"
                >
                  Open in asset history →
                </Link>
              )}
            </div>

            <div className="mt-6 flex justify-between items-center pt-4 border-t border-theme">
              <span className="text-xs text-secondary">Record {currentIndex + 1} of {queue.length}</span>
              <div className="flex gap-2">
                <button onClick={() => setCurrentIndex(i => Math.max(0, i - 1))} disabled={currentIndex === 0} className="halite-btn-ghost px-2 py-1 text-xs disabled:opacity-50">← Prev</button>
                <button onClick={() => setCurrentIndex(i => Math.min(queue.length - 1, i + 1))} disabled={currentIndex === queue.length - 1} className="halite-btn-ghost px-2 py-1 text-xs disabled:opacity-50">Next →</button>
              </div>
            </div>
          </div>

          {/* RIGHT: Retrieved History & Finding */}
          <div className="halite-card p-6 flex flex-col relative overflow-hidden">
            {detailsLoading ? (
              <div className="flex-1 flex items-center justify-center text-secondary text-sm">Loading finding details...</div>
            ) : details ? (
              <div className="flex-1 min-h-0 overflow-y-auto space-y-6 pr-1">
                {details.best_prior ? (
                  <div>
                    <span className="eyebrow mb-4 block">RETRIEVED PRIOR RECORD</span>
                    <div className="space-y-4 font-sans text-sm">
                      <div><span className="text-secondary">Record ID:</span> <span className="font-mono text-primary">{details.best_prior.record_id}</span></div>
                      <div><span className="text-secondary">Date:</span> <span className="text-primary">{formatDate(details.best_prior.occurred_at)}</span></div>

                      <div className="bg-surface-dark/5 p-3 rounded border border-theme">
                        <div className="font-semibold text-primary mb-1">{details.best_prior.part_name}</div>
                        <div className="text-secondary text-xs space-x-3 mb-2">
                          {details.best_prior.part_condition && <span>Condition: {details.best_prior.part_condition}</span>}
                          {details.best_prior.part_location && <span>Location: {details.best_prior.part_location}</span>}
                        </div>
                        <div className="text-primary whitespace-pre-wrap mt-3">{details.best_prior.text}</div>
                      </div>

                      {assetUuid && details.best_prior.record_id && (
                        <Link
                          to={historyLink(assetUuid, details.best_prior.record_id)}
                          className="inline-block text-xs text-accent hover:underline"
                        >
                          Open in asset history →
                        </Link>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-secondary font-sans text-sm mb-6">No relevant prior record retrieved.</div>
                )}

                <Finding
                  label={details.classification?.label}
                  rationale={details.classification?.rationale}
                  confidence={details.confidence}
                  considered={details.candidates_considered}
                  historyCount={historyCount}
                />
              </div>
            ) : (
              <div className="flex-1 min-h-0 overflow-y-auto space-y-6 pr-1">
                <div role="alert" className="rounded border border-amber-500/30 bg-amber-500/5 p-3">
                  <p className="font-sans text-sm font-medium text-amber-400">Finding details unavailable</p>
                  <p className="mt-1 font-sans text-xs text-primary">
                    {detailsError?.message || 'The prior record could not be retrieved.'}
                  </p>
                  <button
                    type="button"
                    onClick={() => setDetailsNonce(n => n + 1)}
                    className="halite-btn mt-2 text-xs"
                  >
                    Retry
                  </button>
                </div>
                {stored && (
                  <div>
                    <span className="eyebrow mb-1 block">STORED FINDING (recorded when this record was ingested)</span>
                    <Finding {...stored} />
                  </div>
                )}
              </div>
            )}

            {!detailsLoading && (
              <div className="mt-6 pt-4 border-t border-theme sticky bottom-0 bg-surface-dark/80 backdrop-blur pb-2">
                <textarea
                  className="halite-input w-full mb-3 text-sm"
                  rows={2}
                  placeholder="Add a review note (required for rejection)..."
                  value={actionNote}
                  onChange={(e) => setActionNote(e.target.value)}
                />
                <div className="flex gap-3">
                  <button
                    onClick={() => handleAction('accept')}
                    disabled={Boolean(pendingAction)}
                    className="halite-btn-primary flex-1 py-2 text-sm disabled:opacity-60"
                  >
                    {pendingAction === 'accept' ? 'Accepting…' : 'Accept'}
                  </button>
                  <button
                    onClick={() => handleAction('reject')}
                    disabled={Boolean(pendingAction)}
                    className="halite-btn-ghost flex-1 py-2 text-sm disabled:opacity-60"
                  >
                    {pendingAction === 'reject' ? 'Rejecting…' : 'Reject'}
                  </button>
                </div>
                <p className="mt-2 font-sans text-[11px] text-secondary">
                  Accept marks this record as reviewed and accepted. Reject marks it rejected and stores your note.
                  Neither action deletes the record.
                </p>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}


function CorrectionsPanel() {
  const [assets, setAssets] = useState([]);
  const [assetId, setAssetId] = useState('');
  const [changed, setChanged] = useState('');
  const [data, setData] = useState({ items: [], total: 0, next: null, summary: {} });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    maintenanceAPI.assets().then(({ data: rows }) => setAssets(rows || [])).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const params = { limit: 50, offset: 0 };
    if (assetId) params.asset_id = assetId;
    if (changed) params.component_changed = changed === 'yes';
    maintenanceAPI.corrections(params)
      .then(({ data: response }) => { if (!cancelled) setData(response); })
      .catch((err) => { if (!cancelled) setError(describeLoadError(err)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [assetId, changed]);

  const loadMore = async () => {
    const params = { limit: 50, offset: data.next };
    if (assetId) params.asset_id = assetId;
    if (changed) params.component_changed = changed === 'yes';
    const { data: response } = await maintenanceAPI.corrections(params);
    setData((current) => ({ ...response, items: [...current.items, ...response.items] }));
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex flex-wrap gap-3">
        <select aria-label="Corrections aircraft" className="halite-input" value={assetId} onChange={(e) => setAssetId(e.target.value)}>
          <option value="">All aircraft</option>
          {assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.tail_number}</option>)}
        </select>
        <select aria-label="Component change" className="halite-input" value={changed} onChange={(e) => setChanged(e.target.value)}>
          <option value="">All corrections</option>
          <option value="yes">Component changed</option>
          <option value="no">Same component</option>
        </select>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="halite-card p-4"><p className="text-xs text-secondary">Detected corrections</p><p className="text-2xl text-primary">{data.summary?.total_corrections ?? 0}</p></div>
        <div className="halite-card p-4"><p className="text-xs text-secondary">Component changed</p><p className="text-2xl text-primary">{data.summary?.component_changed ?? 0}</p></div>
        <div className="halite-card p-4"><p className="text-xs text-secondary">Component-change rate</p><p className="text-2xl text-primary">{data.summary?.component_changed_pct ?? 0}%</p></div>
      </div>
      {loading ? <p className="text-secondary">Loading detected corrections…</p> : error ? <p role="alert" className="text-red-400">{error.message}</p> : (
        <div className="halite-card overflow-hidden">
          <div className="grid grid-cols-[6rem_1fr_3rem_1fr_10rem] gap-3 border-b border-theme px-4 py-3 text-xs text-secondary">
            <span>Aircraft</span><span>Older finding</span><span></span><span>Newer finding</span><span>Review</span>
          </div>
          {data.items.length === 0 ? <p className="p-4 text-sm text-secondary">No detected corrections match these filters.</p> : data.items.map((row) => (
            <div key={`${row.newer_record.id}-${row.older_record.id}`} className="grid grid-cols-[6rem_1fr_3rem_1fr_10rem] gap-3 border-b border-theme px-4 py-4 text-sm">
              <span className="text-primary">{row.aircraft.tail_number}</span>
              <Link className="text-primary hover:underline" to={historyLink(row.aircraft.id, row.older_record.id)}>
                <span className="block font-mono text-xs">{row.older_record.id}</span>{row.older_record.part_name}
              </Link>
              <span className={row.component_changed ? 'text-amber-500' : 'text-secondary'}>→</span>
              <Link className="text-primary hover:underline" to={historyLink(row.aircraft.id, row.newer_record.id)}>
                <span className="block font-mono text-xs">{row.newer_record.id}</span>{row.newer_record.part_name}
                {row.component_changed && <span className="mt-1 block text-xs text-amber-500">{row.older_record.part_name} → {row.newer_record.part_name}</span>}
                <span className="mt-1 block text-xs text-secondary">{row.rationale}</span>
              </Link>
              <div><StatusChip status={row.review_status} analysisState={row.review_status} /><p className="mt-1 text-xs text-secondary">{row.classification_label}</p></div>
            </div>
          ))}
        </div>
      )}
      {data.next != null && <button className="halite-btn" onClick={loadMore}>Load more</button>}
      <p className="text-xs text-secondary">Model-assisted detection; recall on the ground-truth set was 0.66 (docs/evaluation_results.md). Results are not exhaustive.</p>
    </div>
  );
}


export default function ReviewQueue() {
  const [tab, setTab] = useState('review');
  const [analysisStatus, setAnalysisStatus] = useState(null);

  useEffect(() => {
    maintenanceAPI.analysisStatus().then(({ data }) => setAnalysisStatus(data)).catch(() => setAnalysisStatus(null));
  }, []);

  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-2 border-b border-theme px-6 pt-3">
        <button className={`px-4 py-2 text-sm ${tab === 'review' ? 'border-b-2 border-accent text-primary' : 'text-secondary'}`} onClick={() => setTab('review')}>Needs review</button>
        <button className={`px-4 py-2 text-sm ${tab === 'corrections' ? 'border-b-2 border-accent text-primary' : 'text-secondary'}`} onClick={() => setTab('corrections')}>Detected corrections</button>
      </div>
      <div className="min-h-0 flex-1">{tab === 'review' ? <NeedsReviewPanel analysisStatus={analysisStatus} /> : <CorrectionsPanel />}</div>
    </div>
  );
}
