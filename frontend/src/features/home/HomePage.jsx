import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { sessionsAPI } from '../investigation/api';
import { PageHeader } from '../investigation/feedback';

const SUMMARY_PATHS = ['/retrieval/summary', '/integrity/summary', '/sessions/summary'];

function HomeContents() {
  const [widgets, setWidgets] = useState([]);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [allFailed, setAllFailed] = useState(false);
  const [recentFailed, setRecentFailed] = useState(false);
  const [recentLoading, setRecentLoading] = useState(true);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const abort = new AbortController();
    setLoading(true); setAllFailed(false); setRecentFailed(false); setRecentLoading(true);
    setWidgets([]); setRecent([]);
    Promise.allSettled(SUMMARY_PATHS.map(path => api.get(path, { signal: abort.signal, timeout: 15000 })))
      .then(results => {
        if (abort.signal.aborted) return;
        const good = results.filter(result => result.status === 'fulfilled').map(result => result.value.data);
        setWidgets(good);
        setAllFailed(good.length === 0);
      })
      .finally(() => { if (!abort.signal.aborted) setLoading(false); });
    sessionsAPI.list({ mine: true, limit: 5 }, abort.signal).then(({ data }) => {
      if (!abort.signal.aborted) setRecent(data.items);
    }).catch(() => { if (!abort.signal.aborted) setRecentFailed(true); })
      .finally(() => { if (!abort.signal.aborted) setRecentLoading(false); });
    return () => abort.abort();
  }, [reload]);
  return <div className="h-full overflow-y-auto p-4 sm:p-6"><div className="mx-auto max-w-7xl space-y-6">
    <PageHeader title="Maintenance workspace" description="Evidence, record integrity and your recent investigations.">
      <Link className="halite-btn-primary" to="/app/investigations">Open investigations</Link>
    </PageHeader>
    {loading && <p role="status" className="text-sm text-secondary">Loading workspace summaries…</p>}
    {allFailed && <div role="alert" className="halite-card p-4 text-sm text-primary">Workspace summaries are unavailable.
      <button type="button" className="halite-btn-outline ml-3" onClick={() => setReload(n => n + 1)}>Try again</button>
    </div>}
    <div className="grid items-start gap-4 lg:grid-cols-3">{widgets.map(widget => <section key={widget.title} className="halite-card min-w-0 p-5">
      <h2 className="font-brand text-lg text-primary">{widget.title}</h2>
      {(widget.stats || []).length === 0 ? <p className="mt-3 text-sm text-secondary">No summary data is available yet.</p> : <>
        <dl className="mt-4 space-y-3">{widget.stats.map(stat => <div key={stat.label}>
          <dt className="text-sm text-secondary">{stat.label}</dt><dd className="font-brand text-2xl text-primary">{stat.value}</dd>
          {stat.hint && <p className="text-xs text-secondary">{stat.hint}</p>}
        </div>)}</dl>
        {widget.link && <Link className="mt-4 inline-block text-sm text-accent underline" to={widget.link}>Open {widget.title.toLowerCase()}</Link>}
      </>}
    </section>)}</div>
    <section className="halite-card p-5" aria-label="Recent investigations"><h2 className="font-brand text-lg text-primary">Recent investigations</h2>
      {recentLoading ? <p role="status" className="mt-3 text-sm text-secondary">Loading recent investigations…</p> : recentFailed ? <p className="mt-3 text-sm text-secondary">Recent investigations could not be loaded.</p>
        : recent.length === 0 ? <p className="mt-3 text-sm text-secondary">No investigations yet. Start one to save your work.</p>
          : <ul className="mt-3 space-y-3">{recent.map(item => <li key={item.id} className="flex flex-wrap justify-between gap-2 border-t border-theme pt-3">
            <Link className="break-all text-sm text-accent underline" to={`/app/investigations/${encodeURIComponent(item.id)}`}>{item.title}</Link>
            <span className="text-xs text-secondary">{item.status} · {item.turn_count} turns</span>
          </li>)}</ul>}
    </section>
  </div></div>;
}

export default function HomePage() {
  const { user } = useAuth();
  if (!user) return <p className="p-6 text-primary">Sign in to open the maintenance workspace.</p>;
  return <HomeContents key={`${user.id}:${user.organization_id}`} />;
}
