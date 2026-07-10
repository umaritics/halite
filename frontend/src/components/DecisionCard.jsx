const statusClass = {
  active: 'status-active',
  needs_review: 'status-needs_review',
  invalidated: 'status-invalidated',
};

export default function DecisionCard({ decision, onClick }) {
  const components = decision.component_names || decision.components?.map((c) => c.name) || [];

  return (
    <button
      onClick={() => onClick?.(decision)}
      className="halite-card w-full p-4 text-left transition hover:border-accent"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-brand text-primary">{decision.title}</h3>
        <span className={statusClass[decision.status] || 'status-active'}>
          {decision.status?.replace('_', ' ')}
        </span>
      </div>
      <p className="mt-2 line-clamp-2 font-sans text-sm text-secondary">{decision.reasoning}</p>
      {components.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {components.map((name) => (
            <span
              key={name}
              className="rounded-md bg-accent/10 px-2 py-0.5 font-sans text-xs text-accent ring-1 ring-accent/20"
            >
              {name}
            </span>
          ))}
        </div>
      )}
      <div className="mt-3 flex items-center gap-3 font-sans text-xs text-[#555555]">
        <span>{decision.source}</span>
        <span>·</span>
        <span>{decision.created_at ? new Date(decision.created_at).toLocaleDateString() : '—'}</span>
      </div>
    </button>
  );
}
