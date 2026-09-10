import { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MagnifyingGlassIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import GraphViewer, { GraphSidePanel } from '../components/GraphViewer';
import { useGraph } from '../hooks/useGraph';
import { useDomain } from '../context/DomainContext';

const SOFTWARE_TYPES = ['Component', 'Decision', 'Commit', 'Ticket', 'Document'];
const MAINT_TYPES = ['Asset', 'ServiceRecord'];

export default function Graph() {
  const { data, loading, error, refetch } = useGraph();
  const { domain } = useDomain();
  const [selectedNode, setSelectedNode] = useState(null);
  const [search, setSearch] = useState('');
  
  const NODE_TYPES = domain === 'maintenance' ? MAINT_TYPES : SOFTWARE_TYPES;
  
  const [typeFilters, setTypeFilters] = useState({});
  const navigate = useNavigate();

  useEffect(() => {
    setTypeFilters(Object.fromEntries(NODE_TYPES.map((t) => [t, true])));
  }, [domain]);

  const stats = useMemo(() => {
    const counts = {};
    for (const n of data.nodes || []) {
      const label = n.label || 'Other';
      counts[label] = (counts[label] || 0) + 1;
    }
    return counts;
  }, [data]);

  const toggleType = (type) => {
    setTypeFilters((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-theme px-6 py-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="font-brand text-xl text-primary">Knowledge Graph</h2>
            <span className="rounded-full bg-accent/10 px-2.5 py-0.5 text-xs font-medium text-accent border border-accent/20">
              Capped at 2000 nodes
            </span>
          </div>
          <p className="font-sans text-sm text-secondary">3D visualization of decisions, components & relationships</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search nodes…"
              className="halite-input pl-9 pr-4 py-2 text-sm"
            />
          </div>
          <button onClick={refetch} className="halite-btn-ghost" title="Refresh">
            <ArrowPathIcon className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <aside className="w-56 shrink-0 overflow-y-auto border-r border-theme p-4">
          <h3 className="font-sans text-xs font-semibold uppercase tracking-wider text-secondary">Filter by type</h3>
          <div className="mt-3 space-y-2">
            {NODE_TYPES.map((type) => (
              <label key={type} className="flex cursor-pointer items-center gap-2 font-sans text-sm text-primary">
                <input
                  type="checkbox"
                  checked={typeFilters[type]}
                  onChange={() => toggleType(type)}
                  className="rounded border-border-dark bg-black text-accent focus:ring-accent"
                />
                {type}
                <span className="ml-auto font-sans text-xs text-[#555555]">{stats[type] || 0}</span>
              </label>
            ))}
          </div>
          <p className="mt-6 font-sans text-xs text-[#555555]">
            Drag to rotate · Scroll to zoom · Click a node for details
          </p>
        </aside>

        <div className="relative min-h-0 flex-1" style={{ minHeight: 520 }}>
          {error && (
            <p className="absolute left-4 top-4 z-20 rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-400">
              {error} — is the backend running on port 8000?
            </p>
          )}
          {loading && !data.nodes?.length ? (
            <div className="flex h-full items-center justify-center font-sans text-accent">
              Loading graph data…
            </div>
          ) : (
            <>
              <GraphViewer
                data={data}
                searchQuery={search}
                typeFilters={typeFilters}
                onNodeSelect={setSelectedNode}
              />
              <GraphSidePanel
                node={selectedNode}
                onClose={() => setSelectedNode(null)}
                onChatAbout={(node) =>
                  navigate('/app/chat', {
                    state: { prefill: node.displayName || node.title || node.name },
                  })
                }
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
