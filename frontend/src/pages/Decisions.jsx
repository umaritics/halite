import { useEffect, useState } from 'react';
import { PlusIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { decisionsAPI } from '../api/client';
import DecisionCard from '../components/DecisionCard';

const STATUS_FILTERS = ['all', 'active', 'needs_review', 'invalidated'];

export default function Decisions() {
  const [decisions, setDecisions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({
    title: '',
    reasoning: '',
    related_component_names: [],
    linked_ticket_ids: [],
  });

  const fetchDecisions = async () => {
    setLoading(true);
    try {
      const params = filter !== 'all' ? { status: filter } : {};
      const { data } = await decisionsAPI.list(params);
      setDecisions(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDecisions();
  }, [filter]);

  const filtered = decisions.filter((d) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return d.title?.toLowerCase().includes(q) || d.reasoning?.toLowerCase().includes(q);
  });

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await decisionsAPI.create(form);
      setShowModal(false);
      setForm({ title: '', reasoning: '', related_component_names: [], linked_ticket_ids: [] });
      fetchDecisions();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleView = async (decision) => {
    try {
      const { data } = await decisionsAPI.get(decision.id);
      setSelected(data);
    } catch {
      setSelected(decision);
    }
  };

  const handleInvalidate = async () => {
    const note = prompt('Invalidation note:');
    if (!note) return;
    await decisionsAPI.invalidate(selected.id, note);
    setSelected(null);
    fetchDecisions();
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-theme px-6 py-4">
        <div>
          <h2 className="font-brand text-xl text-primary">Decisions</h2>
          <p className="font-sans text-sm text-secondary">Browse and manage project reasoning entries</p>
        </div>
        <button onClick={() => setShowModal(true)} className="halite-btn-primary">
          <PlusIcon className="h-4 w-4" />
          Add Decision
        </button>
      </header>

      <div className="flex flex-wrap items-center gap-3 border-b border-theme px-6 py-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search decisions…"
          className="halite-input max-w-xs text-sm"
        />
        <div className="flex gap-1">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`rounded-lg px-3 py-1.5 font-sans text-xs font-medium capitalize transition ${
                filter === s
                  ? 'bg-accent/15 text-accent ring-1 ring-accent/30'
                  : 'text-secondary hover:text-primary'
              }`}
            >
              {s.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <p className="font-sans text-secondary">Loading decisions…</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filtered.map((d) => (
              <DecisionCard key={d.id} decision={d} onClick={handleView} />
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="halite-card w-full max-w-lg p-6">
            <div className="flex items-center justify-between">
              <h3 className="font-brand text-lg text-primary">Add Decision</h3>
              <button onClick={() => setShowModal(false)} className="text-secondary hover:text-primary">
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="mt-4 space-y-4">
              <div>
                <label className="font-sans text-sm text-secondary">Title</label>
                <input
                  required
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  className="halite-input mt-1"
                />
              </div>
              <div>
                <label className="font-sans text-sm text-secondary">Reasoning</label>
                <textarea
                  required
                  rows={5}
                  value={form.reasoning}
                  onChange={(e) => setForm({ ...form, reasoning: e.target.value })}
                  className="halite-input mt-1 resize-none"
                />
              </div>
              <div>
                <label className="font-sans text-sm text-secondary">Related Components (comma-separated)</label>
                <input
                  value={form.related_component_names.join(', ')}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      related_component_names: e.target.value
                        .split(',')
                        .map((s) => s.trim())
                        .filter(Boolean),
                    })
                  }
                  placeholder="AuthModule, DatabaseLayer"
                  className="halite-input mt-1"
                />
              </div>
              <button type="submit" className="halite-btn-primary w-full">
                Create Decision
              </button>
            </form>
          </div>
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="halite-card max-h-[80vh] w-full max-w-2xl overflow-y-auto p-6">
            <div className="flex items-start justify-between">
              <div>
                <span className={`status-${selected.status}`}>{selected.status}</span>
                <h3 className="font-brand mt-2 text-xl text-primary">{selected.title}</h3>
              </div>
              <button onClick={() => setSelected(null)} className="text-secondary hover:text-primary">
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <p className="mt-4 whitespace-pre-wrap font-sans text-primary">{selected.reasoning}</p>
            {selected.components?.length > 0 && (
              <div className="mt-4">
                <h4 className="font-sans text-sm text-secondary">Related Components</h4>
                <div className="mt-2 flex flex-wrap gap-2">
                  {selected.components.map((c) => (
                    <span key={c.id} className="rounded-md bg-accent/10 px-2 py-1 font-sans text-xs text-accent">
                      {c.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div className="mt-6 flex gap-2">
              <button onClick={handleInvalidate} className="halite-btn text-red-400 ring-1 ring-red-500/30">
                Invalidate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
