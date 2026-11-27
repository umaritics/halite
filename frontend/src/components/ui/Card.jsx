export default function Card({ title, className = '', children }) {
  return (
    <section className={`halite-card p-5 ${className}`.trim()}>
      {title && <h2 className="mb-3 font-brand text-lg text-primary">{title}</h2>}
      {children}
    </section>
  );
}
