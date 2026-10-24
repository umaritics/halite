import { Fragment, useState, useEffect, useLayoutEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { MagnifyingGlassIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';
import { maintenanceAPI } from '../api/client';
import CopilotMarkdown from '../components/CopilotMarkdown';
import DiagnosticEvidenceInspector from '../components/DiagnosticEvidenceInspector';
import { describeDiagnosticError, extractExplanation, splitUnverified } from '../utils/diagnostics';
import {
  clearActiveDiagnosticWorkspace,
  loadActiveDiagnosticWorkspace,
  storeActiveDiagnosticWorkspace,
} from '../utils/diagnosticWorkspace';

const MAX_IDS_PER_CHECK = 5;
const MAX_PERSISTED_INSPECTOR_RECORDS = 50;

// G4: Diagnostic chat page
// Layout:
//   - Asset selector (searchable dropdown)
//   - Symptom textarea
//   - Response panel: ranked_checks, evidence, rare_cases
//   - Context transparency line
//
// Every non-success outcome is shown explicitly (model unavailable, no history,
// rate limit, server error, network error, insufficient evidence). The page never
// fills a gap with invented content.

function QuickDiagnose() {
  const navigate = useNavigate();
  const [assets, setAssets] = useState([]);
  const [assetSearch, setAssetSearch] = useState('');
  const [assetDropdownOpen, setAssetDropdownOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [symptom, setSymptom] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [submitted, setSubmitted] = useState(null);
  const [error, setError] = useState(null);
  const [rareExpanded, setRareExpanded] = useState(false);
  const [expandedIds, setExpandedIds] = useState({});

  useEffect(() => {
    maintenanceAPI.assets()
      .then(res => setAssets(res.data))
      .catch(() => {});
  }, []);

  const filteredAssets = assets.filter(a =>
    a.tail_number.toLowerCase().includes(assetSearch.toLowerCase())
  );

  const runDiagnostic = async (asset, symptomText) => {
    if (loading) return;
    setLoading(true);
    setResult(null);
    setError(null);
    setRareExpanded(false);
    setSubmitted({ asset, symptom: symptomText });
    setExpandedIds({});
    try {
      const res = await maintenanceAPI.diagnose(asset.id, symptomText);
      setResult(res.data);
    } catch (err) {
      setError(describeDiagnosticError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!selectedAsset || !symptom.trim()) return;
    runDiagnostic(selectedAsset, symptom.trim());
  };

  const handleRetry = () => {
    if (submitted) runDiagnostic(submitted.asset, submitted.symptom);
  };

  const handleClear = () => {
    setSymptom('');
    setResult(null);
    setError(null);
    setSubmitted(null);
    setRareExpanded(false);
  };

  // Tolerate absent optional fields in the response.
  const rankedChecks = result?.ranked_checks ?? [];
  const evidence = result?.evidence ?? [];
  const rareCases = result?.rare_cases ?? [];
  const insufficientEvidence = Boolean(result) && rankedChecks.length === 0 && evidence.length === 0;

  const explanation = result ? extractExplanation(result.explanation) : null;
  const warnings = result
    ? [...new Set([...(result.warnings ?? []), ...(explanation?.warnings ?? [])])]
    : [];
  const validIds = result?.citation_validation?.valid_ids ?? [];
  const invalidIds = result?.citation_validation?.invalid_ids ?? [];
  const citationsAllValid = result?.citation_validation?.all_valid;

  // Evidence records the backend returned, keyed by record id, so a ranked check's record
  // ids can link to the right aircraft's history. IDs that are not in `evidence` stay plain
  // text: their aircraft is unknown, so a link could land on the wrong page.
  const evidenceById = Object.fromEntries(evidence.map(ev => [ev.record_id, ev]));
  const openRecord = (ev) => {
    const assetUuid = assets.find(a => a.tail_number === ev.asset_id)?.id || ev.asset_id;
    navigate(`/app/asset-history/${assetUuid}#${ev.record_id}`);
  };

  return (
    <div className="h-full overflow-y-auto">
      <header className="border-b border-theme px-6 py-4">
        <div className="flex items-center gap-3">
          <MagnifyingGlassIcon className="h-5 w-5 text-accent" />
          <div>
            <h2 className="font-brand text-xl text-primary">Diagnostics</h2>
            <p className="font-sans text-sm text-secondary">
              Graph-grounded inspection order with fleet-wide evidence
            </p>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-3xl space-y-6 p-6">
        <form onSubmit={handleSubmit} className="halite-card p-6 space-y-4">
          {/* Asset selector */}
          <div className="relative">
            <label className="eyebrow mb-1 block">Aircraft</label>
            <button
              type="button"
              id="asset-selector-btn"
              onClick={() => setAssetDropdownOpen(o => !o)}
              className="halite-input w-full text-left flex items-center justify-between"
            >
              <span className={selectedAsset ? 'text-primary' : 'text-secondary'}>
                {selectedAsset ? `${selectedAsset.tail_number} (${selectedAsset.record_count} records)` : 'Select aircraft…'}
              </span>
              {assetDropdownOpen
                ? <ChevronUpIcon className="h-4 w-4 text-secondary" />
                : <ChevronDownIcon className="h-4 w-4 text-secondary" />}
            </button>
            {assetDropdownOpen && (
              <div className="absolute z-20 mt-1 w-full rounded-lg border border-theme bg-surface shadow-lg">
                <div className="p-2">
                  <input
                    autoFocus
                    type="text"
                    placeholder="Search tail number…"
                    value={assetSearch}
                    onChange={e => setAssetSearch(e.target.value)}
                    className="halite-input w-full text-sm"
                  />
                </div>
                <ul className="max-h-52 overflow-y-auto divide-y divide-theme">
                  {filteredAssets.length === 0 ? (
                    <li className="px-4 py-2 text-sm text-secondary">No assets found</li>
                  ) : filteredAssets.map(a => (
                    <li key={a.id}>
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedAsset(a);
                          setAssetDropdownOpen(false);
                          setAssetSearch('');
                        }}
                        className={`w-full px-4 py-2 text-left text-sm transition hover:bg-accent/10 ${
                          selectedAsset?.id === a.id ? 'text-accent font-medium' : 'text-primary'
                        }`}
                      >
                        {a.tail_number}
                        <span className="ml-2 text-secondary">{a.record_count} records</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Symptom input */}
          <div>
            <label className="eyebrow mb-1 block">Symptom</label>
            <textarea
              id="symptom-input"
              value={symptom}
              onChange={e => setSymptom(e.target.value)}
              rows={3}
              placeholder="e.g. slide light will not extinguish at door 1R"
              className="halite-input w-full resize-none"
            />
            {!selectedAsset && symptom.trim() && (
              <p className="mt-1 font-sans text-xs text-amber-400">Select an aircraft to run the diagnostic.</p>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              id="diagnose-submit-btn"
              type="submit"
              disabled={!selectedAsset || !symptom.trim() || loading}
              className="halite-btn-primary disabled:opacity-50"
            >
              {loading ? 'Analysing…' : 'Run diagnostic'}
            </button>
            {(symptom || result || error) && (
              <button
                id="diagnose-clear-btn"
                type="button"
                onClick={handleClear}
                disabled={loading}
                className="halite-btn text-sm disabled:opacity-50"
              >
                Clear
              </button>
            )}
          </div>
        </form>

        {/* Error state */}
        {error && !loading && (
          <div role="alert" className="halite-card border border-red-500/30 bg-red-500/5 p-4">
            <p className="font-sans text-sm font-medium text-red-400">{error.title}</p>
            <p className="mt-1 font-sans text-sm text-red-300">{error.message}</p>
            {error.detail && (
              <p className="mt-2 font-mono text-xs text-secondary break-words">Details: {error.detail}</p>
            )}
            {error.retryable && submitted && (
              <button
                id="diagnose-retry-btn"
                type="button"
                onClick={handleRetry}
                className="halite-btn mt-3 text-sm"
              >
                Try again
              </button>
            )}
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div role="status" className="halite-card p-8 text-center">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
            <p className="mt-3 font-sans text-sm text-secondary">
              Querying graph and fleet records…
            </p>
            <p className="mt-1 font-sans text-xs text-secondary">
              A fresh diagnosis calls the language model and can take up to a minute on the shared service.
            </p>
          </div>
        )}

        {/* Result panel */}
        {result && !loading && (
          <>
            {/* Which asset and symptom this answer belongs to */}
            {submitted && (
              <p className="font-sans text-xs text-secondary px-1">
                Diagnosis for <span className="text-primary font-medium">{submitted.asset.tail_number}</span>
                {' — '}&ldquo;{submitted.symptom}&rdquo;
              </p>
            )}

            {/* Context transparency line */}
            <p className="font-sans text-xs text-secondary px-1">
              Answered from{' '}
              <span className="text-accent font-medium">{result.context_size?.asset_records ?? 0}</span>{' '}
              records on this asset and{' '}
              <span className="text-accent font-medium">{result.context_size?.fleet_records ?? 0}</span>{' '}
              fleet-wide matches across{' '}
              <span className="text-accent font-medium">{result.context_size?.fleet_assets ?? 0}</span>{' '}
              assets.
              {typeof result.context_size?.wall_clock_s === 'number' &&
                ` Server time ${result.context_size.wall_clock_s.toFixed(1)} s.`}
            </p>

            {/* Insufficient evidence: never imply a conclusion */}
            {insufficientEvidence && (
              <div id="insufficient-evidence" role="status" className="halite-card border border-amber-500/30 bg-amber-500/5 p-5">
                <p className="font-sans text-sm font-medium text-amber-400">Insufficient evidence</p>
                <p className="mt-1 font-sans text-sm text-primary">
                  Halite found no supporting service records for this symptom, on this aircraft or across the fleet,
                  so it is not offering an inspection order. Try describing the symptom differently, or choose another aircraft.
                </p>
              </div>
            )}

            {/* Warnings reported by the diagnostic service */}
            {warnings.length > 0 && (
              <section id="diagnostic-warnings" role="status" className="halite-card border border-amber-500/30 bg-amber-500/5 p-4">
                <h3 className="font-sans text-sm font-medium text-amber-400">Warnings</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 font-sans text-sm text-primary">
                  {warnings.map((w, i) => (
                    <li key={`${i}-${w}`}>{w}</li>
                  ))}
                </ul>
              </section>
            )}

            {/* 1. Ranked checks */}
            {!insufficientEvidence && (
              <section className="halite-card p-6">
                <h3 className="font-brand text-primary mb-4">Ranked Inspection Order</h3>
                {rankedChecks.length === 0 ? (
                  <p className="font-sans text-sm text-secondary">No ranked components found.</p>
                ) : (
                  <ol id="ranked-checks-list" className="space-y-3">
                    {rankedChecks.map((check, i) => (
                      <li key={`${check.part_name}-${i}`} className="flex items-start gap-4">
                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/10 text-sm font-bold text-accent">
                          {i + 1}
                        </span>
                        <div className="flex-1">
                          <div className="flex items-baseline gap-3">
                            <span className="font-sans font-medium text-primary">{check.part_name}</span>
                            <span className="font-sans text-xs text-secondary">
                              seen in {check.evidence_count} prior case{check.evidence_count !== 1 ? 's' : ''}
                            </span>
                            {typeof check.score === 'number' && (
                              <span
                                className="font-sans text-xs text-secondary"
                                title="Heuristic ordering weight from historical evidence. It is not a probability or calibrated confidence."
                              >
                                evidence score (heuristic) {check.score.toFixed(2)}
                              </span>
                            )}
                          </div>
                          <p className="mt-0.5 font-sans text-xs text-secondary">
                            sources: {(check.sources ?? []).join(', ') || 'n/a'}
                          </p>
                          {(check.evidence_record_ids ?? []).length > 0 && (
                            <p className="mt-0.5 font-sans text-xs text-secondary">
                              records:{' '}
                              {(expandedIds[i] ? check.evidence_record_ids : check.evidence_record_ids.slice(0, MAX_IDS_PER_CHECK)).map((rid, k) => (
                                <span key={rid}>
                                  {k > 0 && ', '}
                                  {evidenceById[rid] ? (
                                    <button
                                      type="button"
                                      className="font-mono text-accent hover:underline"
                                      onClick={() => openRecord(evidenceById[rid])}
                                    >
                                      {rid}
                                    </button>
                                  ) : (
                                    <span className="font-mono">{rid}</span>
                                  )}
                                </span>
                              ))}
                              {check.evidence_record_ids.length > MAX_IDS_PER_CHECK && (
                                <button
                                  type="button"
                                  className="ml-1 text-accent hover:underline"
                                  onClick={() => setExpandedIds(s => ({ ...s, [i]: !s[i] }))}
                                >
                                  {expandedIds[i]
                                    ? 'show fewer'
                                    : `+${check.evidence_record_ids.length - MAX_IDS_PER_CHECK} more`}
                                </button>
                              )}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
              </section>
            )}

            {/* The ranking is computed from the graph; the written explanation comes from the model.
                If the model returned nothing, say so rather than silently showing less. */}
            {!insufficientEvidence && rankedChecks.length > 0 && !explanation?.text && (
              <div id="no-explanation" role="status" className="halite-card border border-amber-500/30 bg-amber-500/5 p-4">
                <p className="font-sans text-sm font-medium text-amber-400">No written explanation returned</p>
                <p className="mt-1 font-sans text-sm text-primary">
                  The language model did not return an explanation for this request, so no narrative or citations are shown.
                  The ranking above is computed from historical records alone. Try again, or rephrase the symptom.
                </p>
              </div>
            )}

            {/* The model's text is always shown when the backend returns it. When there are no
                supporting records it is labelled as unsupported rather than hidden. */}
            {explanation?.text && (
              <section className="halite-card p-6">
                <h3 className="font-brand text-primary mb-3">Analysis</h3>
                {insufficientEvidence && (
                  <p id="unsupported-analysis" className="mb-2 font-sans text-xs text-amber-400">
                    No supporting records were found. The text below was returned by the model and is not backed by retrieved evidence.
                  </p>
                )}
                <p className="font-sans text-sm text-primary leading-relaxed whitespace-pre-wrap">
                  {splitUnverified(explanation.text).map((seg, k) =>
                    seg.flagged ? (
                      <mark
                        key={k}
                        data-unverified="true"
                        className="rounded bg-amber-500/20 px-1 font-mono text-xs text-amber-400"
                      >
                        {seg.text}
                      </mark>
                    ) : (
                      <Fragment key={k}>{seg.text}</Fragment>
                    )
                  )}
                </p>
                {invalidIds.length > 0 ? (
                  <p className="mt-2 font-sans text-xs text-amber-400">
                    ⚠ {invalidIds.length} unverified ID(s) were flagged and marked [UNVERIFIED].
                  </p>
                ) : citationsAllValid === false ? (
                  <p className="mt-2 font-sans text-xs text-amber-400">
                    ⚠ The citation check did not pass, so these references are not shown as verified.
                  </p>
                ) : validIds.length > 0 ? (
                  <p id="citation-status" className="mt-2 font-sans text-xs text-secondary">
                    ✓ {validIds.length} cited record ID{validIds.length !== 1 ? 's' : ''} verified against the graph.
                    This confirms the records exist, not that every statement is supported by them.
                  </p>
                ) : null}
              </section>
            )}

            {/* 2. Evidence cards */}
            {evidence.length > 0 && (
              <section className="halite-card p-6">
                <h3 className="font-brand text-primary mb-4">Evidence Records</h3>
                <div id="evidence-cards" className="space-y-3">
                  {evidence.map(ev => (
                    <div
                      key={ev.record_id}
                      className={`rounded-lg border p-3 ${
                        ev.is_superseded
                          ? 'border-amber-500/30 bg-amber-500/5 opacity-70'
                          : 'border-theme bg-surface'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <button
                          className="font-sans text-sm font-medium text-accent hover:underline"
                          onClick={() => {
                            const assetUuid = assets.find(a => a.tail_number === ev.asset_id)?.id || ev.asset_id;
                            navigate(`/app/asset-history/${assetUuid}#${ev.record_id}`);
                          }}
                        >
                          {ev.record_id}
                        </button>
                        {ev.is_superseded && (
                          <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-500">
                            superseded
                          </span>
                        )}
                      </div>
                      <p className="mt-1 font-sans text-xs text-secondary">
                        {ev.asset_id} · {ev.occurred_at} · {ev.part_name}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 3. Rare prior cases (collapsed) */}
            {rareCases.length > 0 && (
              <section className="halite-card overflow-hidden">
                <button
                  id="rare-cases-toggle"
                  onClick={() => setRareExpanded(r => !r)}
                  className="flex w-full items-center justify-between px-6 py-4 text-left transition hover:bg-accent/5"
                >
                  <span className="font-brand text-primary">
                    Uncommon —{' '}
                    <span className="font-sans text-sm text-secondary">
                      {rareCases.length} occurrence{rareCases.length !== 1 ? 's' : ''} in the corpus
                    </span>
                  </span>
                  {rareExpanded
                    ? <ChevronUpIcon className="h-4 w-4 text-secondary" />
                    : <ChevronDownIcon className="h-4 w-4 text-secondary" />}
                </button>
                {rareExpanded && (
                  <div className="border-t border-theme px-6 py-4 space-y-3">
                    {rareCases.map(rc => (
                      <div key={rc.record_id} className="rounded-lg border border-accent/20 bg-accent/5 p-3">
                        <p className="font-sans text-sm font-medium text-accent">{rc.record_id}</p>
                        <p className="mt-1 font-sans text-xs text-secondary">
                          {rc.asset_id} · {rc.occurred_at} · {rc.part_name}
                        </p>
                        {rc.text && (
                          <p className="mt-1 font-sans text-xs text-primary">{rc.text}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}

            <p id="safety-notice" className="px-1 font-sans text-xs text-secondary">
              Decision support only. This ranking reflects how often components appear in historical records,
              not a calibrated probability. Approved maintenance documentation and qualified personnel remain authoritative.
            </p>
          </>
        )}

        {/* Empty state */}
        {!result && !loading && !error && (
          <div className="halite-card p-12 text-center">
            <MagnifyingGlassIcon className="mx-auto h-12 w-12 text-accent/30" />
            <h3 className="mt-4 font-brand text-lg text-primary">No diagnostic yet</h3>
            <p className="mt-2 font-sans text-sm text-secondary">
              Select an aircraft and describe the symptom to get a ranked inspection order
              backed by fleet-wide evidence from the graph.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

const SESSION_KEY = 'halite-diagnostic-copilot-sessions';
const EMPTY_CASE = {
  symptoms: [],
  observations: [],
  checks_done: [],
  ruled_out: [],
  open_questions: [],
};

function loadSessions() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(SESSION_KEY) || '[]');
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function storeSessions(sessions) {
  try {
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(sessions));
    return true;
  } catch {
    return false;
  }
}

function copilotError(err) {
  const described = describeDiagnosticError(err);
  if (err?.response?.status === 404) {
    return { ...described, title: 'Unknown aircraft', message: 'The selected aircraft no longer exists in the loaded corpus.' };
  }
  return described;
}

function InvestigationUpdates({ delta = {}, rankedChecks = [], evidence = [], openRecord }) {
  const safeDelta = delta ?? {};
  const movedUp = safeDelta.moved_up ?? [];
  const movedDown = safeDelta.moved_down ?? [];
  const introduced = safeDelta.new ?? [];
  const dropped = safeDelta.dropped ?? [];
  const newlyCited = [...new Set(safeDelta.newly_cited_records ?? [])];
  const movementCount = movedUp.length + movedDown.length + introduced.length + dropped.length;
  const introducedByPart = new Map(introduced.map(item => [item.part_name, item.rank]));
  const initialRanking = rankedChecks.length > 0
    && introduced.length >= rankedChecks.length
    && rankedChecks.every(check => introducedByPart.get(check.part_name) === check.rank)
    && movedUp.length === 0
    && movedDown.length === 0
    && dropped.length === 0;
  const initialRankingCount = Math.max(rankedChecks.length, introduced.length);
  const displayedRankingCount = rankedChecks.length;
  const topChecks = rankedChecks.slice(0, 3);
  const evidenceById = Object.fromEntries(evidence.map(record => [record.record_id, record]));
  const visibleEvidenceIds = initialRanking ? [] : newlyCited.slice(0, 3);
  const remainingEvidenceIds = initialRanking ? newlyCited : newlyCited.slice(3);

  const movements = [
    ...movedUp.map(item => ({
      ...item,
      kind: 'up',
      label: 'Moved up',
      symbol: '↑',
      position: `Rank ${item.from_rank} → Rank ${item.to_rank}`,
      className: 'border-accent/35 bg-accent/5',
    })),
    ...introduced.map(item => ({
      ...item,
      kind: 'new',
      label: 'Newly introduced',
      symbol: '+',
      position: `Entered at rank ${item.rank}`,
      className: 'border-sky-500/35 bg-sky-500/5',
    })),
    ...movedDown.map(item => ({
      ...item,
      kind: 'down',
      label: 'Moved down',
      symbol: '↓',
      position: `Rank ${item.from_rank} → Rank ${item.to_rank}`,
      className: 'border-amber-500/35 bg-amber-500/5',
    })),
    ...dropped.map(item => ({
      ...item,
      kind: 'dropped',
      label: 'Dropped from ranking',
      symbol: '×',
      position: `Previously rank ${item.from_rank} · no longer ranked`,
      className: 'border-theme bg-page/20',
    })),
  ];
  const prominent = movements.slice(0, 3);
  const remaining = movements.slice(3);

  const renderMovement = item => (
    <li key={`${item.kind}-${item.part_name}`} className={`rounded-lg border p-3 ${item.className}`}>
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-current font-sans text-sm font-bold text-accent">
          {item.symbol}
        </span>
        <div className="min-w-0">
          <p className="font-sans text-sm font-medium text-primary">{item.part_name}</p>
          <p className="mt-0.5 flex flex-wrap gap-x-1 font-sans text-xs text-secondary">
            <span className="font-medium text-primary">{item.label}</span>
            <span aria-hidden="true">·</span>
            <span>{item.position}</span>
          </p>
        </div>
      </div>
    </li>
  );

  const renderEvidenceId = recordId => evidenceById[recordId] ? (
    <button
      key={recordId}
      type="button"
      onClick={() => openRecord(evidenceById[recordId])}
      className="rounded border border-theme px-2 py-1 font-mono text-xs text-accent hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      {recordId}
    </button>
  ) : (
    <span key={recordId} className="rounded border border-theme px-2 py-1 font-mono text-xs text-secondary">
      {recordId}
    </span>
  );

  let summary = 'Ranking unchanged after this update.';
  if (movementCount > 0) {
    summary = `${movementCount} ranking update${movementCount === 1 ? '' : 's'} from the previous turn.`;
  } else if (newlyCited.length > 0) {
    summary = 'Ranking unchanged; new supporting records were added.';
  }

  return (
    <section aria-label="Investigation Updates" className="rounded-xl border border-accent/30 bg-accent/[0.04] p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="font-brand text-base text-primary">Investigation Updates</h4>
        {!initialRanking && movementCount === 0 && (
          <span className="rounded-full border border-theme px-2 py-0.5 font-sans text-[11px] font-medium uppercase tracking-wide text-secondary">
            No rank change
          </span>
        )}
      </div>

      {initialRanking ? (
        <div className="mt-2 space-y-3">
          <div>
            <p className="font-sans text-sm font-semibold text-primary">Initial ranking established</p>
            <p className="mt-0.5 font-sans text-xs text-secondary">
              {initialRankingCount} ranked component{initialRankingCount === 1 ? '' : 's'}
              {' · '}{displayedRankingCount} displayed below
            </p>
          </div>

          {topChecks.length > 0 && (
            <div>
              <p className="eyebrow">Top checks</p>
              <ol className="mt-1 flex flex-wrap gap-2">
                {topChecks.map(check => (
                  <li key={check.part_name} className="rounded border border-theme bg-surface px-2 py-1 font-sans text-xs text-primary">
                    <span className="mr-1 text-secondary">#{check.rank}</span>{check.part_name}
                  </li>
                ))}
              </ol>
            </div>
          )}

          <p className="font-sans text-xs text-secondary">
            {newlyCited.length} newly cited evidence record{newlyCited.length === 1 ? '' : 's'}
          </p>
        </div>
      ) : (
        <p className="mt-1 font-sans text-sm text-secondary">{summary}</p>
      )}

      {!initialRanking && prominent.length > 0 && (
        <ul aria-label="Most important ranking updates" className="mt-3 grid gap-2 sm:grid-cols-2">
          {prominent.map(renderMovement)}
        </ul>
      )}

      {!initialRanking && remaining.length > 0 && (
        <details className="mt-3 rounded-lg border border-theme px-3 py-2">
          <summary className="cursor-pointer font-sans text-sm font-medium text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
            Show {remaining.length} more ranking update{remaining.length === 1 ? '' : 's'}
          </summary>
          <ul aria-label="Additional ranking updates" className="mt-3 grid gap-2 sm:grid-cols-2">
            {remaining.map(renderMovement)}
          </ul>
        </details>
      )}

      {newlyCited.length > 0 && (
        <div className="mt-3 border-t border-theme pt-3">
          {!initialRanking && (
            <>
              <p className="eyebrow">New supporting records</p>
              <p className="mt-1 font-sans text-xs text-secondary">
                {newlyCited.length} newly cited evidence record{newlyCited.length === 1 ? '' : 's'}
              </p>
              <div aria-label="Newly cited evidence records" className="mt-2 flex flex-wrap gap-2">
                {visibleEvidenceIds.map(renderEvidenceId)}
              </div>
            </>
          )}

          {remainingEvidenceIds.length > 0 && (
            <details className={initialRanking ? '' : 'mt-2'}>
              <summary className="cursor-pointer font-sans text-xs font-medium text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
                {initialRanking
                  ? `View ${remainingEvidenceIds.length} evidence record ID${remainingEvidenceIds.length === 1 ? '' : 's'}`
                  : `Show ${remainingEvidenceIds.length} more evidence record${remainingEvidenceIds.length === 1 ? '' : 's'}`}
              </summary>
              <div aria-label={initialRanking ? 'Initial evidence records' : 'Additional evidence records'} className="mt-2 flex flex-wrap gap-2">
                {remainingEvidenceIds.map(renderEvidenceId)}
              </div>
            </details>
          )}
        </div>
      )}
    </section>
  );
}

const LIVE_RANKING_PREVIEW_COUNT = 5;
const RANKING_TRANSITION_MS = 320;
const MOVEMENT_INDICATOR_MS = 2400;

function componentIdentity(check) {
  return check?.part_name;
}

function hasRankingChanges(delta = {}) {
  return ['moved_up', 'moved_down', 'new', 'dropped']
    .some(field => (delta?.[field] ?? []).length > 0);
}

function prefersReducedMotion() {
  return typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function rankingAnnouncement(delta = {}) {
  const changes = [];
  for (const item of delta.moved_up ?? []) {
    const places = Math.max(0, Number(item.from_rank) - Number(item.to_rank));
    changes.push(`${item.part_name} moved up ${places} ${places === 1 ? 'place' : 'places'}, from rank ${item.from_rank} to ${item.to_rank}.`);
  }
  for (const item of delta.moved_down ?? []) {
    const places = Math.max(0, Number(item.to_rank) - Number(item.from_rank));
    changes.push(`${item.part_name} moved down ${places} ${places === 1 ? 'place' : 'places'}, from rank ${item.from_rank} to ${item.to_rank}.`);
  }
  for (const item of delta.new ?? []) changes.push(`${item.part_name} entered at rank ${item.rank}.`);
  for (const item of delta.dropped ?? []) changes.push(`${item.part_name} was removed from the current ranking.`);
  if ((delta.dropped ?? []).length > 0) {
    changes.push('Other components may move up because a check was removed, not because its failure probability increased.');
  }
  return changes.length > 0 ? `Ranking updated. ${changes.join(' ')}` : '';
}

function movementForCheck(partName, delta = {}) {
  const movedUp = (delta?.moved_up ?? []).find(item => item.part_name === partName);
  if (movedUp) {
    const places = Math.max(0, Number(movedUp.from_rank) - Number(movedUp.to_rank));
    return { label: `Moved up ${places}`, detail: `Rank ${movedUp.from_rank} → Rank ${movedUp.to_rank}`, symbol: '↑', kind: 'moved-up' };
  }
  const movedDown = (delta?.moved_down ?? []).find(item => item.part_name === partName);
  if (movedDown) {
    const places = Math.max(0, Number(movedDown.to_rank) - Number(movedDown.from_rank));
    return { label: `Moved down ${places}`, detail: `Rank ${movedDown.from_rank} → Rank ${movedDown.to_rank}`, symbol: '↓', kind: 'moved-down' };
  }
  const introduced = (delta?.new ?? []).find(item => item.part_name === partName);
  if (introduced) return { label: 'New', detail: `Entered at rank ${introduced.rank}`, symbol: '+', kind: 'new' };
  return null;
}

function scoreLabel(score) {
  const numericScore = Number(score);
  return Number.isFinite(numericScore) ? numericScore.toFixed(2) : 'Not available';
}

function RankingItem({ check, delta, showMovement, selected, onSelect, onMarkDone, onRuleOut, setItemRef, hidden = false }) {
  const movement = check.__exiting
    ? { label: 'Removed', detail: `Previously rank ${check.rank}`, symbol: '−', kind: 'dropped' }
    : showMovement ? movementForCheck(check.part_name, delta) : null;
  return (
    <li
      ref={setItemRef}
      hidden={hidden}
      data-component-id={componentIdentity(check)}
      data-ranking-animation={movement?.kind ?? 'none'}
      className={`overflow-hidden rounded-lg border bg-surface p-3 will-change-transform ${
        check.__exiting ? 'border-red-500/50' : selected ? 'border-accent ring-1 ring-accent/30' : 'border-theme'
      }`}
    >
      <div className="flex items-start gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-accent/50 font-brand text-sm text-accent" aria-label={`Rank ${check.rank}`}>
          {check.rank}
        </span>
        <div className="min-w-0 flex-1">
          {!check.__exiting && onSelect ? (
            <button
              type="button"
              aria-label={`Inspect evidence for ${check.part_name}`}
              aria-pressed={selected}
              onClick={() => onSelect(check.part_name)}
              className="block w-full rounded text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <span className="block break-words font-sans text-sm font-semibold text-primary">{check.part_name}</span>
              <span className="mt-0.5 block font-sans text-xs text-secondary">Heuristic score {scoreLabel(check.score)}</span>
              <span className="mt-1 block font-sans text-[11px] font-medium text-accent">{selected ? 'Evidence selected' : 'Inspect evidence'}</span>
            </button>
          ) : (
            <>
              <p className="break-words font-sans text-sm font-semibold text-primary">{check.part_name}</p>
              <p className="mt-0.5 font-sans text-xs text-secondary">Heuristic score {scoreLabel(check.score)}</p>
            </>
          )}
          {movement && (
            <p className="mt-1 flex flex-wrap items-center gap-x-1 font-sans text-xs text-primary">
              <span aria-hidden="true" className="font-semibold text-accent">{movement.symbol}</span>
              <span className="font-medium">{movement.label}</span>
              <span aria-hidden="true">·</span>
              <span>{movement.detail}</span>
            </p>
          )}
          {check.__exiting && (
            <p className="mt-1 font-sans text-xs leading-5 text-secondary">
              Removed from the current ranking. Other checks may shift upward because space was removed, not because their failure probability increased.
            </p>
          )}
          {!check.__exiting && (onMarkDone || onRuleOut) && (
            <div className="mt-2 flex flex-wrap gap-2">
              {onMarkDone && (
                <button type="button" aria-label={`Mark ${check.part_name} done`} onClick={() => onMarkDone(check.part_name)} className="halite-btn text-xs">
                  Mark done
                </button>
              )}
              {onRuleOut && (
                <button type="button" aria-label={`Rule out ${check.part_name}`} onClick={() => onRuleOut(check.part_name)} className="halite-btn text-xs">
                  Rule out
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

function LiveRankingPanel({ response, transitionKey, loading, selectedPartName, inspectorRecords, assets, onSelect, onOpenRecord, onRecordsResolved, onMarkDone, onRuleOut }) {
  const checks = response?.ranked_checks ?? [];
  const [displayChecks, setDisplayChecks] = useState(checks);
  const [expanded, setExpanded] = useState(false);
  const [showMovement, setShowMovement] = useState(false);
  const [announcement, setAnnouncement] = useState('');
  const itemRefs = useRef(new Map());
  const displayChecksRef = useRef(checks);
  const handledTransitionRef = useRef(transitionKey);
  const pendingAnimationRef = useRef(null);
  const animationsRef = useRef([]);
  const removalTimerRef = useRef(null);
  const indicatorTimerRef = useRef(null);

  useEffect(() => {
    displayChecksRef.current = displayChecks;
  }, [displayChecks]);

  useEffect(() => () => {
    animationsRef.current.forEach(animation => animation.cancel());
    clearTimeout(removalTimerRef.current);
    clearTimeout(indicatorTimerRef.current);
  }, []);

  useLayoutEffect(() => {
    const nextChecks = response?.ranked_checks ?? [];
    const currentChecks = displayChecksRef.current.filter(check => !check.__exiting);
    const shouldAnimate = transitionKey !== handledTransitionRef.current
      && currentChecks.length > 0
      && hasRankingChanges(response?.ranking_delta)
      && !prefersReducedMotion();

    handledTransitionRef.current = transitionKey;
    animationsRef.current.forEach(animation => animation.cancel());
    animationsRef.current = [];
    clearTimeout(removalTimerRef.current);
    clearTimeout(indicatorTimerRef.current);
    pendingAnimationRef.current = null;

    if (!shouldAnimate) {
      displayChecksRef.current = nextChecks;
      setDisplayChecks(nextChecks);
      setShowMovement(false);
      setAnnouncement('');
      return;
    }

    const firstPositions = new Map();
    itemRefs.current.forEach((node, identity) => {
      if (!node.hidden) firstPositions.set(identity, node.getBoundingClientRect());
    });

    const nextIdentities = new Set(nextChecks.map(componentIdentity));
    const droppedByIdentity = new Map((response.ranking_delta?.dropped ?? []).map(item => [item.part_name, item]));
    const exiting = currentChecks
      .map((check, index) => ({ check, index }))
      .filter(({ check }) => !nextIdentities.has(componentIdentity(check)) && droppedByIdentity.has(componentIdentity(check)));
    const stagedChecks = nextChecks.map(check => ({ ...check }));
    exiting.forEach(({ check, index }) => {
      stagedChecks.splice(Math.min(index, stagedChecks.length), 0, { ...check, __exiting: true });
    });

    pendingAnimationRef.current = {
      firstPositions,
      nextChecks,
      transitionKey,
      newIdentities: new Set((response.ranking_delta?.new ?? []).map(item => item.part_name)),
      movedUpIdentities: new Set((response.ranking_delta?.moved_up ?? []).map(item => item.part_name)),
      movedDownIdentities: new Set((response.ranking_delta?.moved_down ?? []).map(item => item.part_name)),
    };
    displayChecksRef.current = stagedChecks;
    setDisplayChecks(stagedChecks);
    setShowMovement(true);
    setAnnouncement(rankingAnnouncement(response.ranking_delta));
    indicatorTimerRef.current = setTimeout(() => setShowMovement(false), MOVEMENT_INDICATOR_MS);
  }, [response, transitionKey]);

  useLayoutEffect(() => {
    const pending = pendingAnimationRef.current;
    if (!pending || pending.transitionKey !== transitionKey) return;
    pendingAnimationRef.current = null;

    itemRefs.current.forEach((node, identity) => {
      if (node.hidden || typeof node.animate !== 'function') return;
      const check = displayChecksRef.current.find(item => componentIdentity(item) === identity);
      let keyframes;
      if (check?.__exiting) {
        const height = Math.max(node.getBoundingClientRect().height, node.scrollHeight, 1);
        keyframes = [
          { opacity: 1, maxHeight: `${height}px` },
          { opacity: 0, maxHeight: '0px', paddingTop: '0px', paddingBottom: '0px', marginTop: '0px' },
        ];
      } else {
        const first = pending.firstPositions.get(identity);
        const last = node.getBoundingClientRect();
        const offset = first ? first.top - last.top : 0;
        if (offset) keyframes = [{ transform: `translateY(${offset}px)` }, { transform: 'translateY(0)' }];
        else if (pending.newIdentities.has(identity)) keyframes = [{ opacity: 0, transform: 'translateY(10px)' }, { opacity: 1, transform: 'translateY(0)' }];
        else if (pending.movedUpIdentities.has(identity)) keyframes = [{ transform: 'translateY(16px)' }, { transform: 'translateY(0)' }];
        else if (pending.movedDownIdentities.has(identity)) keyframes = [{ transform: 'translateY(-16px)' }, { transform: 'translateY(0)' }];
      }
      if (keyframes) {
        animationsRef.current.push(node.animate(keyframes, {
          duration: RANKING_TRANSITION_MS,
          easing: 'cubic-bezier(0.2, 0, 0, 1)',
          fill: 'both',
        }));
      }
    });

    removalTimerRef.current = setTimeout(() => {
      animationsRef.current.forEach(animation => animation.cancel());
      displayChecksRef.current = pending.nextChecks;
      setDisplayChecks(pending.nextChecks);
      animationsRef.current = [];
    }, RANKING_TRANSITION_MS);
  }, [displayChecks, transitionKey]);

  const remainingCount = Math.max(0, checks.length - LIVE_RANKING_PREVIEW_COUNT);

  return (
    <section aria-label="Live investigation ranking" className="halite-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Current recommendations</p>
          <h3 className="mt-1 font-brand text-lg text-primary">Live ranking</h3>
        </div>
        {response && <span className="rounded-full border border-accent/40 px-2 py-0.5 font-sans text-[11px] font-medium uppercase tracking-wide text-accent">Latest</span>}
      </div>

      {announcement && <p role="status" aria-live="polite" aria-atomic="true" className="sr-only">{announcement}</p>}

      {!response ? (
        <div className="mt-4 rounded-lg border border-dashed border-theme p-4">
          <p className="font-sans text-sm font-medium text-primary">No completed ranking yet</p>
          <p className="mt-1 font-sans text-xs leading-5 text-secondary">Complete a Copilot turn to populate current inspection recommendations.</p>
        </div>
      ) : checks.length === 0 ? (
        <div className="mt-4 rounded-lg border border-dashed border-theme p-4">
          <p className="font-sans text-sm font-medium text-primary">No active recommendations</p>
          <p className="mt-1 font-sans text-xs leading-5 text-secondary">The latest completed turn did not return ranked checks.</p>
        </div>
      ) : (
        <>
          <p className="mt-2 font-sans text-xs leading-5 text-secondary">
            Latest completed turn · {checks.length} active ranked check{checks.length === 1 ? '' : 's'}
          </p>
          <ol id="additional-current-ranked-checks" aria-label="Current ranked checks" className="mt-3 space-y-2">
            {displayChecks.map((check, index) => (
              <RankingItem
                key={componentIdentity(check)}
                check={check}
                delta={response.ranking_delta}
                showMovement={showMovement}
                selected={selectedPartName === check.part_name}
                onSelect={onSelect}
                onMarkDone={onMarkDone}
                onRuleOut={onRuleOut}
                setItemRef={node => {
                  const identity = componentIdentity(check);
                  if (node) itemRefs.current.set(identity, node);
                  else itemRefs.current.delete(identity);
                }}
                {...(!expanded && index >= LIVE_RANKING_PREVIEW_COUNT ? { hidden: true } : {})}
              />
            ))}
          </ol>
          {showMovement && (response.ranking_delta?.dropped ?? []).length > 0 && (
            <p className="mt-2 font-sans text-[11px] leading-4 text-secondary">
              Remaining checks may shift upward because a ranked item was removed; this does not mean their failure probability increased.
            </p>
          )}
          {remainingCount > 0 && (
            <button
              type="button"
              aria-expanded={expanded}
              aria-controls="additional-current-ranked-checks"
              onClick={() => setExpanded(value => !value)}
              className="mt-3 w-full rounded-lg border border-theme px-3 py-2 text-left font-sans text-sm font-medium text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              {expanded ? 'Show fewer current checks' : `Show ${remainingCount} more current check${remainingCount === 1 ? '' : 's'}`}
            </button>
          )}
        </>
      )}

      {loading && response && <p role="status" className="mt-3 border-t border-theme pt-3 font-sans text-xs text-secondary">Updating after the current case change…</p>}
      <p className="mt-3 border-t border-theme pt-3 font-sans text-[11px] leading-4 text-secondary">Scores are heuristic ranking signals, not failure probabilities or confidence.</p>
      <DiagnosticEvidenceInspector
        response={response}
        selectedPartName={selectedPartName}
        assets={assets}
        onOpenRecord={onOpenRecord}
        initialRecords={inspectorRecords}
        onRecordsResolved={onRecordsResolved}
      />
    </section>
  );
}

function TurnSnapshot({ response, turnNumber, isCurrent, openRecord }) {
  const evidence = response.evidence ?? [];
  const evidenceById = Object.fromEntries(evidence.map(record => [record.record_id, record]));
  const rankedChecks = response.ranked_checks ?? [];
  const invalidIds = response.citation_validation?.invalid_ids ?? [];
  const validIds = response.citation_validation?.valid_ids ?? [];

  return (
    <details className="rounded-lg border border-theme px-3 py-2">
      <summary className="cursor-pointer font-sans text-sm font-medium text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
        {isCurrent ? 'Current turn details' : 'Historical ranking snapshot'} · Turn {turnNumber}
      </summary>
      <div className="mt-3 space-y-4 border-t border-theme pt-3">
        <div>
          <h4 className="eyebrow mb-2">Full ranked checks</h4>
          {rankedChecks.length === 0 ? <p className="font-sans text-xs text-secondary">No ranked checks returned for this turn.</p> : (
            <ol className="space-y-2">
              {rankedChecks.map(check => (
                <li key={check.part_name} className="rounded border border-theme p-2">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-sans text-sm text-primary">
                    <span>{check.rank}. {check.part_name}</span>
                    <span className="text-xs text-secondary">Heuristic score {scoreLabel(check.score)}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {(check.evidence_record_ids ?? []).map(recordId => {
                      const record = evidenceById[recordId];
                      return record ? (
                        <button key={recordId} type="button" onClick={() => openRecord(record)} className="break-all font-mono text-xs text-accent hover:underline">{recordId}</button>
                      ) : <span key={recordId} className="break-all font-mono text-xs text-secondary">{recordId}</span>;
                    })}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>

        <div>
          <h4 className="eyebrow mb-2">Turn evidence</h4>
          {evidence.length === 0 ? <p className="font-sans text-xs text-secondary">No evidence records returned for this turn.</p> : (
            <div className="flex flex-wrap gap-2">
              {evidence.map(record => (
                <button
                  key={record.record_id}
                  type="button"
                  onClick={() => openRecord(record)}
                  className={`break-all rounded border px-2 py-1 font-mono text-xs ${record.is_superseded ? 'border-amber-500/40 text-amber-400' : 'border-theme text-accent'}`}
                >
                  {record.record_id}{record.is_superseded ? ' · superseded' : ''}
                </button>
              ))}
            </div>
          )}
        </div>

        <p className="font-sans text-xs text-secondary">
          {invalidIds.length > 0
            ? `Not verified against current evidence: ${invalidIds.join(', ')}`
            : validIds.length > 0
              ? `Verified record IDs: ${validIds.join(', ')}`
              : 'No record IDs cited in the narrative.'}
        </p>
      </div>
    </details>
  );
}

function Copilot() {
  const navigate = useNavigate();
  const [restoredWorkspace] = useState(loadActiveDiagnosticWorkspace);
  const conversationHistoryRef = useRef(null);
  const investigationRailRef = useRef(null);
  const followConversationRef = useRef(restoredWorkspace?.scroll.followConversation ?? true);
  const workspaceScrollRef = useRef({
    conversation: restoredWorkspace?.scroll.conversation ?? 0,
    investigation: restoredWorkspace?.scroll.investigation ?? 0,
  });
  const restoreScrollRef = useRef(Boolean(restoredWorkspace));
  const activeWorkspaceRef = useRef(null);
  const scrollPersistTimerRef = useRef(null);
  const explicitClearRef = useRef(false);
  const [assets, setAssets] = useState([]);
  const [assetId, setAssetId] = useState(restoredWorkspace?.assetId ?? '');
  const [message, setMessage] = useState(restoredWorkspace?.draft ?? '');
  const [thread, setThread] = useState(restoredWorkspace?.thread ?? []);
  const [caseState, setCaseState] = useState(restoredWorkspace?.caseState ?? EMPTY_CASE);
  const [sessionId, setSessionId] = useState(restoredWorkspace?.sessionId ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [failedTurn, setFailedTurn] = useState(null);
  const [sessions, setSessions] = useState(loadSessions);
  const [storageWarning, setStorageWarning] = useState('');
  const [rankingTransitionKey, setRankingTransitionKey] = useState(0);
  const [selectedPartName, setSelectedPartName] = useState(restoredWorkspace?.selectedPartName ?? null);
  const [inspectorRecords, setInspectorRecords] = useState(restoredWorkspace?.inspectorRecords ?? {});

  activeWorkspaceRef.current = {
    assetId,
    draft: message,
    thread: loading && thread.at(-1)?.role === 'user' ? thread.slice(0, -1) : thread,
    caseState,
    sessionId,
    selectedPartName,
    inspectorRecords,
    scroll: {
      ...workspaceScrollRef.current,
      followConversation: followConversationRef.current,
    },
  };

  useEffect(() => {
    maintenanceAPI.assets().then(res => setAssets(res.data)).catch(() => {});
  }, []);

  const latestAssistantIndex = thread.reduce((latestIndex, item, index) => item.role === 'assistant' ? index : latestIndex, -1);
  const latest = latestAssistantIndex >= 0 ? thread[latestAssistantIndex].response : null;

  useLayoutEffect(() => {
    if (!restoreScrollRef.current) return;
    if (conversationHistoryRef.current) {
      conversationHistoryRef.current.scrollTop = workspaceScrollRef.current.conversation;
    }
    if (investigationRailRef.current) {
      investigationRailRef.current.scrollTop = workspaceScrollRef.current.investigation;
    }
    restoreScrollRef.current = false;
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      const stored = storeActiveDiagnosticWorkspace(activeWorkspaceRef.current);
      if (!stored) setStorageWarning('Browser storage is unavailable. The active investigation will not survive navigation or refresh.');
      explicitClearRef.current = false;
    }, 120);
    return () => clearTimeout(timer);
  }, [assetId, message, thread, caseState, sessionId, selectedPartName, inspectorRecords]);

  useEffect(() => () => {
    clearTimeout(scrollPersistTimerRef.current);
    if (explicitClearRef.current) clearActiveDiagnosticWorkspace();
    else storeActiveDiagnosticWorkspace(activeWorkspaceRef.current);
  }, []);

  useEffect(() => {
    const history = conversationHistoryRef.current;
    if (!history || !latest || !followConversationRef.current) return;
    const reducedMotion = typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (typeof history.scrollTo === 'function') {
      history.scrollTo({ top: history.scrollHeight, behavior: reducedMotion ? 'auto' : 'smooth' });
    } else {
      history.scrollTop = history.scrollHeight;
    }
  }, [latest]);

  const trackConversationPosition = (event) => {
    const history = event.currentTarget;
    const distanceFromBottom = history.scrollHeight - history.scrollTop - history.clientHeight;
    followConversationRef.current = distanceFromBottom <= 96;
    workspaceScrollRef.current.conversation = history.scrollTop;
    activeWorkspaceRef.current.scroll = {
      ...workspaceScrollRef.current,
      followConversation: followConversationRef.current,
    };
    clearTimeout(scrollPersistTimerRef.current);
    scrollPersistTimerRef.current = setTimeout(() => storeActiveDiagnosticWorkspace(activeWorkspaceRef.current), 120);
  };

  const trackInvestigationPosition = (event) => {
    workspaceScrollRef.current.investigation = event.currentTarget.scrollTop;
    activeWorkspaceRef.current.scroll = {
      ...workspaceScrollRef.current,
      followConversation: followConversationRef.current,
    };
    clearTimeout(scrollPersistTimerRef.current);
    scrollPersistTimerRef.current = setTimeout(() => storeActiveDiagnosticWorkspace(activeWorkspaceRef.current), 120);
  };

  const persist = (nextSessions) => {
    setSessions(nextSessions);
    if (!storeSessions(nextSessions)) {
      setStorageWarning('Session storage is unavailable. This investigation still works, but cannot be saved locally.');
    }
  };

  const sendTurn = async (turnMessage, options = {}) => {
    const text = turnMessage.trim();
    if (!text || loading) return;
    const stateForTurn = options.caseState ?? caseState;
    if (!options.retry) setThread(items => [...items, { role: 'user', content: text }]);
    setLoading(true);
    setError(null);
    setFailedTurn(null);
    try {
      const response = await maintenanceAPI.copilotTurn({
        ...(sessionId ? { session_id: sessionId } : {}),
        ...(assetId ? { asset_id: assetId } : {}),
        message: text,
        case_state: stateForTurn,
      });
      const data = response.data;
      setSessionId(data.session_id);
      setCaseState(data.case_state ?? stateForTurn);
      setThread(items => [...items, { role: 'assistant', response: data, content: data.reply }]);
      if (latest && hasRankingChanges(data.ranking_delta)) {
        setRankingTransitionKey(key => key + 1);
      }
      setMessage('');
    } catch (requestError) {
      setError(copilotError(requestError));
      setFailedTurn({ message: text, caseState: stateForTurn });
    } finally {
      setLoading(false);
    }
  };

  const submit = (event) => {
    event.preventDefault();
    sendTurn(message);
  };

  const newInvestigation = () => {
    explicitClearRef.current = true;
    clearTimeout(scrollPersistTimerRef.current);
    clearActiveDiagnosticWorkspace();
    followConversationRef.current = true;
    workspaceScrollRef.current = { conversation: 0, investigation: 0 };
    setThread([]);
    setCaseState(EMPTY_CASE);
    setSessionId(null);
    setMessage('');
    setError(null);
    setFailedTurn(null);
    setAssetId('');
    setSelectedPartName(null);
    setInspectorRecords({});
  };

  const saveSession = () => {
    if (!thread.length) return;
    const id = sessionId || `local-${Date.now()}`;
    const firstMessage = thread.find(item => item.role === 'user')?.content || 'Investigation';
    const snapshot = {
      id,
      title: firstMessage.slice(0, 48),
      savedAt: new Date().toISOString(),
      assetId,
      thread,
      caseState,
      selectedPartName,
    };
    persist([snapshot, ...sessions.filter(item => item.id !== id)]);
    setSessionId(id);
  };

  const resumeSession = (saved) => {
    followConversationRef.current = true;
    workspaceScrollRef.current = { conversation: 0, investigation: 0 };
    if (investigationRailRef.current) investigationRailRef.current.scrollTop = 0;
    setSessionId(saved.id);
    setAssetId(saved.assetId || '');
    setThread(Array.isArray(saved.thread) ? saved.thread : []);
    setCaseState(saved.caseState || EMPTY_CASE);
    setSelectedPartName(saved.selectedPartName || null);
    setInspectorRecords({});
    setMessage('');
    setError(null);
  };

  const deleteSession = (id) => {
    persist(sessions.filter(item => item.id !== id));
    if (sessionId === id) newInvestigation();
  };

  const updateCaseAndRerun = (field, value) => {
    const next = {
      ...caseState,
      [field]: [...new Set([...(caseState[field] ?? []), value])],
    };
    setCaseState(next);
    sendTurn(`Case update: ${field === 'checks_done' ? 'check completed' : 'ruled out'} ${value}.`, { caseState: next });
  };

  const removeCaseFact = (field, value) => {
    setCaseState(current => ({
      ...current,
      [field]: (current[field] ?? []).filter(item => item !== value),
    }));
  };

  const openRecord = (record) => {
    const uuid = assets.find(asset => asset.tail_number === record.asset_id)?.id || record.asset_id;
    if (conversationHistoryRef.current) workspaceScrollRef.current.conversation = conversationHistoryRef.current.scrollTop;
    if (investigationRailRef.current) workspaceScrollRef.current.investigation = investigationRailRef.current.scrollTop;
    activeWorkspaceRef.current.scroll = {
      ...workspaceScrollRef.current,
      followConversation: followConversationRef.current,
    };
    storeActiveDiagnosticWorkspace(activeWorkspaceRef.current);
    navigate(`/app/asset-history/${uuid}#${record.record_id}`, {
      state: { from: 'diagnostics', returnTo: '/app/diagnostics' },
    });
  };

  const retainInspectorRecords = useCallback((records) => {
    setInspectorRecords(current => {
      const merged = { ...current };
      Object.entries(records).forEach(([recordId, record]) => {
        delete merged[recordId];
        merged[recordId] = record;
      });
      return Object.fromEntries(Object.entries(merged).slice(-MAX_PERSISTED_INSPECTOR_RECORDS));
    });
  }, []);

  return (
    <div data-testid="copilot-layout" className="flex min-h-0 flex-col gap-4 xl:flex-1">
      <section aria-label="Investigation controls" data-testid="copilot-controls" className="halite-card flex shrink-0 flex-wrap items-end gap-3 p-4">
        <label className="min-w-48 flex-1 font-sans text-sm text-primary">
          Aircraft filter
          <select
            aria-label="Aircraft filter"
            value={assetId}
            onChange={event => setAssetId(event.target.value)}
            className="halite-input mt-1 w-full"
          >
            <option value="">All fleet</option>
            {assets.map(asset => (
              <option key={asset.id} value={asset.id}>{asset.tail_number}</option>
            ))}
          </select>
        </label>
        <button type="button" onClick={newInvestigation} className="halite-btn text-sm">New investigation</button>
        <button type="button" onClick={saveSession} disabled={!thread.length} className="halite-btn text-sm disabled:opacity-50">Save session</button>
      </section>

      <div data-testid="copilot-workspace" className="grid min-w-0 items-start gap-5 xl:min-h-0 xl:flex-1 xl:grid-cols-[minmax(0,1fr)_23rem] xl:items-stretch xl:overflow-hidden">
        <main className="order-2 flex min-w-0 flex-col gap-4 xl:order-none xl:col-start-1 xl:row-start-1 xl:h-full xl:min-h-0 xl:overflow-hidden">

        <section aria-label="Diagnostic conversation" className="halite-card min-h-80 p-5 xl:min-h-0 xl:flex-1 xl:overflow-hidden">
          <div
            ref={conversationHistoryRef}
            role="log"
            aria-label="Conversation history"
            aria-live="polite"
            tabIndex="0"
            onScroll={trackConversationPosition}
            data-testid="conversation-history"
            className="space-y-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent xl:h-full xl:min-h-0 xl:overflow-y-auto xl:overscroll-contain xl:pr-2 [overflow-anchor:auto]"
          >
            {thread.length === 0 && (
              <div className="py-12 text-center">
                <h3 className="font-brand text-lg text-primary">Start an evidence-grounded investigation</h3>
                <p className="mt-2 font-sans text-sm text-secondary">Describe a symptom, observation, completed check, or ask about a service record.</p>
              </div>
            )}
            {thread.map((turn, index) => turn.role === 'user' ? (
              <div key={index} className="ml-auto max-w-[85%] rounded-xl bg-accent/10 p-3 font-sans text-sm text-primary">
                {turn.content}
              </div>
            ) : (
              <article key={index} className="space-y-3 rounded-xl border border-theme bg-surface p-4">
                <InvestigationUpdates
                  delta={turn.response.ranking_delta}
                  rankedChecks={turn.response.ranked_checks ?? []}
                  evidence={turn.response.evidence ?? []}
                  openRecord={openRecord}
                />

              {turn.response.llm_status === 'unavailable' || !turn.content ? (
                <div role="alert" className="rounded border border-amber-500/30 bg-amber-500/5 p-3">
                  <p className="font-sans text-sm font-medium text-amber-400">Language model unavailable</p>
                  <p className="font-sans text-xs text-primary">No narrative was invented. Deterministic ranking and evidence remain available in the live ranking and turn details.</p>
                </div>
              ) : (
                <CopilotMarkdown>{turn.content}</CopilotMarkdown>
              )}

              {(turn.response.warnings ?? []).length > 0 && (
                <ul className="list-disc pl-5 font-sans text-xs text-amber-400">
                  {turn.response.warnings.map(warning => <li key={warning}>{warning}</li>)}
                </ul>
              )}

                <TurnSnapshot
                  response={turn.response}
                  turnNumber={thread.slice(0, index + 1).filter(item => item.role === 'assistant').length}
                  isCurrent={index === latestAssistantIndex}
                  openRecord={openRecord}
                />
              </article>
            ))}
            {loading && <div role="status" className="font-sans text-sm text-secondary">Retrieving and reranking the accumulated case…</div>}
          </div>
        </section>

        {error && (
          <div role="alert" className="halite-card border border-red-500/30 bg-red-500/5 p-4">
            <p className="font-sans text-sm font-medium text-red-400">{error.title}</p>
            <p className="font-sans text-sm text-primary">{error.message}</p>
            {error.detail && <p className="mt-1 font-mono text-xs text-secondary">{error.detail}</p>}
            {error.retryable && failedTurn && (
              <button type="button" onClick={() => sendTurn(failedTurn.message, { retry: true, caseState: failedTurn.caseState })} className="halite-btn mt-2 text-sm">Try again</button>
            )}
          </div>
        )}

        <form onSubmit={submit} data-testid="copilot-composer" className="halite-card p-4 xl:shrink-0">
          <label htmlFor="copilot-message" className="eyebrow">Message</label>
          <textarea
            id="copilot-message"
            maxLength={4000}
            value={message}
            onChange={event => setMessage(event.target.value)}
            placeholder="e.g. crack found on drag angle during inspection"
            className="halite-input mt-1 w-full resize-none"
            rows={3}
          />
          <button type="submit" disabled={!message.trim() || loading} className="halite-btn-primary mt-3 disabled:opacity-50">Send</button>
        </form>
        <p className="font-sans text-xs text-secondary xl:shrink-0">Decision support only. Evidence scores are heuristic rankings, not probabilities or confidence.</p>
        </main>

        <aside ref={investigationRailRef} onScroll={trackInvestigationPosition} aria-label="Investigation workspace panels" tabIndex="0" className="order-1 min-w-0 self-start space-y-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent xl:order-none xl:col-start-2 xl:row-start-1 xl:h-full xl:min-h-0 xl:self-stretch xl:overflow-y-auto xl:overscroll-contain xl:pr-1">
          <LiveRankingPanel
            response={latest}
            transitionKey={rankingTransitionKey}
            loading={loading}
            selectedPartName={selectedPartName}
            inspectorRecords={inspectorRecords}
            assets={assets}
            onSelect={setSelectedPartName}
            onOpenRecord={openRecord}
            onRecordsResolved={retainInspectorRecords}
            onMarkDone={partName => updateCaseAndRerun('checks_done', partName)}
            onRuleOut={partName => updateCaseAndRerun('ruled_out', partName)}
          />

        <section className="halite-card p-4">
          <h3 className="font-brand text-primary">Case state</h3>
          {['symptoms', 'observations', 'checks_done', 'ruled_out'].map(field => (
            <div key={field} className="mt-3">
              <h4 className="eyebrow">{field.replace('_', ' ')}</h4>
              {(caseState[field] ?? []).length === 0 ? (
                <p className="font-sans text-xs text-secondary">None</p>
              ) : (
                <ul className="space-y-1">
                  {caseState[field].map(value => (
                    <li key={value} className="flex items-start justify-between gap-2 font-sans text-xs text-primary">
                      <span>{value}</span>
                      <button type="button" aria-label={`Remove ${value}`} onClick={() => removeCaseFact(field, value)} className="text-secondary hover:text-red-400">×</button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </section>

        <section className="halite-card p-4">
          <h3 className="font-brand text-primary">Saved sessions</h3>
          {storageWarning && <p role="status" className="mt-2 font-sans text-xs text-amber-400">{storageWarning}</p>}
          {sessions.length === 0 ? <p className="mt-2 font-sans text-xs text-secondary">No saved sessions.</p> : (
            <ul className="mt-2 space-y-2">
              {sessions.map(saved => (
                <li key={saved.id} className="rounded border border-theme p-2">
                  <button type="button" onClick={() => resumeSession(saved)} className="block w-full text-left font-sans text-xs text-accent">{saved.title}</button>
                  <button type="button" aria-label={`Delete ${saved.title}`} onClick={() => deleteSession(saved.id)} className="mt-1 font-sans text-xs text-red-400">Delete</button>
                </li>
              ))}
            </ul>
          )}
        </section>
        </aside>
      </div>
    </div>
  );
}

export default function Diagnostics() {
  const [tab, setTab] = useState('copilot');
  return (
    <div className="h-full overflow-y-auto xl:flex xl:min-h-0 xl:flex-col xl:overflow-hidden">
      <header className="shrink-0 border-b border-theme px-6 py-4">
        <div className="flex items-center gap-3">
          <MagnifyingGlassIcon className="h-5 w-5 text-accent" />
          <div>
            <h2 className="font-brand text-xl text-primary">Diagnostics</h2>
            <p className="font-sans text-sm text-secondary">Multi-turn, graph-grounded maintenance investigation</p>
          </div>
        </div>
        <div role="tablist" className="mt-4 flex gap-2">
          <button role="tab" aria-selected={tab === 'copilot'} onClick={() => setTab('copilot')} className="halite-btn text-sm">Copilot</button>
          <button role="tab" aria-selected={tab === 'quick'} onClick={() => setTab('quick')} className="halite-btn text-sm">Quick diagnose</button>
        </div>
      </header>
      <div className="mx-auto w-full max-w-[96rem] p-4 sm:p-6 xl:flex xl:min-h-0 xl:flex-1 xl:flex-col">
        {tab === 'copilot' ? <Copilot /> : <QuickDiagnose />}
      </div>
    </div>
  );
}
