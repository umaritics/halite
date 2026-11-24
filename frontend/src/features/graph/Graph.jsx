import { useMemo, useState } from 'react';
import { MagnifyingGlassIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { Button, EmptyState, ErrorBoundary, ErrorCard, PageHeader, Skeleton } from '../../components/ui';
import GraphFallback from './GraphFallback';
import GraphViewer, { GraphSidePanel } from './GraphViewer';
import { useGraph } from './useGraph';
import { hasWebGL } from './webgl';
import {
  EDGE_MEANING,
  MAINT_LABELS,
  aircraftOptions,
  countBy,
  focusAircraft,
  maintenanceGraph,
} from './graphScope';

// The backend default (200) returns only a slice of the maintenance graph; ask for enough to
// hold the whole thing (about 2,200 nodes on staging) and say so if the cap is reached.
export const MAINT_GRAPH_LIMIT = 3000;
// Above this many edges the whole-fleet view is slow to lay out and hard to read.
const DENSE_EDGE_COUNT = 1500;
const EDGE_SWATCH = { ABOUT: '#E8650A', PRECEDED_BY: '#E8650A', SUPERSEDES: '#E5A100' };
const NO_WEBGL_REASON =
  "The 3D graph needs WebGL, which this browser isn't providing. The same stored nodes and edges are listed below.";
const VIEWER_FAILED_REASON = 'The 3D graph could not be drawn. The same stored nodes and edges are listed below.';

export default function Graph() {
  const { data, loading, error, refetch } = useGraph(MAINT_GRAPH_LIMIT);
  const [selectedNode, setSelectedNode] = useState(null);
  const [search, setSearch] = useState('');
  const [typeFilters, setTypeFilters] = useState(() => Object.fromEntries(MAINT_LABELS.map((t) => [t, true])));
  // undefined = not chosen yet (use the busiest aircraft); '' = whole fleet.
  const [chosenTail, setChosenTail] = useState(undefined);
  const webgl = useMemo(() => hasWebGL(), []);

  const full = useMemo(() => maintenanceGraph(data), [data]);
  const aircraft = useMemo(() => aircraftOptions(full), [full]);
  const tail = chosenTail === undefined ? aircraft[0]?.tail ?? '' : chosenTail;
  const scoped = useMemo(() => focusAircraft(full, tail), [full, tail]);

  const nodeCounts = useMemo(() => countBy(scoped.nodes, (n) => n.label), [scoped]);
  const edgeCounts = useMemo(() => countBy(scoped.edges, (e) => e.type), [scoped]);
  const assetIdByTail = useMemo(() => new Map(aircraft.map((a) => [a.tail, a.id])), [aircraft]);
  const hitCap = (data.nodes?.length ?? 0) >= MAINT_GRAPH_LIMIT;
  const dense = !tail && scoped.edges.length > DENSE_EDGE_COUNT;

  const toggleType = (type) => setTypeFilters((prev) => ({ ...prev, [type]: !prev[type] }));
  const selectedAssetUuid =
    selectedNode?.label === 'Asset' ? selectedNode.id : assetIdByTail.get(selectedNode?.asset_key);

  const failedFallback = <GraphFallback data={scoped} tail={tail} reason={VIEWER_FAILED_REASON} />;

  function renderMain() {
    if (error) {
      return (
        <div className="p-6">
          <ErrorCard message={error} onRetry={refetch} />
        </div>
      );
    }
    if (loading && !data.nodes?.length) {
      return <Skeleton variant="card" lines={6} className="p-6" />;
    }
    if (!scoped.nodes.length) {
      return (
        <div className="p-6">
          <EmptyState
            title="No graph data yet"
            body="No aircraft or service records are stored yet. Ingest service records and they will appear here."
          />
        </div>
      );
    }
    if (!webgl) {
      return <GraphFallback data={scoped} tail={tail} reason={NO_WEBGL_REASON} />;
    }
    return (
      <>
        {dense && (
          <p
            id="graph-density-warning"
            className="absolute left-4 top-4 z-20 max-w-sm rounded-md bg-amber-500/10 px-3 py-2 text-xs text-amber-400"
          >
            {scoped.edges.length} edges is too dense to read. Pick one aircraft to see its records and
            corrections clearly.
          </p>
        )}
        <ErrorBoundary
          resetKey={tail}
          fallback={failedFallback}
          onError={(err) => console.error('Graph render failed:', err)}
        >
          <GraphViewer
            data={scoped}
            searchQuery={search}
            typeFilters={typeFilters}
            onNodeSelect={setSelectedNode}
          />
        </ErrorBoundary>
        <GraphSidePanel
          node={selectedNode}
          assetUuid={selectedAssetUuid}
          onClose={() => setSelectedNode(null)}
        />
      </>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="px-6 pt-4">
        <PageHeader
          title="Knowledge Graph"
          description="Stored aircraft, service records and the relationships between them"
          actions={
            <div className="flex flex-wrap items-center gap-3">
              {!loading && !error && (
                <span
                  id="graph-scope-chip"
                  className="rounded-full border border-accent/20 bg-accent/10 px-2.5 py-0.5 text-xs font-medium text-accent"
                >
                  {tail ? `Aircraft ${tail}` : 'Whole fleet'}: {scoped.nodes.length} nodes · {scoped.edges.length} edges
                  {hitCap ? ' (loaded cap reached — graph may be incomplete)' : ''}
                </span>
              )}
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search nodes…"
                  aria-label="Search nodes"
                  className="halite-input py-2 pl-9 pr-4 text-sm"
                />
              </div>
              <Button variant="ghost" onClick={refetch} aria-label="Refresh graph" title="Refresh">
                <ArrowPathIcon className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          }
        />
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden md:flex-row">
        <aside className="max-h-[40%] w-full shrink-0 overflow-y-auto border-b border-theme p-4 md:max-h-none md:w-64 md:border-b-0 md:border-r">
          <label htmlFor="graph-aircraft" className="font-sans text-xs font-semibold uppercase tracking-wider text-secondary">
            Aircraft
          </label>
          <select
            id="graph-aircraft"
            value={tail}
            onChange={(e) => {
              setChosenTail(e.target.value);
              setSelectedNode(null);
            }}
            className="halite-input mt-2 w-full py-2 text-sm"
          >
            <option value="">Whole fleet (dense)</option>
            {aircraft.map((a) => (
              <option key={a.id} value={a.tail}>
                {a.tail} · {a.records} rec{a.corrections ? ` · ${a.corrections} corr.` : ''}
              </option>
            ))}
          </select>

          <h3 className="mt-6 font-sans text-xs font-semibold uppercase tracking-wider text-secondary">Filter by type</h3>
          <div className="mt-3 space-y-2">
            {MAINT_LABELS.map((type) => (
              <label key={type} className="flex cursor-pointer items-center gap-2 font-sans text-sm text-primary">
                <input
                  type="checkbox"
                  checked={!!typeFilters[type]}
                  onChange={() => toggleType(type)}
                  className="rounded border-border-dark bg-black text-accent focus:ring-accent"
                />
                {type}
                <span className="ml-auto font-sans text-xs text-[#555555]">{nodeCounts[type] || 0}</span>
              </label>
            ))}
          </div>

          <h3 className="mt-6 font-sans text-xs font-semibold uppercase tracking-wider text-secondary">Relationships</h3>
          <ul id="graph-edge-legend" className="mt-3 space-y-3">
            {Object.keys(EDGE_MEANING).map((type) => (
              <li key={type} className="font-sans text-xs text-secondary">
                <span className="flex items-center gap-2 text-primary">
                  <span
                    aria-hidden="true"
                    className="inline-block h-1 w-5 rounded"
                    style={{ background: EDGE_SWATCH[type] }}
                  />
                  {type}
                  <span className="ml-auto text-[#555555]">{edgeCounts[type] || 0}</span>
                </span>
                <span className="mt-1 block">{EDGE_MEANING[type]}</span>
              </li>
            ))}
          </ul>

          <p className="mt-6 font-sans text-xs text-[#555555]">
            Drag to rotate · Scroll to zoom · Click a node for details
          </p>
        </aside>

        <div className="relative min-h-[320px] flex-1 md:min-h-[520px]">
          {renderMain()}
        </div>
      </div>
    </div>
  );
}
