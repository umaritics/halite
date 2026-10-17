import { useEffect, useState } from 'react';
import { SunIcon, MoonIcon } from '@heroicons/react/24/outline';
import { useTheme } from '../context/ThemeContext';
import { healthAPI, maintenanceAPI } from '../api/client';
import HaliteLogo from '../components/HaliteLogo';
import BrandName from '../components/BrandName';

// Mid-I: the software-only tools that used to live here (agent-context export and the
// "Reset knowledge graph" action, which runs a full-graph DETACH DELETE) are no longer
// exposed. A single click on that button would erase the loaded maintenance corpus.
// A row for a /api/health field. Fields the backend did not send are not shown at all,
// so a missing field is never presented as "false" or "no".
function HealthRow({ label, value, warn = false, mono = false }) {
  if (value === undefined || value === null) return null;
  return (
    <div className="flex justify-between items-center">
      <dt className="text-secondary">{label}</dt>
      <dd className={`${mono ? 'font-mono text-xs ' : ''}${warn ? 'text-amber-500' : 'text-accent'}`}>{value}</dd>
    </div>
  );
}

const yesNo = (v) => (typeof v === 'boolean' ? (v ? 'Yes' : 'No') : undefined);

export default function Settings() {
  const { theme, toggleTheme, isDark } = useTheme();
  const [health, setHealth] = useState(null);
  const [analysis, setAnalysis] = useState(null);

  useEffect(() => {
    healthAPI.check().then(({ data }) => setHealth(data)).catch(() => setHealth(null));
    maintenanceAPI.analysisStatus().then(({ data }) => setAnalysis(data)).catch(() => setAnalysis(null));
  }, []);

  return (
    <div className="h-full overflow-y-auto">
      <header className="border-b border-theme px-6 py-4">
        <h2 className="font-brand text-xl text-primary">Settings</h2>
        <p className="font-sans text-sm text-secondary">Appearance and system status</p>
      </header>

      <div className="mx-auto max-w-2xl space-y-6 p-6">
        <section className="halite-card p-6">
          <div className="flex items-center gap-6">
            <HaliteLogo className="h-16 w-16" />
            <div>
              <h3 className="font-brand text-primary">
                <BrandName className="text-accent" /> Theme
              </h3>
              <p className="mt-1 font-sans text-sm text-secondary">
                Burnt orange accent on pure black or white. Toggle for presentations.
              </p>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-between rounded-lg bg-surface p-4">
            <div className="flex items-center gap-3">
              {isDark ? (
                <MoonIcon className="h-5 w-5 text-accent" />
              ) : (
                <SunIcon className="h-5 w-5 text-accent" />
              )}
              <div>
                <p className="font-sans text-sm font-medium text-primary">
                  {isDark ? 'Dark Mode' : 'Light Mode'}
                </p>
                <p className="font-sans text-xs text-[#555555]">Currently using {theme} theme</p>
              </div>
            </div>
            <button
              onClick={toggleTheme}
              className={`relative h-7 w-12 rounded-full transition ${
                isDark ? 'bg-accent' : 'bg-[#CCCCCC]'
              }`}
            >
              <span
                className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition ${
                  isDark ? 'left-5' : 'left-0.5'
                }`}
              />
            </button>
          </div>
        </section>

        <section className="halite-card p-6">
          <h3 className="font-brand text-primary">Conflict-analysis coverage</h3>
          {analysis ? (
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-5">
              {['total', 'unscored', 'scored', 'needs_review', 'reviewed'].map((key) => (
                <div key={key}><dt className="text-secondary">{key.replaceAll('_', ' ')}</dt><dd className="text-xl text-primary">{analysis[key] ?? 0}</dd></div>
              ))}
            </dl>
          ) : <p className="mt-3 text-sm text-secondary">Analysis coverage unavailable.</p>}
        </section>

        <section className="halite-card p-6">
          <h3 className="font-brand text-primary">System Status</h3>
          {health ? (
            <dl className="mt-4 space-y-3 font-sans text-sm">
              <div className="flex justify-between items-center">
                <dt className="text-secondary">Graph Mode</dt>
                <dd>
                  {health.graph_mode === 'memory' ? (
                    <span className="inline-flex items-center rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-500 ring-1 ring-inset ring-amber-500/20">Memory (Demo)</span>
                  ) : (
                    <span className="text-accent">{health.graph_mode}</span>
                  )}
                </dd>
              </div>
              <div className="flex justify-between items-center">
                <dt className="text-secondary">LLM Mode</dt>
                <dd>
                  {health.llm_mode === 'fallback' ? (
                    <span className="inline-flex items-center rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-500 ring-1 ring-inset ring-amber-500/20">Fallback (Stubbed)</span>
                  ) : (
                    <span className="text-accent">{health.llm_mode}</span>
                  )}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-secondary">Pinned Model</dt>
                <dd className="text-accent">{health.model || 'unknown'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-secondary">Maintenance Records</dt>
                <dd className="text-accent">{health.maintenance_record_count || 0} ingested</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-secondary">Confidence Threshold</dt>
                <dd className="text-accent">{health.maint_threshold?.toFixed(2) || '0.50'}</dd>
              </div>
              <HealthRow label="Corpus Loaded" value={yesNo(health.maintenance_corpus_loaded)} warn={health.maintenance_corpus_loaded === false} />
              <HealthRow label="In-Memory Graph" value={yesNo(health.using_memory_graph)} warn={health.using_memory_graph === true} />
              <HealthRow label="Neo4j Configured" value={yesNo(health.neo4j_configured)} warn={health.neo4j_configured === false} />
              <HealthRow label="Groq Configured" value={yesNo(health.groq_configured)} warn={health.groq_configured === false} />
              <HealthRow label="Demo Mode" value={yesNo(health.demo_mode)} warn={health.demo_mode === true} />
              <HealthRow
                label="Model Fallbacks Used"
                value={typeof health.fallback_invocations === 'number' ? health.fallback_invocations : undefined}
                warn={health.fallback_invocations > 0}
              />
              <HealthRow
                label="Deployed Version"
                value={health.git_sha && health.git_sha !== 'unknown' ? String(health.git_sha).slice(0, 8) : undefined}
                mono
              />
            </dl>
          ) : (
            <p className="mt-4 font-sans text-sm text-red-400">Backend not reachable. Start the API server.</p>
          )}
        </section>

        <section className="halite-card p-6">
          <h3 className="font-brand text-primary">
            About <BrandName className="text-accent" />
          </h3>
          <p className="mt-2 font-sans text-sm text-secondary">
            <BrandName className="text-accent" /> turns historical maintenance service records into an
            evidence-aware knowledge graph: it ranks what to investigate next, links each suggestion to
            its source records, and flags records that later reports corrected. It is decision support
            only. Approved maintenance documentation and qualified personnel remain authoritative.
            Built for FAST NUCES FYP.
          </p>
        </section>
      </div>
    </div>
  );
}
