import { Button } from '../../components/ui';

// Sticky footer with the review note and Accept/Reject. Colours come from the theme
// tokens so it reads in both light and dark mode.
export default function DecisionBar({ canAdjudicate, role, decision }) {
  const { note, setNote, pending, submit } = decision;

  return (
    <div className="sticky bottom-0 mt-6 border-t border-theme bg-surface pb-2 pt-4">
      {!canAdjudicate ? (
        <div className="rounded-md border border-theme bg-surface p-3 font-sans text-xs text-secondary">
          Signed in as <span className="font-mono text-primary">{role || 'technician'}</span>.
          Supervisor or administrator access is required to accept or reject conflict findings.
        </div>
      ) : (
        <>
          <textarea
            className="halite-input mb-3 w-full text-sm"
            rows={2}
            placeholder="Add a review note (required for rejection)..."
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
          <div className="flex gap-3">
            <Button
              className="flex-1"
              onClick={() => submit('accept')}
              disabled={Boolean(pending)}
            >
              {pending === 'accept' ? 'Accepting…' : 'Accept'}
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => submit('reject')}
              disabled={Boolean(pending)}
            >
              {pending === 'reject' ? 'Rejecting…' : 'Reject'}
            </Button>
          </div>
          <p className="mt-2 font-sans text-[11px] text-secondary">
            Accept marks this record as reviewed and accepted. Reject marks it rejected and stores your note.
            Your reviewer identity is recorded in the audit trail; neither action deletes the record.
          </p>
        </>
      )}
    </div>
  );
}
