import React, { useEffect, useState, useCallback } from 'react';
import { maintenanceAPI } from '../api/client';
import StatusChip from '../components/StatusChip';
import ConfidenceBar from '../components/ConfidenceBar';

export default function ReviewQueue() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [details, setDetails] = useState(null);
  const [historyCount, setHistoryCount] = useState(0);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [actionNote, setActionNote] = useState('');
  const [errorMsg, setErrorMsg] = useState(null);
  const [toast, setToast] = useState(null);

  const fetchQueue = useCallback(() => {
    return maintenanceAPI.reviewQueue()
      .then(res => {
        setQueue(res.data);
        if (res.data.length === 0) {
          setDetails(null);
        }
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  const activeRecord = queue[currentIndex];

  useEffect(() => {
    if (!activeRecord) return;
    
    setDetailsLoading(true);
    setErrorMsg(null);
    setActionNote('');

    const tail = activeRecord.asset_key || activeRecord.asset_id; // Try to extract tail if asset_id is not tail

    Promise.all([
      maintenanceAPI.submitRecord({ record_id: activeRecord.record_id }),
      maintenanceAPI.assetHistory(tail).catch(() => ({ data: { count: '?' } }))
    ]).then(([recRes, histRes]) => {
      setDetails(recRes.data);
      setHistoryCount(histRes.data.count);
    }).catch(err => {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || 'Failed to load details');
    }).finally(() => {
      setDetailsLoading(false);
    });

  }, [activeRecord]);

  const handleAction = async (action) => {
    if (action === 'reject' && !actionNote.trim()) {
      setErrorMsg('A note is required to reject a record.');
      return;
    }

    const currentRec = activeRecord;
    const oldQueue = [...queue];

    // Optimistic UI update
    setQueue(q => q.filter((_, i) => i !== currentIndex));
    if (currentIndex >= oldQueue.length - 1) {
      setCurrentIndex(Math.max(0, oldQueue.length - 2));
    }
    
    setToast(`${action === 'accept' ? 'Accepted' : 'Rejected'} record ${currentRec.record_id}`);
    setTimeout(() => setToast(null), 3000);

    try {
      if (action === 'accept') {
        await maintenanceAPI.accept(currentRec.record_id, actionNote);
      } else {
        await maintenanceAPI.reject(currentRec.record_id, actionNote);
      }
    } catch (err) {
      // Revert on failure
      setQueue(oldQueue);
      setErrorMsg(err.response?.data?.detail || `Failed to ${action} record`);
      setToast(null);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'a' || e.key === 'A') handleAction('accept');
      if (e.key === 'r' || e.key === 'R') handleAction('reject');
      if (e.key === 'ArrowLeft') setCurrentIndex(i => Math.max(0, i - 1));
      if (e.key === 'ArrowRight') setCurrentIndex(i => Math.min(queue.length - 1, i + 1));
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [queue, currentIndex, actionNote]);

  if (loading) {
    return <div className="p-6 text-secondary font-sans text-sm">Loading queue...</div>;
  }

  if (queue.length === 0) {
    return (
      <div className="flex h-full flex-col">
        <header className="border-b border-theme px-6 py-4">
          <h2 className="font-brand text-xl text-primary">Review Queue</h2>
          <p className="font-sans text-sm text-secondary">Records the system could not resolve confidently</p>
        </header>
        <div className="p-6 font-sans text-secondary">
          Nothing awaiting review — all records were resolved automatically.
        </div>
      </div>
    );
  }

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
          Keyboard shortcuts: <kbd className="bg-surface-dark/10 px-1 rounded">A</kbd> Accept, <kbd className="bg-surface-dark/10 px-1 rounded">R</kbd> Reject, <kbd className="bg-surface-dark/10 px-1 rounded">←/→</kbd> Navigate
        </div>
      </header>

      {toast && (
        <div className="bg-accent text-black px-4 py-2 text-sm font-sans font-medium text-center">
          {toast}
        </div>
      )}

      {errorMsg && (
        <div className="bg-red-500/10 text-red-500 border-b border-red-500/20 px-6 py-2 text-sm font-sans">
          {errorMsg}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid gap-6 lg:grid-cols-[1fr_1.15fr] h-full">
          
          {/* LEFT: Incoming Record */}
          <div className="halite-card p-6 flex flex-col">
            <span className="eyebrow mb-4">INCOMING RECORD</span>
            <div className="space-y-4 font-sans text-sm flex-1">
              <div><span className="text-secondary">Record ID:</span> <span className="font-mono text-primary">{activeRecord.record_id}</span></div>
              <div><span className="text-secondary">Tail Number:</span> <span className="text-primary">{activeRecord.asset_key || activeRecord.tail_number}</span></div>
              <div><span className="text-secondary">Date:</span> <span className="text-primary">{new Date(activeRecord.occurred_at).toLocaleDateString()}</span></div>
              
              <div className="bg-surface-dark/5 p-3 rounded border border-theme">
                <div className="font-semibold text-primary mb-1">{activeRecord.part_name}</div>
                <div className="text-secondary text-xs space-x-3 mb-2">
                  {activeRecord.part_condition && <span>Condition: {activeRecord.part_condition}</span>}
                  {activeRecord.part_location && <span>Location: {activeRecord.part_location}</span>}
                  {activeRecord.jasc_code && <span>JASC: {activeRecord.jasc_code}</span>}
                </div>
                <div className="text-primary whitespace-pre-wrap mt-3">{activeRecord.text}</div>
              </div>
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
              <>
                <div className="flex-1 space-y-6">
                  {details.best_prior ? (
                    <div>
                      <span className="eyebrow mb-4 block">RETRIEVED PRIOR RECORD</span>
                      <div className="space-y-4 font-sans text-sm">
                        <div><span className="text-secondary">Record ID:</span> <span className="font-mono text-primary">{details.best_prior.record_id}</span></div>
                        <div><span className="text-secondary">Date:</span> <span className="text-primary">{new Date(details.best_prior.occurred_at).toLocaleDateString()}</span></div>
                        
                        <div className="bg-surface-dark/5 p-3 rounded border border-theme">
                          <div className="font-semibold text-primary mb-1">{details.best_prior.part_name}</div>
                          <div className="text-secondary text-xs space-x-3 mb-2">
                            {details.best_prior.part_condition && <span>Condition: {details.best_prior.part_condition}</span>}
                            {details.best_prior.part_location && <span>Location: {details.best_prior.part_location}</span>}
                          </div>
                          <div className="text-primary whitespace-pre-wrap mt-3">{details.best_prior.text}</div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-secondary font-sans text-sm mb-6">No relevant prior record retrieved.</div>
                  )}

                  <div className="border-t border-theme pt-6">
                    <div className="flex justify-between items-start mb-3">
                      <StatusChip status={details.classification?.label || 'no_conflict'} />
                      <ConfidenceBar confidence={details.confidence} />
                    </div>
                    <p className="font-sans text-sm text-primary mb-3">
                      {details.classification?.rationale || 'No rationale provided.'}
                    </p>
                    <p className="font-sans text-xs text-secondary italic">
                      Examined {details.candidates_considered} of {historyCount} records on this asset.
                    </p>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-theme sticky bottom-0 bg-surface-dark/80 backdrop-blur pb-2">
                  <textarea 
                    className="halite-input w-full mb-3 text-sm" 
                    rows={2} 
                    placeholder="Add a review note (required for rejection)..."
                    value={actionNote}
                    onChange={(e) => setActionNote(e.target.value)}
                  />
                  <div className="flex gap-3">
                    <button onClick={() => handleAction('accept')} className="halite-btn-primary flex-1 py-2 text-sm">
                      Accept
                    </button>
                    <button onClick={() => handleAction('reject')} className="halite-btn-ghost flex-1 py-2 text-sm">
                      Reject
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-secondary text-sm">Finding details unavailable.</div>
            )}
          </div>
          
        </div>
      </div>
    </div>
  );
}
