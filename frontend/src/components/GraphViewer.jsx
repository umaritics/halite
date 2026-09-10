import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import { useTheme } from '../context/ThemeContext';

const NODE_COLORS = {
  Component: '#E8650A',
  Decision: '#FF7A1A',
  Commit: '#888888',
  Ticket: '#C45A0A',
  Document: '#666666',
  Asset: '#FF9E5E', // Distinct from Decision
  ServiceRecord: '#B34A00', // distinct
};

const DECISION_STATUS_COLORS = {
  active: '#E8650A',
  needs_review: '#FF7A1A',
  invalidated: '#CC3300',
};

function getNodeColor(node) {
  if (node.label === 'Decision' || node.title) {
    return DECISION_STATUS_COLORS[node.status] || NODE_COLORS.Decision;
  }
  if (node.label === 'ServiceRecord') {
    return node.status === 'superseded' ? '#555555' : NODE_COLORS.ServiceRecord;
  }
  return NODE_COLORS[node.label] || '#E8650A';
}

function getNodeLabel(node) {
  return node.name || node.title || node.filename || node.id?.slice(0, 8) || 'Node';
}

export default function GraphViewer({ data, onNodeSelect, searchQuery = '', typeFilters = {} }) {
  const fgRef = useRef();
  const containerRef = useRef();
  const { isDark } = useTheme();
  const [size, setSize] = useState({ w: 800, h: 560 });
  const [error, setError] = useState(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const measure = () => {
      const w = Math.max(el.clientWidth || 0, 320);
      const h = Math.max(el.clientHeight || 0, 480);
      setSize({ w, h });
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    // Remeasure after layout settles
    const t1 = setTimeout(measure, 50);
    const t2 = setTimeout(measure, 250);
    return () => {
      ro.disconnect();
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);

  const graphData = useMemo(() => {
    const activeTypes = Object.entries(typeFilters)
      .filter(([, v]) => v)
      .map(([k]) => k);

    let nodes = (data.nodes || []).map((n) => ({
      id: n.id,
      label: n.label || (n.title ? 'Decision' : n.name ? 'Component' : 'Node'),
      name: getNodeLabel(n),
      color: getNodeColor(n),
      val: n.label === 'Decision' || n.title ? 8 : 5,
      // keep original fields for side panel
      ...n,
      displayName: getNodeLabel(n),
    }));

    if (activeTypes.length) {
      nodes = nodes.filter((n) => activeTypes.includes(n.label));
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      nodes = nodes.filter((n) => n.displayName.toLowerCase().includes(q));
    }

    const ids = new Set(nodes.map((n) => n.id));
    const links = (data.edges || [])
      .map((e) => ({
        source: typeof e.source === 'object' ? e.source.id : e.source,
        target: typeof e.target === 'object' ? e.target.id : e.target,
        type: e.type,
      }))
      .filter((e) => ids.has(e.source) && ids.has(e.target));

    return { nodes, links };
  }, [data, searchQuery, typeFilters]);

  useEffect(() => {
    if (!fgRef.current || !graphData.nodes.length) return;
    const t = setTimeout(() => {
      try {
        fgRef.current.zoomToFit(500, 80);
      } catch (err) {
        setError(String(err));
      }
    }, 400);
    return () => clearTimeout(t);
  }, [graphData, size]);

  const handleClick = useCallback(
    (node) => {
      if (node) onNodeSelect?.(node);
    },
    [onNodeSelect]
  );

  const bg = isDark ? '#000000' : '#F5F5F5';
  const linkCol = isDark ? 'rgba(232,101,10,0.55)' : 'rgba(232,101,10,0.7)';

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full overflow-hidden"
      style={{ minHeight: 520 }}
    >
      {error && (
        <div className="absolute left-4 top-4 z-20 rounded-md bg-red-500/10 px-3 py-2 text-xs text-red-400">
          Graph render error: {error}
        </div>
      )}

      {graphData.nodes.length === 0 ? (
        <div className="flex h-full min-h-[520px] items-center justify-center">
          <p className="font-sans text-sm text-secondary">No nodes to display</p>
        </div>
      ) : (
        <ForceGraph3D
          ref={fgRef}
          graphData={graphData}
          width={size.w}
          height={size.h}
          backgroundColor={bg}
          showNavInfo={false}
          nodeLabel="displayName"
          nodeColor={(n) => n.color}
          nodeVal={(n) => n.val || 5}
          nodeRelSize={6}
          nodeOpacity={1}
          linkColor={() => linkCol}
          linkWidth={1.5}
          linkOpacity={0.8}
          linkDirectionalParticles={2}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleColor={() => '#E8650A'}
          onNodeClick={handleClick}
          onNodeHover={(node) => {
            document.body.style.cursor = node ? 'pointer' : 'default';
          }}
          cooldownTicks={80}
          onEngineStop={() => {
            try {
              fgRef.current?.zoomToFit(400, 60);
            } catch {
              /* ignore */
            }
          }}
        />
      )}

      <div className="pointer-events-none absolute bottom-3 left-3 rounded-md bg-black/50 px-2 py-1 font-sans text-[11px] text-[#888888]">
        {graphData.nodes.length} nodes · {graphData.links.length} links · drag to rotate
      </div>
    </div>
  );
}

export function GraphSidePanel({ node, onClose, onChatAbout }) {
  if (!node) return null;

  return (
    <div className="halite-card absolute right-4 top-4 z-10 max-h-[calc(100%-2rem)] w-80 overflow-y-auto p-4">
      <div className="flex items-start justify-between">
        <div>
          <span className="font-sans text-xs uppercase text-accent">{node.label}</span>
          <h3 className="font-brand mt-1 text-primary">{node.displayName || getNodeLabel(node)}</h3>
        </div>
        <button onClick={onClose} className="text-secondary hover:text-primary">
          ✕
        </button>
      </div>

      <div className="mt-4 space-y-2 font-sans text-sm text-secondary">
        {node.status && (
          <p>
            <span className="text-[#555555]">Status:</span> {node.status}
          </p>
        )}
        {node.reasoning && <p className="whitespace-pre-wrap">{node.reasoning}</p>}
        {node.description && <p>{node.description}</p>}
        {node.file_path && (
          <p>
            <span className="text-[#555555]">Path:</span>{' '}
            <code className="font-mono text-xs text-accent">{node.file_path}</code>
          </p>
        )}
      </div>

      <button onClick={() => onChatAbout?.(node)} className="halite-btn-primary mt-4 w-full text-sm">
        Chat about this
      </button>
    </div>
  );
}
