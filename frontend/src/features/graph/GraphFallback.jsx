import { Badge } from '../../components/ui';
import { formatDate } from '../../utils/format';
import { getNodeLabel } from './nodeLabel';

const CORRECTION_EDGE = 'SUPERSEDES';
// A whole-fleet table can run to thousands of rows; show a readable slice and say so.
export const FALLBACK_ROW_LIMIT = 200;

const endId = (value) => (typeof value === 'object' && value !== null ? value.id : value);

// Which records are on either side of a stored correction.
function correctionRoles(edges) {
  const roles = new Map();
  for (const edge of edges) {
    if (edge.type !== CORRECTION_EDGE) continue;
    roles.set(endId(edge.source), 'Correction');
    if (!roles.has(endId(edge.target))) roles.set(endId(edge.target), 'Superseded');
  }
  return roles;
}

function Limited({ shown, total }) {
  if (total <= shown) return null;
  return (
    <p className="mt-2 text-xs text-secondary">
      Showing the first {shown} of {total}. Pick one aircraft to see all of its rows.
    </p>
  );
}

function NodesTable({ nodes, roles }) {
  const rows = nodes.slice(0, FALLBACK_ROW_LIMIT);
  return (
    <div>
      <table className="w-full text-left text-sm">
        <caption className="mb-2 text-left font-brand text-primary">Nodes</caption>
        <thead className="text-xs uppercase text-secondary">
          <tr>
            <th scope="col" className="py-1 pr-3">Type</th>
            <th scope="col" className="py-1 pr-3">Name</th>
            <th scope="col" className="py-1 pr-3">Date</th>
            <th scope="col" className="py-1">Correction</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((node) => (
            <tr key={node.id} className="border-t border-theme">
              <td className="py-1 pr-3">{node.label}</td>
              <td className="py-1 pr-3 font-mono text-xs text-primary">{getNodeLabel(node)}</td>
              <td className="py-1 pr-3">{node.occurred_at ? formatDate(node.occurred_at) : ''}</td>
              <td className="py-1">
                {roles.get(node.id) && <Badge tone="warning">{roles.get(node.id)}</Badge>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Limited shown={rows.length} total={nodes.length} />
    </div>
  );
}

function EdgesTable({ edges, names }) {
  const rows = edges.slice(0, FALLBACK_ROW_LIMIT);
  const nameOf = (end) => names.get(endId(end)) || String(endId(end));
  return (
    <div>
      <table className="w-full text-left text-sm">
        <caption className="mb-2 text-left font-brand text-primary">Edges</caption>
        <thead className="text-xs uppercase text-secondary">
          <tr>
            <th scope="col" className="py-1 pr-3">Relationship</th>
            <th scope="col" className="py-1 pr-3">From</th>
            <th scope="col" className="py-1 pr-3">To</th>
            <th scope="col" className="py-1">Correction</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((edge, index) => (
            <tr key={index} className="border-t border-theme">
              <td className="py-1 pr-3">{edge.type}</td>
              <td className="py-1 pr-3 font-mono text-xs text-primary">{nameOf(edge.source)}</td>
              <td className="py-1 pr-3 font-mono text-xs text-primary">{nameOf(edge.target)}</td>
              <td className="py-1">
                {edge.type === CORRECTION_EDGE && <Badge tone="warning">Correction</Badge>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Limited shown={rows.length} total={edges.length} />
    </div>
  );
}

/**
 * Readable stand-in for the 3D graph, used when WebGL is missing or the viewer throws.
 * It lists the same stored nodes and edges, so it also works as a text alternative.
 */
export default function GraphFallback({ data, tail, reason }) {
  const nodes = data.nodes || [];
  const edges = data.edges || [];
  const corrections = edges.filter((edge) => edge.type === CORRECTION_EDGE).length;
  const names = new Map(nodes.map((node) => [node.id, getNodeLabel(node)]));
  const roles = correctionRoles(edges);

  return (
    <section aria-label="Graph as text" className="h-full space-y-4 overflow-y-auto p-6">
      <div role="status">
        <p className="text-sm text-primary">{reason}</p>
        <p className="mt-2 text-sm text-secondary">
          {tail ? `Aircraft ${tail}` : 'Whole fleet'}: {nodes.length} nodes · {edges.length} edges ·{' '}
          {corrections} {corrections === 1 ? 'correction' : 'corrections'}
        </p>
      </div>
      <NodesTable nodes={nodes} roles={roles} />
      <EdgesTable edges={edges} names={names} />
    </section>
  );
}
