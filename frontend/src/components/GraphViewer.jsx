import { Component, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import { Link } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { formatDate } from '../utils/format';

// Correction edges (SUPERSEDES, computed by the conflict engine) are drawn apart from the
// stored ordering/ownership edges so they can be found at a glance.
const CORRECTION_EDGE = 'SUPERSEDES';
const CORRECTION_COLOR = '#E5A100';

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
  // Aircraft show their tail number and service records their FAA record id; a UUID prefix
  // means nothing to a reader.
  return (
    node.tail_number || node.record_id || node.name || node.title || node.filename || node.id?.slice(0, 8) || 'Node'
  );
}

// WebGL is required by the 3D graph. Some browsers (sandboxed panes, machines with
// hardware acceleration off) don't provide it; without this check the 3D renderer
// throws and, with no error boundary, blanks the whole app.
function hasWebGL() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (c.getContext('webgl') || c.getContext('experimental-webgl')));
  } catch {
    return false;
  }
}

function NoWebGL() {
  return (
    <div className="flex h-full min-h-[520px] items-center justify-center p-8">
      <div className="max-w-md text-center font-sans">
        <p className="text-sm text-primary">The 3D graph needs WebGL, which this browser isn't providing.</p>
        <p className="mt-2 text-xs text-secondary">
          Open Halite in Chrome or Safari with hardware acceleration turned on. The rest of the app works normally.
        </p>
      </div>
    </div>
  );
}

class GraphErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(err) {
    console.error('Graph render failed:', err);
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

export default function GraphViewer({ data, onNodeSelect, searchQuery = '', typeFilters = {} }) {
  const fgRef = useRef();
  const containerRef = useRef();
  const { isDark } = useTheme();
  const [size, setSize] = useState({ w: 800, h: 560 });
  const [error, setError] = useState(null);
  const webgl = useMemo(() => hasWebGL(), []);

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
      // The aircraft is the hub; its records stay small so dozens of them remain distinguishable.
      val: n.label === 'Asset' ? 14 : n.label === 'ServiceRecord' ? 3 : n.label === 'Decision' || n.title ? 8 : 5,
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
    // Space the layout out so a small graph's edges are not hidden behind its nodes.
    const link = fgRef.current.d3Force?.('link');
    link?.distance?.(70);
    fgRef.current.d3Force?.('charge')?.strength?.(-140);
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
  // Animated particles on every edge are heavy on a dense graph; keep them for corrections
  // always, and for other edges only while the view is small enough to stay smooth.
  const particlesOnAll = graphData.links.length <= 600;

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
      ) : !webgl ? (
        <NoWebGL />
      ) : (
        <GraphErrorBoundary fallback={<NoWebGL />}>
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
          nodeRelSize={4}
          nodeOpacity={1}
          linkColor={(l) => (l.type === CORRECTION_EDGE ? CORRECTION_COLOR : linkCol)}
          linkWidth={(l) => (l.type === CORRECTION_EDGE ? 3.5 : 1.5)}
          linkOpacity={0.8}
          linkDirectionalParticles={(l) => (l.type === CORRECTION_EDGE ? 4 : particlesOnAll ? 2 : 0)}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleColor={(l) => (l.type === CORRECTION_EDGE ? CORRECTION_COLOR : '#E8650A')}
          onNodeClick={handleClick}
          onNodeHover={(node) => {
            document.body.style.cursor = node ? 'pointer' : 'default';
          }}
          // Settle the layout before the first frame so the camera fits to the final positions even
          // when frames are slow; very large views keep a short animated settle instead.
          warmupTicks={graphData.nodes.length > 600 ? 30 : 120}
          cooldownTicks={graphData.nodes.length > 600 ? 80 : 0}
          cooldownTime={3000}
          onEngineStop={() => {
            try {
              fgRef.current?.zoomToFit(400, 60);
            } catch {
              /* ignore */
            }
          }}
        />
        </GraphErrorBoundary>
      )}

      <div className="pointer-events-none absolute bottom-3 left-3 rounded-md bg-black/50 px-2 py-1 font-sans text-[11px] text-[#888888]">
        {graphData.nodes.length} nodes · {graphData.links.length} links · drag to rotate
      </div>
    </div>
  );
}

// `assetUuid` (optional) is the aircraft's id, used to link into the asset history page.
export function GraphSidePanel({ node, onClose, onChatAbout, assetUuid }) {
  if (!node) return null;

  const isRecord = node.label === 'ServiceRecord';
  const isAsset = node.label === 'Asset';

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
        {isRecord && (
          <div id="graph-record-details" className="space-y-1">
            <p><span className="text-[#555555]">Record:</span> <span className="font-mono text-xs text-primary">{node.record_id}</span></p>
            {node.asset_key && <p><span className="text-[#555555]">Aircraft:</span> {node.asset_key}</p>}
            <p><span className="text-[#555555]">Date:</span> {formatDate(node.occurred_at)}</p>
            {node.part_name && <p><span className="text-[#555555]">Part:</span> {node.part_name}</p>}
            {node.jasc_code && <p><span className="text-[#555555]">JASC:</span> {node.jasc_code}</p>}
            {node.source && <p><span className="text-[#555555]">Source:</span> {node.source}</p>}
            {node.text && <p className="whitespace-pre-wrap text-xs">{String(node.text).slice(0, 280)}{String(node.text).length > 280 ? '…' : ''}</p>}
          </div>
        )}
        {isAsset && (
          <div id="graph-asset-details" className="space-y-1">
            {node.tail_number && <p><span className="text-[#555555]">Tail number:</span> {node.tail_number}</p>}
            {(node.make || node.model) && <p><span className="text-[#555555]">Aircraft:</span> {[node.make, node.model].filter(Boolean).join(' ')}</p>}
            {node.serial_number && <p><span className="text-[#555555]">Serial:</span> {node.serial_number}</p>}
          </div>
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

      {(isRecord || isAsset) && (assetUuid || isAsset) && (
        <Link
          to={
            isRecord
              ? `/app/asset-history/${encodeURIComponent(assetUuid)}#${encodeURIComponent(node.record_id)}`
              : `/app/asset-history/${encodeURIComponent(assetUuid || node.id)}`
          }
          className="mt-4 inline-block text-xs text-accent hover:underline"
        >
          Open in asset history →
        </Link>
      )}

      {onChatAbout && (
        <button onClick={() => onChatAbout(node)} className="halite-btn-primary mt-4 w-full text-sm">
          Chat about this
        </button>
      )}
    </div>
  );
}
