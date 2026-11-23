export default function PageHeader({ title, description, actions, children }) {
  const slot = actions ?? children;
  return (
    <header className="flex flex-wrap items-start justify-between gap-4 border-b border-theme pb-4">
      <div className="min-w-0">
        <h1 className="font-brand text-2xl text-primary">{title}</h1>
        {description && <p className="mt-2 text-sm text-secondary">{description}</p>}
      </div>
      {slot}
    </header>
  );
}
