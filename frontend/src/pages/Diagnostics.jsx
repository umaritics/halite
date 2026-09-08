import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MagnifyingGlassIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';
import { maintenanceAPI } from '../api/client';

// G4: Diagnostic chat page
// Layout:
//   - Asset selector (searchable dropdown)
//   - Symptom textarea
//   - Response panel: ranked_checks, evidence, rare_cases
//   - Context transparency line

export default function Diagnostics() {
  const navigate = useNavigate();
  const [assets, setAssets] = useState([]);
  const [assetSearch, setAssetSearch] = useState('');
  const [assetDropdownOpen, setAssetDropdownOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [symptom, setSymptom] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedAsset || !symptom.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    setRareExpanded(false);
    try {
      const res = await maintenanceAPI.diagnose(selectedAsset.id, symptom.trim());
      setResult(res.data);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Diagnostic failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
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
          </div>

          <button
            id="diagnose-submit-btn"
            type="submit"
            disabled={!selectedAsset || !symptom.trim() || loading}
            className="halite-btn-primary disabled:opacity-50"
          >
            {loading ? 'Analysing…' : 'Run diagnostic'}
          </button>
        </form>

        {/* Error state */}
        {error && (
          <div className="halite-card border border-red-500/30 bg-red-500/5 p-4">
            <p className="font-sans text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="halite-card p-8 text-center">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
            <p className="mt-3 font-sans text-sm text-secondary">
              Querying graph and fleet records…
            </p>
          </div>
        )}

        {/* Result panel */}
        {result && !loading && (
          <>
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

            {/* 1. Ranked checks */}
            <section className="halite-card p-6">
              <h3 className="font-brand text-primary mb-4">Ranked Inspection Order</h3>
              {result.ranked_checks.length === 0 ? (
                <p className="font-sans text-sm text-secondary">No ranked components found.</p>
              ) : (
                <ol id="ranked-checks-list" className="space-y-3">
                  {result.ranked_checks.map((check, i) => (
                    <li key={check.part_name} className="flex items-start gap-4">
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
                          sources: {check.sources.join(', ')}
                        </p>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </section>

            {/* LLM explanation */}
            {result.explanation && (
              <section className="halite-card p-6">
                <h3 className="font-brand text-primary mb-3">Analysis</h3>
                <p className="font-sans text-sm text-primary leading-relaxed whitespace-pre-wrap">
                  {result.explanation}
                </p>
                {result.citation_validation?.invalid_ids?.length > 0 && (
                  <p className="mt-2 font-sans text-xs text-amber-400">
                    ⚠ {result.citation_validation.invalid_ids.length} unverified ID(s) were flagged and marked [UNVERIFIED].
                  </p>
                )}
              </section>
            )}

            {/* 2. Evidence cards */}
            {result.evidence?.length > 0 && (
              <section className="halite-card p-6">
                <h3 className="font-brand text-primary mb-4">Evidence Records</h3>
                <div id="evidence-cards" className="space-y-3">
                  {result.evidence.map(ev => (
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
                          onClick={() => navigate(`/app/asset-history/${ev.asset_id}`)}
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
            {result.rare_cases?.length > 0 && (
              <section className="halite-card overflow-hidden">
                <button
                  id="rare-cases-toggle"
                  onClick={() => setRareExpanded(r => !r)}
                  className="flex w-full items-center justify-between px-6 py-4 text-left transition hover:bg-accent/5"
                >
                  <span className="font-brand text-primary">
                    Uncommon —{' '}
                    <span className="font-sans text-sm text-secondary">
                      {result.rare_cases.length} occurrence{result.rare_cases.length !== 1 ? 's' : ''} in the corpus
                    </span>
                  </span>
                  {rareExpanded
                    ? <ChevronUpIcon className="h-4 w-4 text-secondary" />
                    : <ChevronDownIcon className="h-4 w-4 text-secondary" />}
                </button>
                {rareExpanded && (
                  <div className="border-t border-theme px-6 py-4 space-y-3">
                    {result.rare_cases.map(rc => (
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
