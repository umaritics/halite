import { useEffect, useMemo, useRef, useState } from 'react';
import { maintenanceAPI } from '../api/client';
import {
  caseIssueLabels,
  evidenceKey,
  groupEvidenceRecords,
  historicalIssueDiff,
  resolveRecordAircraft,
} from '../utils/diagnosticEvidence';
import { describeLoadError } from '../utils/loadError';

const GROUP_PREVIEW_COUNT = 3;

function assetIdentifier(record, assets) {
  return resolveRecordAircraft(record, assets).assetId;
}

function RecordField({ label, children }) {
  if (children === undefined || children === null || children === '') return null;
  return (
    <div>
      <dt className="font-sans text-[11px] uppercase tracking-wide text-secondary">{label}</dt>
      <dd className="mt-0.5 break-words font-sans text-sm text-primary">{children}</dd>
    </div>
  );
}

function ProvenanceNotice({ group, currentIssues }) {
  const { provenance } = group;
  const issueDiff = historicalIssueDiff(group.condition, currentIssues);
  let title = 'Aircraft identity unavailable or unverified';
  let explanation = provenance.selectedAircraftLabel
    ? `The available record fields do not verify whether this evidence belongs to selected aircraft ${provenance.selectedAircraftLabel}.`
    : 'No investigation aircraft is selected, so this evidence cannot be classified as same- or other-aircraft history.';
  let className = 'border-theme bg-page/20';

  if (provenance.kind === 'same') {
    title = 'Same-aircraft historical evidence';
    explanation = `Historical evidence from selected aircraft ${provenance.selectedAircraftLabel}. It does not confirm the current root cause.`;
    className = 'border-emerald-500/30 bg-emerald-500/5';
  } else if (provenance.kind === 'other') {
    title = 'Other-aircraft / fleet evidence';
    explanation = `Historical evidence from aircraft ${provenance.aircraftLabel}. It is not a record from selected aircraft ${provenance.selectedAircraftLabel} and does not establish that aircraft’s root cause.`;
    className = 'border-amber-500/30 bg-amber-500/5';
  }

  return (
    <div className={`mt-3 rounded-lg border p-3 ${className}`}>
      <p className="font-sans text-xs font-semibold text-primary">{title}</p>
      <p className="mt-1 font-sans text-[11px] leading-4 text-secondary">{explanation}</p>
      {issueDiff && (
        <p className="mt-1 font-sans text-[11px] leading-4 text-secondary">
          These records concern {issueDiff.historical.join(' and ')}; the current case includes {issueDiff.current.join(' and ')}.
        </p>
      )}
    </div>
  );
}

