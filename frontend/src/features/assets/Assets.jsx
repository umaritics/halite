import React, { useEffect, useMemo, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { maintenanceAPI } from '../../api/client';
import { describeLoadError } from '../../utils/loadError';
import { EmptyState, ErrorCard, PageHeader, Skeleton } from '../../components/ui';

function visibleAssets(assets, search, sort) {
  const needle = search.toLowerCase();
  const matches = assets.filter((a) => (a.tail_number || '').toLowerCase().includes(needle));
  if (sort === 'count') {
    return matches.sort((a, b) => b.record_count - a.record_count);
  }
  return matches.sort((a, b) => (a.tail_number || '').localeCompare(b.tail_number || ''));
}

function AssetCard({ asset }) {
  return (
    <NavLink
      to={`/app/asset-history/${asset.id}`}
      className="halite-card block p-4 transition-colors hover:border-accent"
    >
      <div className="mb-2 flex items-start justify-between">
        <h3 className="font-brand text-lg text-primary">{asset.tail_number}</h3>
        <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-accent/20 px-1.5 text-xs font-semibold text-accent ring-1 ring-accent/40">
          {asset.record_count}
        </span>
      </div>
      <div className="mb-2 font-sans text-sm text-secondary">
        {asset.make} {asset.model} {asset.serial_number ? `(SN: ${asset.serial_number})` : ''}
      </div>
      <div className="mt-auto font-sans text-xs text-secondary">ID: {asset.id}</div>
    </NavLink>
  );
}

function AssetList({ assets, filtered, search }) {
  if (assets.length === 0) {
    return (
      <EmptyState
        title="No assets yet"
        body="Aircraft and equipment appear here once maintenance records have been ingested."
      />
    );
  }
  if (filtered.length === 0) {
    return (
      <EmptyState
        title="No assets match your search"
        body={`Nothing matches "${search}". Try a different tail number.`}
      />
    );
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {filtered.map((asset) => (
        <AssetCard key={asset.id} asset={asset} />
      ))}
    </div>
  );
}

export default function Assets() {
  const [assets, setAssets] = useState([]);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('count'); // count or tail
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    maintenanceAPI
      .assets()
      .then((res) => {
        if (!cancelled) setAssets(Array.isArray(res.data) ? res.data : []);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error(err);
        setError(describeLoadError(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const filtered = useMemo(() => visibleAssets(assets, search, sort), [assets, search, sort]);

  let body;
  if (loading) {
    body = (
      <div>
        <p className="mb-3 text-sm text-secondary">Loading assets...</p>
        <Skeleton variant="card" lines={3} />
      </div>
    );
  } else if (error) {
    body = (
      <ErrorCard
        message={`Could not load assets. ${error.message}`}
        onRetry={() => setAttempt((n) => n + 1)}
      />
    );
  } else {
    body = <AssetList assets={assets} filtered={filtered} search={search} />;
  }

  return (
    <div className="flex h-full flex-col">
      <div className="px-6 pt-4">
        <PageHeader
          title="Assets"
          description="Aircraft and equipment with recorded service history"
        />
      </div>

      <div className="flex flex-wrap items-center gap-3 border-b border-theme px-6 py-3">
        <input
          type="text"
          aria-label="Search assets by tail number"
          placeholder="Search by tail number..."
          className="halite-input w-full sm:w-[320px]"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="Sort assets"
          className="halite-input"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
        >
          <option value="count">Sort by Record Count</option>
          <option value="tail">Sort by Tail Number</option>
        </select>
      </div>

      <div className="flex-1 overflow-y-auto p-6">{body}</div>
    </div>
  );
}
