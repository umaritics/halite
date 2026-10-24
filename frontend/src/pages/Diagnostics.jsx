import { Fragment, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MagnifyingGlassIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';
import { maintenanceAPI } from '../api/client';
import CopilotMarkdown from '../components/CopilotMarkdown';
import { describeDiagnosticError, extractExplanation, splitUnverified } from '../utils/diagnostics';

const MAX_IDS_PER_CHECK = 5;

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

function Copilot() {
  const navigate = useNavigate();
  const [assets, setAssets] = useState([]);
  const [assetId, setAssetId] = useState('');
  const [message, setMessage] = useState('');
  const [thread, setThread] = useState([]);
  const [caseState, setCaseState] = useState(EMPTY_CASE);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [failedTurn, setFailedTurn] = useState(null);
  const [sessions, setSessions] = useState(loadSessions);
  const [storageWarning, setStorageWarning] = useState('');

  useEffect(() => {
    maintenanceAPI.assets().then(res => setAssets(res.data)).catch(() => {});
  }, []);

  const latest = [...thread].reverse().find(item => item.role === 'assistant')?.response;

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
    setThread([]);
    setCaseState(EMPTY_CASE);
    setSessionId(null);
    setMessage('');
    setError(null);
    setFailedTurn(null);
    setAssetId('');
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
    };
    persist([snapshot, ...sessions.filter(item => item.id !== id)]);
    setSessionId(id);
  };

  const resumeSession = (saved) => {
    setSessionId(saved.id);
    setAssetId(saved.assetId || '');
    setThread(Array.isArray(saved.thread) ? saved.thread : []);
    setCaseState(saved.caseState || EMPTY_CASE);
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
    navigate(`/app/asset-history/${uuid}#${record.record_id}`);
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_19rem]">
      <div className="space-y-4">
        <div className="halite-card flex flex-wrap items-end gap-3 p-4">
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
        </div>

        <section aria-label="Diagnostic conversation" className="halite-card min-h-80 space-y-4 p-5">
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
                  <p className="font-sans text-xs text-primary">No narrative was invented. Deterministic ranking and evidence are still shown below.</p>
                </div>
              ) : (
                <CopilotMarkdown>{turn.content}</CopilotMarkdown>
              )}

              {(turn.response.warnings ?? []).length > 0 && (
                <ul className="list-disc pl-5 font-sans text-xs text-amber-400">
                  {turn.response.warnings.map(warning => <li key={warning}>{warning}</li>)}
                </ul>
              )}

              {(turn.response.ranked_checks ?? []).length > 0 && (
                <div>
                  <h4 className="eyebrow mb-2">Ranked checks</h4>
                  <ol className="space-y-2">
                    {turn.response.ranked_checks.map(check => (
                        <li key={check.part_name} className="rounded border border-theme p-2">
                          <div className="flex flex-wrap items-center gap-2 font-sans text-sm text-primary">
                            <span>{check.rank}. {check.part_name}</span>
                            <span className="text-xs text-secondary">evidence score (heuristic) {Number(check.score).toFixed(2)}</span>
                          </div>
                          <div className="mt-1 flex flex-wrap gap-2">
                            {(check.evidence_record_ids ?? []).map(recordId => {
                              const record = (turn.response.evidence ?? []).find(item => item.record_id === recordId);
                              return record ? (
                                <button key={recordId} type="button" onClick={() => openRecord(record)} className="font-mono text-xs text-accent hover:underline">{recordId}</button>
                              ) : <span key={recordId} className="font-mono text-xs text-secondary">{recordId}</span>;
                            })}
                          </div>
                          {index === thread.length - 1 && (
                            <div className="mt-2 flex gap-2">
                              <button type="button" onClick={() => updateCaseAndRerun('checks_done', check.part_name)} className="halite-btn text-xs">Mark done</button>
                              <button type="button" onClick={() => updateCaseAndRerun('ruled_out', check.part_name)} className="halite-btn text-xs">Rule out</button>
                            </div>
                          )}
                        </li>
                    ))}
                  </ol>
                </div>
              )}

              {(turn.response.evidence ?? []).length > 0 && (
                <div>
                  <h4 className="eyebrow mb-2">Evidence</h4>
                  <div className="flex flex-wrap gap-2">
                    {turn.response.evidence.map(record => (
                      <button
                        key={record.record_id}
                        type="button"
                        onClick={() => openRecord(record)}
                        className={`rounded border px-2 py-1 font-mono text-xs ${record.is_superseded ? 'border-amber-500/40 text-amber-400' : 'border-theme text-accent'}`}
                      >
                        {record.record_id}{record.is_superseded ? ' · superseded' : ''}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <p className="font-sans text-xs text-secondary">
                {(turn.response.citation_validation?.invalid_ids ?? []).length > 0
                  ? `Unverified IDs: ${turn.response.citation_validation.invalid_ids.join(', ')}`
                  : (turn.response.citation_validation?.valid_ids ?? []).length > 0
                    ? `Verified record IDs: ${turn.response.citation_validation.valid_ids.join(', ')}`
                    : 'No record IDs cited in the narrative.'}
              </p>
            </article>
          ))}
          {loading && <div role="status" className="font-sans text-sm text-secondary">Retrieving and reranking the accumulated case…</div>}
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

        <form onSubmit={submit} className="halite-card p-4">
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
        <p className="font-sans text-xs text-secondary">Decision support only. Evidence scores are heuristic rankings, not probabilities or confidence.</p>
      </div>

      <aside className="space-y-4">
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
  );
}

export default function Diagnostics() {
  const [tab, setTab] = useState('copilot');
  return (
    <div className="h-full overflow-y-auto">
      <header className="border-b border-theme px-6 py-4">
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
      <div className="mx-auto max-w-6xl p-6">
        {tab === 'copilot' ? <Copilot /> : <QuickDiagnose />}
      </div>
    </div>
  );
}
