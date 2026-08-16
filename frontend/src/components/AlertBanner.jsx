import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

function formatAlertDate(alert) {
  const raw =
    alert.flagged_at ||
    alert.commit?.timestamp ||
    alert.decision?.updated_at ||
    alert.decision?.created_at;
  if (!raw || typeof raw !== 'string') return 'Date unknown';
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export default function AlertBanner({ alert, onView, onAcknowledge, onInvalidate }) {
  const { decision, commit, component } = alert;

  return (
    <div className="halite-card border-accent/30 p-5">
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-accent/10 p-2 ring-1 ring-accent/30">
          <ExclamationTriangleIcon className="h-5 w-5 text-accent" />
        </div>
        <div className="flex-1">
          <h3 className="font-brand text-primary">{decision.title}</h3>
          <p className="mt-1 font-sans text-xs text-[#888888]">{formatAlertDate(alert)}</p>
          <p className="mt-1 line-clamp-2 font-sans text-sm text-secondary">{decision.reasoning}</p>

          <div className="mt-3 space-y-1 font-sans text-xs text-[#555555]">
            {component && (
              <p>
                <span className="text-secondary">Component:</span> {component.name}
              </p>
            )}
            {commit && (
              <p>
                <span className="text-secondary">Triggered by commit:</span>{' '}
                <code className="font-mono text-accent">{commit.id?.slice(0, 8)}</code>
                {commit.files_changed?.length > 0 && (
                  <span> — {commit.files_changed.join(', ')}</span>
                )}
              </p>
            )}
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <button onClick={() => onView?.(decision)} className="halite-btn-ghost text-xs">
              View Full Decision
            </button>
            <button onClick={() => onAcknowledge?.(decision)} className="halite-btn-primary text-xs">
              Mark as Reviewed
            </button>
            <button
              onClick={() => onInvalidate?.(decision)}
              className="halite-btn text-xs text-red-400 ring-1 ring-red-500/30 hover:bg-red-500/10"
            >
              Invalidate
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
