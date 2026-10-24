import { useEffect, useMemo, useRef, useState } from 'react';
import { maintenanceAPI } from '../api/client';
import { formatDate } from '../utils/format';
import { describeLoadError } from '../utils/loadError';

function evidenceKey(record) {
  return String(record?.record_id ?? record?.id ?? '');
}

function assetIdentifier(record, assets) {
  const sourceAsset = record?.asset_id || record?.asset_key;
  if (!sourceAsset) return '';
  const asset = assets.find(item => item.id === sourceAsset || item.tail_number === sourceAsset);
  return asset?.id || '';
}

function RecordField({ label, children, mono = false }) {
  if (children === undefined || children === null || children === '') return null;
  return (
    <div>
      <dt className="font-sans text-[11px] uppercase tracking-wide text-secondary">{label}</dt>
      <dd className={`mt-0.5 break-words text-sm text-primary ${mono ? 'font-mono' : 'font-sans'}`}>{children}</dd>
    </div>
  );
}

export default function DiagnosticEvidenceInspector({
  response,
  selectedPartName,
  assets,
  onOpenRecord,
  initialRecords = {},
  onRecordsResolved,
}) {
  const checks = response?.ranked_checks ?? [];
  const selectedCheck = checks.find(check => check.part_name === selectedPartName);
  const evidenceById = useMemo(
    () => new Map((response?.evidence ?? []).map(record => [evidenceKey(record), record])),
    [response]
  );
  const responseEvidenceSignature = useMemo(
    () => [...evidenceById.keys()].sort().join('|'),
    [evidenceById]
  );
  const recordIds = useMemo(() => selectedCheck?.evidence_record_ids ?? [], [selectedCheck]);
  const sourceEvidence = useMemo(
    () => recordIds.map(recordId => evidenceById.get(String(recordId))).filter(Boolean),
    [evidenceById, recordIds]
  );
  const missingEvidenceIds = useMemo(
    () => recordIds.map(String).filter(recordId => !evidenceById.has(recordId)),
    [evidenceById, recordIds]
  );
  const historyCacheRef = useRef(new Map());
  const recordCacheRef = useRef(new Map());
  const requestRef = useRef(0);
  const recordRequestRef = useRef(0);
  const [historyRecords, setHistoryRecords] = useState(new Map());
  const [loadState, setLoadState] = useState({ loading: false, errors: [] });
  const [lookedUpRecords, setLookedUpRecords] = useState(new Map());
  const [recordLoadState, setRecordLoadState] = useState({ loading: false, errors: [], missing: [] });
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const requestId = ++requestRef.current;
    setHistoryRecords(new Map());
    setLoadState({ loading: false, errors: [] });

    if (!selectedCheck || sourceEvidence.length === 0) return undefined;

    const sources = new Map();
    sourceEvidence.forEach(record => {
      const assetId = assetIdentifier(record, assets);
      if (assetId) sources.set(assetId, record.asset_id || record.asset_key || assetId);
    });
    if (sources.size === 0) return undefined;

    let cancelled = false;
    const cached = new Map();
    const pending = [];
    sourceEvidence.forEach(record => {
      const recordId = evidenceKey(record);
      if (initialRecords[recordId]) cached.set(recordId, initialRecords[recordId]);
    });
    sources.forEach((sourceLabel, assetId) => {
      const cachedHistory = historyCacheRef.current.get(assetId);
      if (cachedHistory?.signature === responseEvidenceSignature) {
        for (const record of cachedHistory.records) cached.set(evidenceKey(record), record);
      } else if (sourceEvidence.some(record => assetIdentifier(record, assets) === assetId && !cached.has(evidenceKey(record)))) {
        pending.push({ assetId, sourceLabel });
      }
    });
    setHistoryRecords(cached);
    if (pending.length === 0) return undefined;

    setLoadState({ loading: true, errors: [] });
    Promise.allSettled(pending.map(({ assetId }) => maintenanceAPI.assetHistory(assetId)))
      .then(results => {
        if (cancelled || requestRef.current !== requestId) return;
        const nextRecords = new Map(cached);
        const errors = [];
        results.forEach((result, index) => {
          const { assetId, sourceLabel } = pending[index];
          if (result.status === 'fulfilled') {
            const records = Array.isArray(result.value?.data?.records) ? result.value.data.records : [];
            historyCacheRef.current.set(assetId, { signature: responseEvidenceSignature, records });
            records.forEach(record => nextRecords.set(evidenceKey(record), record));
          } else {
            errors.push({ assetId, sourceLabel, error: describeLoadError(result.reason) });
          }
        });
        setHistoryRecords(nextRecords);
        const resolved = Object.fromEntries(recordIds
          .map(String)
          .filter(recordId => nextRecords.has(recordId))
          .map(recordId => [recordId, nextRecords.get(recordId)]));
        if (Object.keys(resolved).length > 0) onRecordsResolved?.(resolved);
        setLoadState({ loading: false, errors });
      });

    return () => { cancelled = true; };
  }, [selectedCheck, sourceEvidence, assets, responseEvidenceSignature, retryKey, initialRecords, recordIds, onRecordsResolved]);

  useEffect(() => {
    const requestId = ++recordRequestRef.current;
    const cached = new Map();
    const pending = [];
    missingEvidenceIds.forEach(recordId => {
      if (initialRecords[recordId]) cached.set(recordId, initialRecords[recordId]);
      else if (recordCacheRef.current.has(recordId)) cached.set(recordId, recordCacheRef.current.get(recordId));
      else pending.push(recordId);
    });
    setLookedUpRecords(cached);
    setRecordLoadState({ loading: pending.length > 0, errors: [], missing: [] });
    if (!selectedCheck || pending.length === 0) return undefined;

    let cancelled = false;
    Promise.allSettled(pending.map(recordId => maintenanceAPI.records({ q: recordId, limit: 1, offset: 0 })))
      .then(results => {
        if (cancelled || recordRequestRef.current !== requestId) return;
        const nextRecords = new Map(cached);
        const errors = [];
        const missing = [];
        results.forEach((result, index) => {
          const recordId = pending[index];
          if (result.status === 'fulfilled') {
            const items = Array.isArray(result.value?.data?.items) ? result.value.data.items : [];
            const record = items.find(item => evidenceKey(item) === recordId);
            if (record) {
              recordCacheRef.current.set(recordId, record);
              nextRecords.set(recordId, record);
            } else {
              missing.push(recordId);
            }
          } else {
            errors.push({ recordId, error: describeLoadError(result.reason) });
          }
        });
        setLookedUpRecords(nextRecords);
        const resolved = Object.fromEntries([...nextRecords.entries()]);
        if (Object.keys(resolved).length > 0) onRecordsResolved?.(resolved);
        setRecordLoadState({ loading: false, errors, missing });
      });

    return () => { cancelled = true; };
  }, [selectedCheck, missingEvidenceIds, retryKey, initialRecords, onRecordsResolved]);

  if (!response) {
    return null;
  }

  if (!selectedPartName) {
    return (
      <section aria-label="Component evidence inspector" className="mt-4 border-t border-theme pt-4">
        <h4 className="font-brand text-base text-primary">Evidence inspector</h4>
        <p className="mt-2 font-sans text-xs leading-5 text-secondary">
          Select a ranked component to inspect the historical records supporting its current heuristic position.
        </p>
      </section>
    );
  }

  if (!selectedCheck) {
    const dropped = (response.ranking_delta?.dropped ?? []).find(item => item.part_name === selectedPartName);
    const ruledOut = (response.case_state?.ruled_out ?? []).includes(selectedPartName);
    return (
      <section aria-label="Component evidence inspector" className="mt-4 border-t border-theme pt-4">
        <p className="eyebrow">Selected component</p>
        <h4 className="mt-1 break-words font-brand text-base text-primary">{selectedPartName}</h4>
        <div role="status" className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
          <p className="font-sans text-sm font-medium text-amber-400">
            {ruledOut ? 'Ruled out of the current investigation' : 'No longer in the current ranking'}
          </p>
          <p className="mt-1 font-sans text-xs leading-5 text-secondary">
            {dropped?.from_rank ? `It was previously rank ${dropped.from_rank}. ` : ''}
            Earlier evidence is not shown as current evidence. Select another ranked component to continue.
          </p>
        </div>
      </section>
    );
  }

  const observations = response.case_state?.observations ?? [];

  return (
    <section aria-label="Component evidence inspector" className="mt-4 border-t border-theme pt-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="eyebrow">Selected component</p>
          <h4 className="mt-1 break-words font-brand text-base text-primary">{selectedCheck.part_name}</h4>
        </div>
        <span className="rounded-full border border-accent/40 px-2 py-0.5 font-sans text-xs font-medium text-accent">
          Rank {selectedCheck.rank}
        </span>
      </div>

      <div className="mt-3 rounded-lg border border-theme bg-surface p-3">
        <p className="font-sans text-xs font-medium text-primary">HALITE heuristic ranking</p>
        <p className="mt-1 font-sans text-xs leading-5 text-secondary">
          Score {Number.isFinite(Number(selectedCheck.score)) ? Number(selectedCheck.score).toFixed(2) : 'not available'} is a ranking signal, not a failure probability or confirmation of a root cause.
        </p>
      </div>

      <div className="mt-4">
        <h5 className="font-sans text-xs font-semibold uppercase tracking-wide text-primary">Current technician observations</h5>
        {observations.length > 0 ? (
          <ul className="mt-2 list-disc space-y-1 pl-5 font-sans text-xs leading-5 text-secondary">
            {observations.map(observation => <li key={observation}>{observation}</li>)}
          </ul>
        ) : (
          <p className="mt-1 font-sans text-xs text-secondary">No current observations are recorded in the case state.</p>
        )}
      </div>

      <div className="mt-4">
        <h5 className="font-sans text-xs font-semibold uppercase tracking-wide text-primary">Historical FAA SDR evidence</h5>
        <p className="mt-1 font-sans text-[11px] leading-4 text-secondary">
          Historical observations help order checks; they do not verify the current aircraft&apos;s root cause.
        </p>

        {recordIds.length === 0 ? (
          <div className="mt-2 rounded-lg border border-dashed border-theme p-3 font-sans text-xs text-secondary">
            No supporting record IDs were returned for this component.
          </div>
        ) : (
          <div className="mt-2 space-y-2">
            {recordIds.map(recordId => {
              const turnRecord = evidenceById.get(String(recordId));
              const fullRecord = historyRecords.get(String(recordId));
              const lookedUpRecord = lookedUpRecords.get(String(recordId));
              const record = turnRecord
                ? { ...turnRecord, ...fullRecord, asset_id: turnRecord.asset_id }
                : lookedUpRecord ?? null;
              const resolvedAssetId = assetIdentifier(record, assets);
              const canOpen = Boolean(record && resolvedAssetId);
              const missingFromHistory = Boolean(
                turnRecord
                && resolvedAssetId
                && historyCacheRef.current.get(resolvedAssetId)?.signature === responseEvidenceSignature
                && !fullRecord
              );
              return (
                <article key={recordId} className="rounded-lg border border-theme bg-surface p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <span className="break-all font-mono text-xs text-accent">{recordId}</span>
                    {record?.is_superseded || record?.status === 'superseded' ? (
                      <span className="font-sans text-[11px] text-amber-400">Superseded historical record</span>
                    ) : null}
                  </div>
                  {record ? (
                    <>
                      <dl className="mt-3 grid gap-3 sm:grid-cols-2">
                        <RecordField label="Aircraft / tail">{record.tail_number || record.asset_id || record.asset_key}</RecordField>
                        <RecordField label="Report date">{record.occurred_at ? formatDate(record.occurred_at) : null}</RecordField>
                        <RecordField label="Reported component">{record.part_name}</RecordField>
                        <RecordField label="Condition / location">{[record.part_condition, record.part_location].filter(Boolean).join(' · ')}</RecordField>
                      </dl>
                      {record.text && (
                        <div className="mt-3">
                          <p className="font-sans text-[11px] uppercase tracking-wide text-secondary">Maintenance report</p>
                          <p className="mt-1 whitespace-pre-wrap break-words font-sans text-xs leading-5 text-primary">{record.text}</p>
                        </div>
                      )}
                      {canOpen && (
                        <button
                          type="button"
                          onClick={() => onOpenRecord(record)}
                          className="mt-3 font-sans text-xs font-medium text-accent underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                        >
                          Open full record view →
                        </button>
                      )}
                      {missingFromHistory && (
                        <p role="status" className="mt-2 font-sans text-[11px] leading-4 text-amber-400">
                          This record was not found in the retrieved aircraft history. The fields above are the evidence snapshot returned with this Copilot turn.
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="mt-2 font-sans text-xs leading-5 text-secondary">
                      {recordLoadState.missing.includes(String(recordId))
                        ? 'The record identifier was returned for this component, but no matching source record was found.'
                        : 'Only this record identifier is available in the current Copilot response.'}
                    </p>
                  )}
                </article>
              );
            })}
          </div>
        )}

        {loadState.loading && <p role="status" className="mt-2 font-sans text-xs text-secondary">Loading original aircraft history…</p>}
        {recordLoadState.loading && <p role="status" className="mt-2 font-sans text-xs text-secondary">Loading source records by identifier…</p>}
        {loadState.errors.length > 0 && (
          <div role="alert" className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
            <p className="font-sans text-xs font-medium text-amber-400">Some original record details could not be retrieved</p>
            {loadState.errors.map(({ assetId, sourceLabel, error }) => (
              <p key={assetId} className="mt-1 font-sans text-xs leading-5 text-secondary">
                {sourceLabel}: {error.message}
              </p>
            ))}
            <button type="button" onClick={() => setRetryKey(value => value + 1)} className="halite-btn mt-2 text-xs">Retry</button>
          </div>
        )}
        {recordLoadState.errors.length > 0 && (
          <div role="alert" className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
            <p className="font-sans text-xs font-medium text-amber-400">Some source records could not be retrieved</p>
            {recordLoadState.errors.map(({ recordId, error }) => (
              <p key={recordId} className="mt-1 font-sans text-xs leading-5 text-secondary">
                {recordId}: {error.message}
              </p>
            ))}
            <button type="button" onClick={() => setRetryKey(value => value + 1)} className="halite-btn mt-2 text-xs">Retry</button>
          </div>
        )}
      </div>
    </section>
  );
}
