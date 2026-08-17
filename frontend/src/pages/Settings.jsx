import { useEffect, useState } from 'react';
import { SunIcon, MoonIcon } from '@heroicons/react/24/outline';
import { useTheme } from '../context/ThemeContext';
import { healthAPI, graphAPI } from '../api/client';
import HaliteLogo from '../components/HaliteLogo';
import BrandName from '../components/BrandName';

export default function Settings() {
  const { theme, toggleTheme, isDark } = useTheme();
  const [health, setHealth] = useState(null);
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState(null);

  useEffect(() => {
    healthAPI.check().then(({ data }) => setHealth(data)).catch(() => setHealth(null));
  }, []);

  const handleResetGraph = async () => {
    const confirmed = window.confirm(
      'This wipes the knowledge graph and restores seed demo data (JWT / PostgreSQL / AuthModule). Continue?'
    );
    if (!confirmed) return;
    setResetting(true);
    setResetMessage(null);
    try {
      const { data } = await graphAPI.reset();
      setResetMessage(`Graph reset (${data.mode}). Seed decisions restored. Re-upload the transcript if you need those nodes.`);
      const healthRes = await healthAPI.check().catch(() => null);
      if (healthRes?.data) setHealth(healthRes.data);
    } catch (err) {
      setResetMessage(err.message || 'Reset failed');
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <header className="border-b border-theme px-6 py-4">
        <h2 className="font-brand text-xl text-primary">Settings</h2>
        <p className="font-sans text-sm text-secondary">Appearance and system configuration</p>
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
          <h3 className="font-brand text-primary">System Status</h3>
          {health ? (
            <dl className="mt-4 space-y-2 font-sans text-sm">
              <div className="flex justify-between">
                <dt className="text-secondary">API Status</dt>
                <dd className="text-accent">{health.status}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-secondary">Demo Mode</dt>
                <dd className="text-accent">
                  {health.demo_mode ? 'Yes (in-memory graph)' : 'No (Neo4j)'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-secondary">Groq LLM</dt>
                <dd className="text-accent">
                  {health.groq_configured ? 'Configured' : 'Demo responses'}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="mt-4 font-sans text-sm text-red-400">Backend not reachable. Start the API server.</p>
          )}
        </section>

        <section className="halite-card p-6">
          <h3 className="font-brand text-primary">Demo graph</h3>
          <p className="mt-2 font-sans text-sm text-secondary">
            Wipe all nodes and restore the seeded JWT / PostgreSQL decisions. Use this before a clean viva run, then
            ingest the transcript once.
          </p>
          <button
            onClick={handleResetGraph}
            disabled={resetting}
            className="halite-btn mt-4 text-sm text-red-400 ring-1 ring-red-500/30 hover:bg-red-500/10 disabled:opacity-60"
          >
            {resetting ? 'Resetting…' : 'Reset knowledge graph'}
          </button>
          {resetMessage && (
            <p className="mt-3 font-sans text-sm text-accent">{resetMessage}</p>
          )}
        </section>

        <section className="halite-card p-6">
          <h3 className="font-brand text-primary">
            About <BrandName className="text-accent" />
          </h3>
          <p className="mt-2 font-sans text-sm text-secondary">
            <BrandName className="text-accent" /> is a living knowledge graph for software project reasoning, decisions, and
            institutional memory. Built for FAST NUCES FYP — capturing the &quot;why&quot; behind your codebase.
          </p>
        </section>
      </div>
    </div>
  );
}
