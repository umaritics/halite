import { Fragment, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MagnifyingGlassIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';
import { maintenanceAPI } from '../api/client';
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

export default function Diagnostics() {
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
                          </div>
                          <p className="mt-0.5 font-sans text-xs text-secondary">
                            sources: {(check.sources ?? []).join(', ') || 'n/a'}
                          </p>
                          {(check.evidence_record_ids ?? []).length > 0 && (
                            <p className="mt-0.5 font-sans text-xs text-secondary">
                              records:{' '}
                              {check.evidence_record_ids.slice(0, MAX_IDS_PER_CHECK).map((rid, k) => (
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
                              {check.evidence_record_ids.length > MAX_IDS_PER_CHECK &&
                                ` +${check.evidence_record_ids.length - MAX_IDS_PER_CHECK} more`}
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

            {/* LLM explanation: withheld when there is nothing for it to be grounded in */}
            {explanation?.text && !insufficientEvidence && (
              <section className="halite-card p-6">
                <h3 className="font-brand text-primary mb-3">Analysis</h3>
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
