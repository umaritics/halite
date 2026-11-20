// Small shared preparation proposal; existing feature pages are unchanged.
export function Button({ children, ...props }) {
  return <button type="button" className="halite-btn-outline disabled:opacity-50" {...props}>{children}</button>;
}
export function PageHeader({ title, description, children }) {
  return <header className="flex flex-wrap items-start justify-between gap-4 border-b border-theme pb-4">
    <div className="min-w-0"><h1 className="font-brand text-2xl text-primary">{title}</h1><p className="mt-2 text-sm text-secondary">{description}</p></div>{children}
  </header>;
}
export function ErrorCard({ message, onRetry }) {
  return <div role="alert" className="halite-card space-y-3 border-red-500/40 p-5"><p className="text-primary">{message}</p><Button onClick={onRetry}>Try again</Button></div>;
}
export function EmptyState({ title, children }) {
  return <section className="halite-card p-6"><h2 className="font-brand text-lg text-primary">{title}</h2><p className="mt-2 text-sm text-secondary">{children}</p></section>;
}
