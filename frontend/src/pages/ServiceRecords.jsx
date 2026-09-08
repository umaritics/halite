import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { maintenanceAPI } from '../api/client';
import StatusChip from '../components/StatusChip';
import ConfidenceBar from '../components/ConfidenceBar';

const STATUS_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'auto_accepted', label: 'Auto Accepted' },
  { id: 'needs_review', label: 'Needs Review' },
  { id: 'accepted', label: 'Accepted' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'superseded', label: 'Superseded' },
];

export default function ServiceRecords() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const itemsPerPage = 50;

  useEffect(() => {
    // Client-side gathering of all records via assets -> history
    maintenanceAPI.assets()
      .then(async (res) => {
        const assets = res.data;
        const historyPromises = assets.map(a => maintenanceAPI.assetHistory(a.id));
        const results = await Promise.all(historyPromises);
        let allRecords = [];
        results.forEach(r => {
          if (r.data && r.data.records) {
            // Append asset tail number for rendering
            const tailNumber = r.data.records[0]?.asset_key || r.data.asset_id;
            allRecords.push(...r.data.records.map(rec => ({ ...rec, tail_number: tailNumber, asset_id: r.data.asset_id })));
          }
        });
        allRecords.sort((a, b) => new Date(b.occurred_at) - new Date(a.occurred_at));
        setRecords(allRecords);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

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
          <p className="font-sans text-sm text-secondary">All ingested maintenance records</p>
        </div>
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

      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="text-secondary text-sm">Loading records...</div>
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
                <div className="p-4 text-sm text-secondary">No records found.</div>
              ) : (
                paginated.map(rec => (
                  <Link 
                    key={rec.id || rec.record_id}
                    to={`/app/assets/${rec.asset_id}#${rec.record_id}`}
                    className="flex items-center gap-4 px-4 py-3 border-b border-theme hover:bg-surface-dark/5 transition-colors font-sans text-sm"
                  >
                    <div className="w-32 font-mono text-xs text-primary truncate" title={rec.record_id}>
                      {rec.record_id}
                    </div>
                    <div className="w-24 text-primary">{rec.tail_number}</div>
                    <div className="w-28 text-secondary">{new Date(rec.occurred_at).toLocaleDateString()}</div>
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
