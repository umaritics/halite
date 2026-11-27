import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { maintenanceAPI } from '../../api/client';
import StatusChip from '../../components/StatusChip';
import ConfidenceBar from '../../components/ConfidenceBar';
import { formatDate } from '../../utils/format';
import { describeLoadError } from '../../utils/loadError';
import { Button, EmptyState, ErrorCard, PageHeader, Skeleton } from '../../components/ui';
import DebouncedInput from './DebouncedInput';

const PAGE_SIZE = 50;
// Wide screens use one aligned grid of flexible columns (no fixed widths, so it never
// overflows); below lg every record becomes a wrapped card instead of a table row.
const ROW_LAYOUT =
  'flex flex-wrap items-center gap-x-4 gap-y-1 lg:grid lg:gap-3 ' +
  'lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.8fr)_minmax(0,0.9fr)_minmax(0,1.4fr)_minmax(0,1.7fr)_minmax(0,1fr)]';
const FILTER_KEYS = ['asset', 'q', 'status', 'analysis_state', 'part', 'date_from', 'date_to'];

function apiParams(searchParams, offset = 0) {
  const params = { limit: PAGE_SIZE, offset };
  FILTER_KEYS.forEach((key) => {
    const value = searchParams.get(key);
    if (value) params[key === 'asset' ? 'asset_id' : key] = value;
  });
  return params;
}

function RecordRow({ record, linkedRecordId }) {
  const isLinked = linkedRecordId === record.record_id;
  return (
    <div
      id={`record-${record.record_id}`}
      className={`border-b border-theme ${isLinked ? 'ring-2 ring-inset ring-accent bg-accent/5' : ''}`}
    >
      <Link
        to={`/app/asset-history/${record.asset_id}#${record.record_id}`}
        className={`${ROW_LAYOUT} px-4 py-3 text-sm hover:bg-surface-dark/5`}
      >
        <span className="min-w-0 max-w-full truncate font-mono text-xs text-primary">{record.record_id}</span>
        <span className="text-primary">{record.tail_number}</span>
        <span className="text-secondary">{formatDate(record.occurred_at)}</span>
        <span className="min-w-0 max-w-full truncate text-primary">{record.part_name || 'Unknown'}</span>
        <ConfidenceBar
          confidence={record.confidence}
          analysisState={record.analysis_state}
          classification={record.classification_label}
          candidateCount={record.candidate_count ?? record.candidates_considered}
          status={record.status}
          legacyPlaceholder={record.legacy_placeholder}
          analysisMethod={record.analysis_method}
          analysisPasses={record.analysis_passes}
          voteAgreement={record.analysis_vote_agreement}
        />
        <StatusChip
          status={record.status}
          analysisState={record.analysis_state}
          legacyPlaceholder={record.legacy_placeholder}
        />
      </Link>
      {record.status === 'superseded' && record.corrected_by && (
        <div className="bg-amber-500/5 px-4 py-2 text-xs text-amber-500">
          Corrected by{' '}
          <Link
            className="font-mono underline"
            to={`/app/asset-history/${record.asset_id}#${record.corrected_by.record_id}`}
          >
            {record.corrected_by.record_id}
          </Link>
          {` — component changed ${record.part_name || 'Unknown'} → ${record.corrected_by.part_name || 'Unknown'}`}
        </div>
      )}
    </div>
  );
}