function EvidenceRecord({ entry, assets, onOpenRecord, missingFromHistory, sourceMissing }) {
  const { recordId, record } = entry;
  const resolvedAssetId = assetIdentifier(record, assets);
  const canOpen = Boolean(record && resolvedAssetId);
  const sourceDate = String(record?.occurred_at ?? '').trim();

  return (
    <details className="rounded-lg border border-theme bg-page/20 px-3 py-2">
      <summary className="cursor-pointer list-none rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
        <span className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
          <span className="break-all font-mono text-xs text-accent">{recordId}</span>
          <span className="flex shrink-0 flex-wrap items-center gap-2 font-sans text-[11px] text-secondary">
            {sourceDate && <time dateTime={sourceDate}>{sourceDate}</time>}
            {record?.is_superseded || record?.status === 'superseded' ? (
              <span className="text-amber-400">Superseded</span>
            ) : null}
            <span aria-hidden="true" className="text-accent">Details ↓</span>
          </span>
        </span>
      </summary>

      <div className="mt-3 border-t border-theme pt-3">
        {record ? (
          <>
            <dl className="grid gap-3 sm:grid-cols-2">
              <RecordField label="Aircraft / tail">{record.tail_number || record.asset_id || record.asset_key}</RecordField>
              <RecordField label="Reported component">{record.part_name}</RecordField>
              <RecordField label="Condition">{record.part_condition}</RecordField>
              <RecordField label="Location">{record.part_location}</RecordField>
            </dl>
            {record.text && (
              <div className="mt-3">
                <p className="font-sans text-[11px] uppercase tracking-wide text-secondary">Original maintenance narrative</p>
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
          <p className="font-sans text-xs leading-5 text-secondary">
            {sourceMissing
              ? 'The cited identifier was preserved, but no matching source record was retrieved.'
              : 'Only this cited record identifier is currently available.'}
          </p>
        )}
      </div>
    </details>
  );
}

function EvidenceGroup({ group, assets, currentIssues, expanded, onToggle, onOpenRecord, missingFromHistory, sourceMissing }) {
  const hiddenCount = Math.max(0, group.records.length - GROUP_PREVIEW_COUNT);
  const visibleRecords = expanded ? group.records : group.records.slice(0, GROUP_PREVIEW_COUNT);
  const groupTitle = group.aircraft ? `Aircraft ${group.aircraft}` : 'Aircraft not identified';

  return (
    <article className="rounded-xl border border-theme bg-surface p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h6 className="break-words font-sans text-sm font-semibold text-primary">{groupTitle}</h6>
          <p className="mt-0.5 font-sans text-xs text-secondary">
            {group.records.length} maintenance record{group.records.length === 1 ? '' : 's'}
          </p>
        </div>
        <span className="rounded-full border border-theme px-2 py-0.5 font-sans text-[10px] uppercase tracking-wide text-secondary">
          {group.provenance.kind === 'same' ? 'Same aircraft' : group.provenance.kind === 'other' ? 'Fleet evidence' : 'Unverified aircraft'}
        </span>
      </div>

      {(group.component || group.condition) && (
        <dl className="mt-3 grid gap-2 sm:grid-cols-2">
          <RecordField label="Reported component">{group.component}</RecordField>
          <RecordField label="Historical condition">{group.condition}</RecordField>
        </dl>
      )}

      <ProvenanceNotice group={group} currentIssues={currentIssues} />

      <div className="mt-3 space-y-2" aria-label={`Individual reports for ${groupTitle}`}>
        {visibleRecords.map(entry => (
          <EvidenceRecord
            key={entry.recordId}
            entry={entry}
            assets={assets}
            onOpenRecord={onOpenRecord}
            missingFromHistory={missingFromHistory(entry)}
            sourceMissing={sourceMissing(entry.recordId)}
          />
        ))}
      </div>

      {hiddenCount > 0 && (
        <button
          type="button"
          aria-expanded={expanded}
          onClick={onToggle}
          className="mt-3 w-full rounded-lg border border-theme px-3 py-2 text-left font-sans text-xs font-medium text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          {expanded ? 'Show fewer records' : `Show remaining ${hiddenCount} record${hiddenCount === 1 ? '' : 's'}`}
        </button>
      )}
    </article>
  );
}

export default function DiagnosticEvidenceInspector({
  response,
  selectedPartName,
  selectedAssetId,
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
  const [expandedGroups, setExpandedGroups] = useState(new Set());

  useEffect(() => {
    setExpandedGroups(new Set());
  }, [selectedPartName, responseEvidenceSignature]);

  useEffect(() => {
    const requestId = ++requestRef.current;
    setHistoryRecords(new Map());
    setLoadState({ loading: false, errors: [] });

    if (!selectedCheck || sourceEvidence.length === 0) return undefined;

    const sources = new Map();
    sourceEvidence.forEach(record => {
      const assetId = assetIdentifier(record, assets);
      if (assetId) sources.set(assetId, record.tail_number || record.asset_id || record.asset_key || assetId);
    });
    if (sources.size === 0) return undefined;

    let cancelled = false;
    const cached = new Map();
    sourceEvidence.forEach(record => {
      const recordId = evidenceKey(record);
      if (initialRecords[recordId]) cached.set(recordId, initialRecords[recordId]);
    });
    const pending = [];
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

  const recordsById = useMemo(() => {
    const records = new Map();
    recordIds.map(String).forEach(recordId => {
      const turnRecord = evidenceById.get(recordId);
      const enrichedRecord = historyRecords.get(recordId);
      const lookedUpRecord = lookedUpRecords.get(recordId);
      const initialRecord = initialRecords[recordId];
      if (turnRecord) {
        records.set(recordId, {
          ...turnRecord,
          ...(initialRecord ?? {}),
          ...(enrichedRecord ?? {}),
          asset_id: turnRecord.asset_id || enrichedRecord?.asset_id || initialRecord?.asset_id,
        });
      } else if (lookedUpRecord || initialRecord) {
        records.set(recordId, lookedUpRecord ?? initialRecord);
      }
    });
    return records;
  }, [recordIds, evidenceById, historyRecords, lookedUpRecords, initialRecords]);

  const groups = useMemo(
    () => groupEvidenceRecords(recordIds, recordsById, selectedAssetId, assets),
    [recordIds, recordsById, selectedAssetId, assets]
  );
  const currentIssues = useMemo(() => caseIssueLabels(response?.case_state), [response]);

  if (!response) return null;

  if (!selectedPartName) {
    return (
      <section aria-label="Component evidence inspector" className="mt-4 border-t border-theme pt-4">
        <h4 className="font-brand text-base text-primary">Evidence inspector</h4>
        <p className="mt-2 font-sans text-xs leading-5 text-secondary">
          Select a ranked component to inspect its grounded historical records.
        </p>
      </section>
    );
  }

  if (!selectedCheck) {
    const dropped = (response.ranking_delta?.dropped ?? []).find(item => item.part_name === selectedPartName);
    const ruledOut = (response.case_state?.ruled_out ?? []).includes(selectedPartName);
    return (
      <section aria-label="Component evidence inspector" className="mt-4 border-t border-theme pt-4">
        <h4 className="break-words font-brand text-base text-primary">Evidence for {selectedPartName}</h4>
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

  const observationCount = response.case_state?.observations?.length ?? 0;
  const retrievedCount = recordsById.size;
  const missingFromHistory = ({ recordId, record }) => {
    const resolvedAssetId = assetIdentifier(record, assets);
    return Boolean(
      evidenceById.has(recordId)
      && resolvedAssetId
      && historyCacheRef.current.get(resolvedAssetId)?.signature === responseEvidenceSignature
      && !historyRecords.has(recordId)
    );
  };

  return (
    <section aria-label="Component evidence inspector" className="mt-4 border-t border-theme pt-4">
      <h4 className="break-words font-brand text-base text-primary">Evidence for {selectedCheck.part_name}</h4>
      <p className="mt-1 font-sans text-[11px] leading-4 text-secondary">
        Case State contains {observationCount} model-extracted observation{observationCount === 1 ? '' : 's'}; original technician wording remains in the conversation.
      </p>

      <div className="mt-4">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h5 className="font-sans text-xs font-semibold uppercase tracking-wide text-primary">Historical evidence</h5>
            <p className="mt-1 font-sans text-xs text-secondary">
              {recordIds.length} cited record ID{recordIds.length === 1 ? '' : 's'} · {retrievedCount} source record{retrievedCount === 1 ? '' : 's'} retrieved
            </p>
          </div>
        </div>
        <p className="mt-2 font-sans text-[11px] leading-4 text-secondary">
          Historical records help order checks; they are not probabilities and do not confirm the current aircraft&apos;s root cause.
        </p>
        {retrievedCount < recordIds.length && (
          <p role="status" className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-2 font-sans text-[11px] leading-4 text-amber-400">
            Source details are currently available for {retrievedCount} of {recordIds.length} cited IDs. Every cited ID remains listed below.
          </p>
        )}

        {recordIds.length === 0 ? (
          <div className="mt-2 rounded-lg border border-dashed border-theme p-3 font-sans text-xs text-secondary">
            No supporting record IDs were returned for this component.
          </div>
        ) : (
          <div className="mt-3 space-y-3">
            {groups.map(group => (
              <EvidenceGroup
                key={group.key}
                group={group}
                assets={assets}
                currentIssues={currentIssues}
                expanded={expandedGroups.has(group.key)}
                onToggle={() => setExpandedGroups(current => {
                  const next = new Set(current);
                  if (next.has(group.key)) next.delete(group.key);
                  else next.add(group.key);
                  return next;
                })}
                onOpenRecord={onOpenRecord}
                missingFromHistory={missingFromHistory}
                sourceMissing={recordId => recordLoadState.missing.includes(String(recordId))}
              />
            ))}
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
