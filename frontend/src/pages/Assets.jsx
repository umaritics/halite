import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { maintenanceAPI } from '../api/client';

export default function Assets() {
  const [assets, setAssets] = useState([]);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('count'); // count or tail
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    maintenanceAPI.assets()
      .then(res => setAssets(res.data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const filtered = assets.filter(a => (a.tail_number || '').toLowerCase().includes(search.toLowerCase()));
  
  if (sort === 'count') {
    filtered.sort((a, b) => b.record_count - a.record_count);
  } else {
    filtered.sort((a, b) => (a.tail_number || '').localeCompare(b.tail_number || ''));
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-theme px-6 py-4">
        <div>
          <h2 className="font-brand text-xl text-primary">Assets</h2>
          <p className="font-sans text-sm text-secondary">Aircraft and equipment with recorded service history</p>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-3 border-b border-theme px-6 py-3">
        <input 
          type="text" 
          placeholder="Search by tail number..." 
          className="halite-input w-full sm:w-[320px]"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select 
          className="halite-input" 
          value={sort} 
          onChange={e => setSort(e.target.value)}
        >
          <option value="count">Sort by Record Count</option>
          <option value="tail">Sort by Tail Number</option>
        </select>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="text-secondary text-sm">Loading assets...</div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map(a => (
              <NavLink 
                key={a.id} 
                to={`/app/asset-history/${a.id}`}
                className="halite-card p-4 hover:border-accent transition-colors block"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-brand text-lg text-primary">{a.tail_number}</h3>
                  <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-accent/20 px-1.5 text-xs font-semibold text-accent ring-1 ring-accent/40">
                    {a.record_count}
                  </span>
                </div>
                <div className="font-sans text-sm text-secondary mb-2">
                  {a.make} {a.model} {a.serial_number ? `(SN: ${a.serial_number})` : ''}
                </div>
                <div className="font-sans text-xs text-secondary mt-auto">
                  {/* Note: In a real app we'd map latest record date here if API provides it */}
                  ID: {a.id}
                </div>
              </NavLink>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
