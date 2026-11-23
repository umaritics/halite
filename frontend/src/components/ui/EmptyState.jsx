export default function EmptyState({ title, body, action, children }) {
  const text = body ?? children;
  return (
    <section className="halite-card p-6">
      <h2 className="font-brand text-lg text-primary">{title}</h2>
      {text && <p className="mt-2 text-sm text-secondary">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </section>
  );
}
