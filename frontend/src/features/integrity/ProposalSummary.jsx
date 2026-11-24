import { Badge } from '../../components/ui';

const FIELD_NAMES = {
  part_name: 'Part',
  jasc_code: 'JASC',
  part_location: 'Location',
  part_condition: 'Condition',
};

// The link's own method wins over the analysis method: a person's decision or a cited
// report ID is how the pair was really chosen, whatever the model first said.
function proposedBy(proposal) {
  const method = proposal.link?.method || proposal.method;
  if (method === 'human') return 'Human decision';
  if (method === 'explicit_citation') return 'Linked by citation';
  return method ? 'Model proposal' : null;
}

const shown = (value) => value || '(blank)';

// How the pair was proposed and what differs between the two reports. Only rendered
// when there is a proposed prior; the panel explains its absence itself.
export default function ProposalSummary({ proposal }) {
  if (!proposal.proposed_prior) return null;
  const how = proposedBy(proposal);
  const changes = proposal.changed_fields || [];
  return (
    <div className="space-y-3 font-sans text-sm">
      {how && <Badge tone="accent">{how}</Badge>}
      {proposal.proposal_source === 'recomputed' && (
        <p className="text-xs text-secondary">
          This earlier report was re-derived just now; it was not stored when the record was analysed.
        </p>
      )}
      <div>
        <span className="eyebrow mb-1 block">WHAT CHANGED</span>
        {changes.length === 0 ? (
          <p className="text-secondary">No tracked fields changed between the two reports.</p>
        ) : (
          <ul className="space-y-1 text-primary">
            {changes.map((change) => (
              <li key={change.field}>
                {FIELD_NAMES[change.field] || change.field}: {shown(change.prior)} → {shown(change.new)}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
