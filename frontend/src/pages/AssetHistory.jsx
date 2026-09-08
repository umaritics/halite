import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { maintenanceAPI } from '../api/client';
import StatusChip from '../components/StatusChip';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';

export default function AssetHistory() {
  const { assetId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    maintenanceAPI.assetHistory(assetId)
      .then(res => setData(res.data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, [assetId]);

  if (loading) {
    return (
      <div className="flex h-full flex-col p-6">
        <div className="h-8 w-32 bg-surface-dark/10 animate-pulse rounded mb-4"></div>
        <div className="h-24 w-full bg-surface-dark/10 animate-pulse rounded mb-4 halite-card"></div>
        <div className="h-24 w-full bg-surface-dark/10 animate-pulse rounded mb-4 halite-card"></div>
        <div className="h-24 w-full bg-surface-dark/10 animate-pulse rounded mb-4 halite-card"></div>
      </div>
    );
  }

  if (!data || !data.records || data.records.length === 0) {
    return (
      <div className="flex h-full flex-col p-6">
        <Link to="/app/assets" className="inline-flex items-center gap-2 text-accent hover:underline mb-4 font-sans text-sm font-medium">
          <ArrowLeftIcon className="h-4 w-4" /> Back to Assets
        </Link>
        <p className="font-sans text-secondary">No records for this asset yet.</p>
      </div>
    );
  }

  const tailNumber = data.records[0]?.asset_key || assetId;
  const records = [...data.records].sort((a, b) => new Date(a.occurred_at) - new Date(b.occurred_at));

  return (
    <div className="flex h-full flex-col">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-theme px-6 py-4">
        <div>
          <Link to="/app/assets" className="inline-flex items-center gap-2 text-accent hover:underline mb-2 font-sans text-sm font-medium">
            <ArrowLeftIcon className="h-4 w-4" /> Back to Assets
          </Link>
          <h2 className="font-brand text-xl text-primary">{tailNumber}</h2>
          <p className="font-sans text-sm text-secondary">{data.count} service records</p>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6 relative">
        <div className="absolute left-10 top-6 bottom-6 w-[2px] bg-accent/20 hidden sm:block"></div>
        <div className="space-y-6">
          {records.map((rec) => {
            const isSuperseded = rec.status === 'superseded';
            // Parse supersede target/rationale from text if needed, 
            // since API doesn't seem to have a dedicated rationale field on history. 
            // The instruction says "Superseded by {record_id} — {rationale}".
            // We will just show a placeholder if we don't have it explicitly, or check if it's passed somehow.
            return (
              <div key={rec.id || rec.record_id} className="relative flex items-start gap-4 sm:pl-12">
                <div className="absolute left-9 -ml-[5px] mt-1.5 h-[10px] w-[10px] rounded-full bg-accent ring-4 ring-page hidden sm:block"></div>
                <div className={`halite-card p-4 flex-1 ${isSuperseded ? 'opacity-50' : ''}`}>
                  <div className="flex justify-between items-start mb-2">
                    <span className="eyebrow">{new Date(rec.occurred_at).toLocaleDateString()}</span>
                    <StatusChip status={rec.status} />
                  </div>
                  
                  {isSuperseded && (
                    <div className="mb-3 font-sans text-sm text-accent bg-accent/10 p-2 rounded border border-accent/20">
                      Superseded by {rec.superseding_record || 'Unknown'} — {rec.supersede_rationale || 'Previous record invalidated'}
                    </div>
                  )}

                  <h4 className="font-sans font-semibold text-primary mb-1">
                    {rec.part_name} {rec.part_condition ? `- ${rec.part_condition}` : ''} {rec.part_location ? `(${rec.part_location})` : ''}
                  </h4>
                  <p className="font-sans text-sm text-secondary whitespace-pre-wrap">
                    {rec.text}
                  </p>
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