export default function ServiceRecords() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [assets, setAssets] = useState([]);
  const [assetsError, setAssetsError] = useState(null);
  const [pageData, setPageData] = useState({ items: [], total: 0, next: null });
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [loadMoreError, setLoadMoreError] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const filterSignature = searchParams.toString();
  const linkedRecordId = searchParams.get('record')
    || (typeof window !== 'undefined' ? decodeURIComponent(window.location.hash.slice(1)) : '');

  useEffect(() => {
    let cancelled = false;
    maintenanceAPI.assets()
      .then(({ data }) => { if (!cancelled) setAssets(Array.isArray(data) ? data : []); })
      .catch((err) => { if (!cancelled) setAssetsError(describeLoadError(err)); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setLoadMoreError(null);
    maintenanceAPI.records(apiParams(searchParams))
      .then(({ data }) => { if (!cancelled) setPageData(data); })
      .catch((err) => { if (!cancelled) setError(describeLoadError(err)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
    // searchParams identity changes independently of its serialized filters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterSignature, attempt]);

  const setFilter = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value); else next.delete(key);
    setSearchParams(next, { replace: true });
  };

  const loadMore = async () => {
    if (pageData.next == null || loadingMore) return;
    setLoadingMore(true);
    setLoadMoreError(null);
    try {
      const { data } = await maintenanceAPI.records(apiParams(searchParams, pageData.next));
      setPageData((current) => ({ ...data, items: [...current.items, ...data.items] }));
    } catch (err) {
      setLoadMoreError(describeLoadError(err));
    } finally {
      setLoadingMore(false);
    }
  };

  const selectedTail = useMemo(
    () => assets.find((asset) => asset.id === searchParams.get('asset'))?.tail_number,
    [assets, searchParams]
  );

  return (
    <div className="flex h-full flex-col">
      <div className="px-6 pt-4">
        <PageHeader
          title="Service Records"
          description={
            selectedTail
              ? `Fleet records filtered to ${selectedTail}`
              : 'All aircraft — fleet-wide records'
          }
        />
      </div>

      <div className="grid gap-3 border-b border-theme px-6 py-3 sm:grid-cols-2 md:grid-cols-4 xl:grid-cols-7">
        <select aria-label="Aircraft" className="halite-input" value={searchParams.get('asset') || ''} onChange={(e) => setFilter('asset', e.target.value)}>
          <option value="">All aircraft</option>
          {assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.tail_number}</option>)}
        </select>
        <DebouncedInput aria-label="Search records" className="halite-input" placeholder="Search fleet…" value={searchParams.get('q') || ''} onCommit={(value) => setFilter('q', value)} />
        <select aria-label="Status" className="halite-input" value={searchParams.get('status') || ''} onChange={(e) => setFilter('status', e.target.value)}>
          <option value="">All statuses</option>
          {['unscored', 'no_action', 'auto_accepted', 'needs_review', 'accepted', 'rejected', 'superseded'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}
        </select>
        <select aria-label="Analysis state" className="halite-input" value={searchParams.get('analysis_state') || ''} onChange={(e) => setFilter('analysis_state', e.target.value)}>
          <option value="">All analysis states</option>
          {['unscored', 'scored', 'needs_review', 'reviewed'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}
        </select>
        <DebouncedInput aria-label="Component" className="halite-input" placeholder="Component" value={searchParams.get('part') || ''} onCommit={(value) => setFilter('part', value)} />
        <input aria-label="Date from" type="date" className="halite-input" value={searchParams.get('date_from') || ''} onChange={(e) => setFilter('date_from', e.target.value)} />
        <input aria-label="Date to" type="date" className="halite-input" value={searchParams.get('date_to') || ''} onChange={(e) => setFilter('date_to', e.target.value)} />
      </div>

      {assetsError && <div role="status" className="px-6 py-2 text-sm text-amber-400">Aircraft filter unavailable: {assetsError.message}</div>}

      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div>
            <p className="mb-3 text-sm text-secondary">Loading fleet records…</p>
            <Skeleton variant="card" lines={4} />
          </div>
        ) : error ? (
          <div className="max-w-xl">
            <ErrorCard
              message={
                <>
                  <span className="block">Could not load service records</span>
                  <span className="block text-sm text-secondary">{error.message}</span>
                </>
              }
              onRetry={() => setAttempt((n) => n + 1)}
            />
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-secondary">
              Showing {pageData.items.length} of {pageData.total} records
            </p>
            <div className="halite-card overflow-hidden">
              <div className={`${ROW_LAYOUT} hidden border-b border-theme px-4 py-3 text-xs text-secondary lg:grid`}>
                <span>Record ID</span>
                <span>Aircraft</span>
                <span>Date</span>
                <span>Component</span>
                <span>Analysis</span>
                <span>Status</span>
              </div>
              {pageData.items.length === 0 ? (
                <div className="p-4">
                  <EmptyState title="No records match the current filters." />
                </div>
              ) : (
                pageData.items.map((record) => <RecordRow key={record.record_id} record={record} linkedRecordId={linkedRecordId} />)
              )}
            </div>
            {loadMoreError && (
              <ErrorCard
                message={`Could not load more records. ${loadMoreError.message}`}
                onRetry={loadMore}
                retryLabel="Try again"
              />
            )}
            {pageData.next != null && !loadMoreError && (
              <Button variant="outline" loading={loadingMore} onClick={loadMore}>
                {loadingMore ? 'Loading…' : 'Load more'}
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
