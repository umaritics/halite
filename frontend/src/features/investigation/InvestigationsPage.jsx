import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { sessionsAPI } from './api';
import { clearLegacyInvestigations } from './privacy';
import { ErrorCard, investigationError, PageHeader } from './feedback';

function InvestigationList({ user, status, mine }) {
  const navigate = useNavigate();
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const [items, setItems] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [assets, setAssets] = useState([]);
  const [assetError, setAssetError] = useState(false);
  const [asset, setAsset] = useState('');
  const [title, setTitle] = useState('');
  const [creating, setCreating] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const abort = new AbortController();
    setLoading(true);
    setError(null);
    sessionsAPI.list({ status: status || undefined, mine, limit: 20 }, abort.signal)
      .then(({ data }) => {
        if (!abort.signal.aborted) { setItems(data.items); setCursor(data.next_cursor); }
      })
      .catch(err => { if (!abort.signal.aborted) setError(investigationError(err)); })
      .finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, [status, mine, reload]);
  useEffect(() => {
    let active = true;
    const abort = new AbortController();
    sessionsAPI.assets(abort.signal).then(({ data }) => { if (active) setAssets(data); })
      .catch(() => { if (active) setAssetError(true); });
    return () => { active = false; abort.abort(); };
  }, []);
  useEffect(() => { clearLegacyInvestigations(); return () => { clearLegacyInvestigations(); }; }, []);

  async function start(event) {
    event.preventDefault();
    if (creating) return;
    setCreating(true); setError(null);
    try {
      const { data } = await sessionsAPI.create({ title: title.trim() || null, asset_id: asset || null });
      if (alive.current) navigate(`/app/investigations/${encodeURIComponent(data.id)}`);
    } catch (err) { if (alive.current) setError(investigationError(err)); }
    finally { if (alive.current) setCreating(false); }
  }
  async function more() {
    if (!cursor || loading) return;
    setLoading(true); setError(null);
    try {
      const { data } = await sessionsAPI.list({ status: status || undefined, mine, cursor, limit: 20 });
      if (!alive.current) return;
      setItems(previous => [...previous, ...data.items.filter(item => !previous.some(p => p.id === item.id))]);
      setCursor(data.next_cursor);
    } catch (err) { if (alive.current) setError(investigationError(err)); }
    finally { if (alive.current) setLoading(false); }
  }
  return <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
    <section className="min-w-0 space-y-4" aria-label="Investigation history">
      <ErrorCard message={error} onRetry={() => setReload(n => n + 1)} />
      {loading && <p role="status" className="text-sm text-secondary">Loading investigations…</p>}
      {!loading && !error && items.length === 0 && <div className="halite-card p-6">
        <h2 className="font-brand text-lg text-primary">No investigations in this view</h2>
        <p className="mt-2 text-sm text-secondary">Start an investigation or change the status filter.</p>
      </div>}
      <ul className="space-y-3">{items.map(item => <li key={item.id} className="halite-card min-w-0 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Link className="break-words font-brand text-lg text-accent underline" to={`/app/investigations/${encodeURIComponent(item.id)}`}>{item.title}</Link>
          <span className="rounded border border-theme px-2 py-1 text-xs text-primary">{item.status}</span>
        </div>
        <p className="mt-2 text-sm text-secondary">{item.asset_tail || 'All fleet'} · {item.turn_count} turns{item.user_id !== user.id ? ' · Supervisor view' : ''}</p>
        <time className="mt-1 block text-xs text-secondary" dateTime={item.created_at}>{item.created_at}</time>
        {item.outcome_part && <p className="mt-2 text-sm text-primary">Recorded finding: {item.outcome_part}</p>}
      </li>)}</ul>
      {cursor && <button type="button" className="halite-btn-outline disabled:opacity-50" disabled={loading} onClick={more}>Load more investigations</button>}
    </section>
    <form onSubmit={start} className="halite-card min-w-0 p-5">
      <h2 className="font-brand text-lg text-primary">Start an investigation</h2>
      <fieldset disabled={creating} className="mt-4 space-y-4">
        <label className="block text-sm text-primary">Investigation title (optional)<input className="halite-input mt-1" maxLength={160} value={title} onChange={e => setTitle(e.target.value)} /></label>
        <label className="block text-sm text-primary">Aircraft<select aria-label="Aircraft" className="halite-input mt-1" value={asset} onChange={e => setAsset(e.target.value)}>
          <option value="">All fleet</option>{assets.map(item => <option key={item.id} value={item.id}>{item.tail_number}</option>)}
        </select></label>
        {assetError && <p role="status" className="text-sm text-secondary">Aircraft options could not be loaded. You can still start a fleet-wide investigation.</p>}
        <button className="halite-btn-primary disabled:opacity-50" disabled={creating}>{creating ? 'Creating…' : 'Create investigation'}</button>
      </fieldset>
      <p className="mt-3 text-xs text-secondary">Saved to your account. Your organisation’s supervisors can read your investigations.</p>
    </form>
  </div>;
}

export default function InvestigationsPage() {
  const { user } = useAuth();
  const [status, setStatus] = useState('');
  const [mine, setMine] = useState(true);
  if (!user) return <p className="p-6 text-primary">Sign in to view your investigations.</p>;
  return <div className="h-full overflow-y-auto p-4 sm:p-6">
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader title="Investigations" description="Resume your work, review the evidence, and record what was found."><Link to="/app/investigations/experiments" className="halite-btn-outline">How Halite decides</Link><Link to="/app/investigations/quick" className="halite-btn-outline">Quick diagnosis</Link></PageHeader>
      <div className="flex flex-wrap items-end gap-4">
        <label className="text-sm text-primary">Status<select aria-label="Status" className="halite-input mt-1" value={status} onChange={e => setStatus(e.target.value)}>
          <option value="">All statuses</option><option value="open">Open</option><option value="closed">Closed</option>
        </select></label>
        {['supervisor', 'admin'].includes(user.role) && <label className="flex items-center gap-2 pb-3 text-sm text-primary">
          <input type="checkbox" checked={mine} onChange={e => setMine(e.target.checked)} />Only my investigations
        </label>}
      </div>
      <InvestigationList key={`${user.id}:${user.organization_id}:${status}:${mine}`} user={user} status={status} mine={mine} />
    </div>
  </div>;
}
