import React, { useEffect, useState, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { maintenanceAPI } from '../api/client';
import StatusChip from '../components/StatusChip';
import ConfidenceBar from '../components/ConfidenceBar';
import { formatDate, dateValue } from '../utils/format';
import { describeLoadError } from '../utils/loadError';

const STATUS_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'unscored', label: 'Unscored' },
  { id: 'auto_accepted', label: 'Auto Accepted' },
  { id: 'needs_review', label: 'Needs Review' },
  { id: 'accepted', label: 'Accepted' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'superseded', label: 'Superseded' },
];

// Newest first; records with no usable date go last instead of scrambling the order.
function newestFirst(a, b) {
  const ta = dateValue(a.occurred_at);
  const tb = dateValue(b.occurred_at);
  if (ta === tb) return 0;
  if (ta === Number.POSITIVE_INFINITY) return 1;
  if (tb === Number.POSITIVE_INFINITY) return -1;
  return tb - ta;
}

// The aircraft shown when none is chosen: the one with the most records.
function defaultAsset(assets) {
  return assets.reduce((best, a) => ((a.record_count ?? 0) > (best?.record_count ?? -1) ? a : best), null);
}

// Performance note (docs/mid1/10_perf_assets_api_handoff.md): this page used to fetch the
// history of every aircraft on load (~119 requests). It now loads the aircraft list and the
// history of ONE aircraft, so first load is 2 requests and switching aircraft is 1.
export default function ServiceRecords() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedAssetId = searchParams.get('asset');

  const [assets, setAssets] = useState([]);
  const [assetsLoading, setAssetsLoading] = useState(true);
  const [assetsError, setAssetsError] = useState(null);
  const [assetsAttempt, setAssetsAttempt] = useState(0);

  const [records, setRecords] = useState([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordsError, setRecordsError] = useState(null);
  const [recordsAttempt, setRecordsAttempt] = useState(0);

  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const itemsPerPage = 50;

  useEffect(() => {
    let cancelled = false;
    setAssetsLoading(true);
    setAssetsError(null);
    maintenanceAPI.assets()
      .then(res => { if (!cancelled) setAssets(Array.isArray(res.data) ? res.data : []); })
      .catch(err => {
        if (cancelled) return;
        console.error(err);
        setAssetsError(describeLoadError(err));
      })
      .finally(() => { if (!cancelled) setAssetsLoading(false); });
    return () => { cancelled = true; };
  }, [assetsAttempt]);

  const requestedAsset = assets.find(a => a.id === requestedAssetId);
  const selectedAsset = requestedAsset || defaultAsset(assets);
  const selectedId = selectedAsset?.id;
  const requestedMissing = Boolean(requestedAssetId) && !assetsLoading && !assetsError && !requestedAsset;

  useEffect(() => {
    if (!selectedId) {
      setRecords([]);
      return undefined;
    }
    let cancelled = false;
    setRecordsLoading(true);
    setRecordsError(null);
    setRecords([]);
    maintenanceAPI.assetHistory(selectedId)
      .then(res => {
        if (cancelled) return;
        const list = res.data?.records ?? [];
        const assetId = res.data?.asset_id || selectedId;
        setRecords(
          list
            .map(rec => ({ ...rec, tail_number: rec.asset_key || selectedAsset.tail_number, asset_id: assetId }))
            .sort(newestFirst)
        );
      })
      .catch(err => {
        if (cancelled) return;
        console.error(err);
        setRecordsError(describeLoadError(err));
      })
      .finally(() => { if (!cancelled) setRecordsLoading(false); });
    return () => { cancelled = true; };
    // selectedAsset is derived from selectedId + assets; refetch only when the id or retry changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, recordsAttempt]);

  const chooseAsset = (id) => {
    setSearchParams({ asset: id }, { replace: true });
    setPage(1);
  };

  const filtered = useMemo(() => {
    return records.filter(r => {
      const matchStatus = filter === 'all' || r.status === filter;
      const term = search.toLowerCase();
      const matchSearch = (r.text || '').toLowerCase().includes(term) ||
                          (r.part_name || '').toLowerCase().includes(term);
      return matchStatus && matchSearch;
    });
  }, [records, filter, search]);

  const totalPages = Math.ceil(filtered.length / itemsPerPage);
  const paginated = filtered.slice((page - 1) * itemsPerPage, page * itemsPerPage);

  return (
    <div className="flex h-full flex-col">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-theme px-6 py-4">
        <div>
          <h2 className="font-brand text-xl text-primary">Service Records</h2>
          <p className="font-sans text-sm text-secondary">
            Maintenance records for one aircraft at a time
            {selectedAsset ? ` — ${selectedAsset.tail_number}` : ''}
          </p>
        </div>
        {assets.length > 0 && (
          <label className="flex items-center gap-2 font-sans text-sm text-secondary">
            <span className="eyebrow">Aircraft</span>
            <select
              aria-label="Aircraft"
              className="halite-input"
              value={selectedId ?? ''}
              onChange={e => chooseAsset(e.target.value)}
            >
              {assets.map(a => (
                <option key={a.id} value={a.id}>
                  {a.tail_number}{a.record_count !== undefined ? ` (${a.record_count})` : ''}
                </option>
              ))}
            </select>
          </label>
        )}
      </header>

      <div className="flex flex-wrap items-center gap-3 border-b border-theme px-6 py-3">
        <input
          type="text"
          placeholder="Search discrepancy or part..."
          className="halite-input w-full sm:w-[320px]"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
        />
        <div className="flex gap-2 bg-surface-dark/5 p-1 rounded-md border border-theme">
          {STATUS_FILTERS.map(f => (
            <button
              key={f.id}
              onClick={() => { setFilter(f.id); setPage(1); }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                filter === f.id ? 'bg-accent text-black' : 'text-secondary hover:text-primary'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {requestedMissing && (
        <div role="status" className="border-b border-amber-500/20 bg-amber-500/5 px-6 py-2 font-sans text-sm text-amber-400">
          The aircraft in the link was not found. Showing {selectedAsset?.tail_number ?? 'the first aircraft'} instead.
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6">
        {assetsLoading ? (
          <div className="text-secondary text-sm">Loading aircraft...</div>
        ) : assetsError ? (
          <div role="alert" className="halite-card border border-red-500/30 bg-red-500/5 p-4 max-w-xl">
            <p className="font-sans text-sm font-medium text-red-400">Could not load the aircraft list</p>
            <p className="mt-1 font-sans text-sm text-red-300">{assetsError.message}</p>
            <button type="button" onClick={() => setAssetsAttempt(n => n + 1)} className="halite-btn mt-3 text-sm">
              Try again
            </button>
          </div>
        ) : assets.length === 0 ? (
          <div className="text-secondary text-sm">No aircraft in the loaded corpus.</div>
        ) : recordsLoading ? (
          <div className="text-secondary text-sm">Loading records...</div>
        ) : recordsError ? (
          <div role="alert" className="halite-card border border-red-500/30 bg-red-500/5 p-4 max-w-xl">
            <p className="font-sans text-sm font-medium text-red-400">Could not load records for this aircraft</p>
            <p className="mt-1 font-sans text-sm text-red-300">{recordsError.message}</p>
            <button type="button" onClick={() => setRecordsAttempt(n => n + 1)} className="halite-btn mt-3 text-sm">
              Try again
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="halite-card overflow-hidden">
              <div className="flex items-center gap-4 bg-surface-dark/5 px-4 py-3 border-b border-theme font-sans text-xs font-medium text-secondary">
                <div className="w-32">Record ID</div>
                <div className="w-24">Tail No</div>
                <div className="w-28">Date</div>
                <div className="flex-1">Part Name</div>
                <div className="w-32">Confidence</div>
                <div className="w-32">Status</div>
              </div>
              {paginated.length === 0 ? (
                <div className="p-4 text-sm text-secondary">
                  {records.length === 0 ? 'No records for this aircraft.' : 'No records match the current filter.'}
                </div>
              ) : (
                paginated.map(rec => (
                  <Link
                    key={rec.id || rec.record_id}
                    to={`/app/asset-history/${rec.asset_id}#${rec.record_id}`}
                    className="flex items-center gap-4 px-4 py-3 border-b border-theme hover:bg-surface-dark/5 transition-colors font-sans text-sm"
                  >
                    <div className="w-32 font-mono text-xs text-primary truncate" title={rec.record_id}>
                      {rec.record_id}
                    </div>
                    <div className="w-24 text-primary">{rec.tail_number}</div>
                    <div className="w-28 text-secondary">{formatDate(rec.occurred_at)}</div>
                    <div className="flex-1 text-primary truncate">{rec.part_name}</div>
                    <div className="w-32">
                      <ConfidenceBar confidence={rec.confidence} />
                    </div>
                    <div className="w-32">
                      <StatusChip status={rec.status} />
                    </div>
                  </Link>
                ))
              )}
            </div>

            <p className="font-sans text-xs text-secondary">
              {records.length} record{records.length !== 1 ? 's' : ''} for {selectedAsset?.tail_number}. Records are loaded one aircraft
              at a time; searching across the whole fleet is not available yet.
            </p>

            {totalPages > 1 && (
              <div className="flex justify-between items-center mt-4">
                <span className="text-sm text-secondary">
                  Showing {(page - 1) * itemsPerPage + 1} to {Math.min(page * itemsPerPage, filtered.length)} of {filtered.length}
                </span>
                <div className="flex gap-2">
                  <button
                    disabled={page === 1}
                    onClick={() => setPage(p => p - 1)}
                    className="halite-btn-ghost px-3 py-1 disabled:opacity-50"
                  >
                    Prev
                  </button>
                  <button
                    disabled={page === totalPages}
                    onClick={() => setPage(p => p + 1)}
                    className="halite-btn-ghost px-3 py-1 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
