import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useLocation, Link } from 'react-router-dom';
import { maintenanceAPI } from '../api/client';
import StatusChip from '../components/StatusChip';
import ConfidenceBar from '../components/ConfidenceBar';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { formatDate, dateValue } from '../utils/format';
import { describeLoadError } from '../utils/loadError';

// A record deep link looks like /app/asset-history/<asset>#<record_id>. The page
// scrolls to that record and marks it, so "open the cited record" lands on the
// record itself and not just somewhere in a long timeline.
function recordIdFromHash(hash) {
  if (!hash || hash.length < 2) return '';
  try {
    return decodeURIComponent(hash.slice(1));
  } catch {
    return hash.slice(1);
  }
}

function BackLink() {
  return (
    <Link to="/app/assets" className="inline-flex items-center gap-2 text-accent hover:underline mb-4 font-sans text-sm font-medium">
      <ArrowLeftIcon className="h-4 w-4" /> Back to Assets
    </Link>
  );
}

export default function AssetHistory() {
  const { assetId } = useParams();
  const { hash } = useLocation();
  const linkedRecordId = recordIdFromHash(hash);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    maintenanceAPI.assetHistory(assetId)
      .then(res => { if (!cancelled) setData(res.data); })
      .catch(err => {
        if (cancelled) return;
        console.error(err);
        setData(null);
        setError(describeLoadError(err));
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [assetId, attempt]);

  // Oldest first; records without a usable date go last instead of scrambling the order.
  const records = useMemo(
    () => [...(data?.records ?? [])].sort((a, b) => dateValue(a.occurred_at) - dateValue(b.occurred_at)),
    [data]
  );

  const linkedFound = Boolean(linkedRecordId) && records.some(r => r.record_id === linkedRecordId);

  // Wait for loading to finish: while the skeleton is showing the cards are not in the DOM yet.
  useEffect(() => {
    if (loading || !linkedFound) return;
    const el = document.getElementById(`record-${linkedRecordId}`);
    if (el && typeof el.scrollIntoView === 'function') {
      // Instant jump: on a long history a smooth scroll is slow and can be caught mid-animation.
      el.scrollIntoView({ block: 'center' });
    }
  }, [loading, linkedFound, linkedRecordId]);

  if (loading) {
    return (
      <div className="flex h-full flex-col p-6" role="status" aria-label="Loading service history">
        <div className="h-8 w-32 bg-surface-dark/10 animate-pulse rounded mb-4"></div>
        <div className="h-24 w-full bg-surface-dark/10 animate-pulse rounded mb-4 halite-card"></div>
        <div className="h-24 w-full bg-surface-dark/10 animate-pulse rounded mb-4 halite-card"></div>
        <div className="h-24 w-full bg-surface-dark/10 animate-pulse rounded mb-4 halite-card"></div>
      </div>
    );
  }

  if (error) {
    const notFound = error.kind === 'not-found';
    return (
      <div className="flex h-full flex-col p-6">
        <BackLink />
        <div role="alert" className="halite-card border border-red-500/30 bg-red-500/5 p-4 max-w-xl">
          <p className="font-sans text-sm font-medium text-red-400">
            {notFound ? 'Aircraft not found' : 'Could not load service history'}
          </p>
          <p className="mt-1 font-sans text-sm text-red-300">
            {notFound
              ? 'No aircraft with this identifier exists in the loaded corpus. Go back and pick one from the list.'
              : error.message}
          </p>
          {!notFound && (
            <button type="button" onClick={() => setAttempt(n => n + 1)} className="halite-btn mt-3 text-sm">
              Try again
            </button>
          )}
        </div>
      </div>
    );
  }

  if (records.length === 0) {
    return (
      <div className="flex h-full flex-col p-6">
        <BackLink />
        <p className="font-sans text-secondary">No records for this asset yet.</p>
      </div>
    );
  }

  const tailNumber = records[0]?.asset_key || assetId;

  return (
    <div className="flex h-full flex-col">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-theme px-6 py-4">
        <div>
          <Link to="/app/assets" className="inline-flex items-center gap-2 text-accent hover:underline mb-2 font-sans text-sm font-medium">
            <ArrowLeftIcon className="h-4 w-4" /> Back to Assets
          </Link>
          <h2 className="font-brand text-xl text-primary">{tailNumber}</h2>
          <p className="font-sans text-sm text-secondary">{data.count ?? records.length} service records</p>
        </div>
      </header>

      {linkedRecordId && !linkedFound && (
        <div role="status" className="border-b border-amber-500/20 bg-amber-500/5 px-6 py-2 font-sans text-sm text-amber-400">
          Record <span className="font-mono">{linkedRecordId}</span> is not part of this aircraft&apos;s history.
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6 relative">
        <div className="absolute left-10 top-6 bottom-6 w-[2px] bg-accent/20 hidden sm:block"></div>
        <div className="space-y-6">
          {records.map((rec) => {
            const isSuperseded = rec.status === 'superseded';
            const isLinked = linkedFound && rec.record_id === linkedRecordId;
            return (
              <div key={rec.id || rec.record_id} className="relative flex items-start gap-4 sm:pl-12">
                <div className="absolute left-9 -ml-[5px] mt-1.5 h-[10px] w-[10px] rounded-full bg-accent ring-4 ring-page hidden sm:block"></div>
                <div
                  id={`record-${rec.record_id}`}
                  data-linked={isLinked ? 'true' : undefined}
                  className={`halite-card p-4 flex-1 ${isSuperseded ? 'opacity-50' : ''} ${
                    isLinked ? 'ring-2 ring-accent' : ''
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="eyebrow">{formatDate(rec.occurred_at)}</span>
                    <div className="flex items-center gap-2">
                      {isLinked && (
                        <span className="rounded-full bg-accent px-2 py-0.5 text-xs font-medium text-black">
                          Linked record
                        </span>
                      )}
                      <StatusChip status={rec.status} analysisState={rec.analysis_state} legacyPlaceholder={rec.legacy_placeholder} />
                    </div>
                  </div>

                  {isSuperseded && rec.corrected_by && (
                    <div className="mb-3 rounded border border-accent/20 bg-accent/10 p-2 font-sans text-sm text-accent">
                      Corrected by{' '}
                      <Link className="font-mono underline" to={`#${encodeURIComponent(rec.corrected_by.record_id)}`}>
                        {rec.corrected_by.record_id}
                      </Link>
                      {` — component changed ${rec.part_name || 'Unknown'} → ${rec.corrected_by.part_name || 'Unknown'}`}
                    </div>
                  )}

                  <h4 className="font-sans font-semibold text-primary mb-1">
                    {rec.part_name} {rec.part_condition ? `- ${rec.part_condition}` : ''} {rec.part_location ? `(${rec.part_location})` : ''}
                  </h4>
                  <p className="font-sans text-sm text-secondary whitespace-pre-wrap">
                    {rec.text}
                  </p>
                  {/* Conflict-engine and ingest fields exactly as the backend returns them. */}
                  {(rec.analysis_state || rec.confidence != null || rec.jasc_code || rec.source) && (
                    <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 font-sans text-xs text-secondary">
                      <ConfidenceBar confidence={rec.confidence} analysisState={rec.analysis_state} classification={rec.classification_label} candidateCount={rec.candidate_count ?? rec.candidates_considered} status={rec.status} legacyPlaceholder={rec.legacy_placeholder} analysisMethod={rec.analysis_method} analysisPasses={rec.analysis_passes} voteAgreement={rec.analysis_vote_agreement} />
                      {rec.jasc_code && <span>JASC {rec.jasc_code}</span>}
                      {rec.source && <span>Source: {rec.source}</span>}
                    </div>
                  )}
                  <div className="mt-3 font-sans text-xs text-[#888888] font-mono">
                    ID: {rec.record_id}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
