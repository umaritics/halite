// Aircraft show their tail number and service records their FAA record id; a UUID prefix
// means nothing to a reader.
export function getNodeLabel(node) {
  return (
    node.tail_number || node.record_id || node.name || node.title || node.filename || node.id?.slice(0, 8) || 'Node'
  );
}
