const BLOCK = 'animate-pulse rounded bg-black/10 dark:bg-white/10';

function Line({ width }) {
  return <div className={`${BLOCK} h-3.5`} style={{ width }} />;
}

/** variant "line" shows stacked text lines; "card" shows a card-shaped block. */
export default function Skeleton({ variant = 'line', lines = 3, className = '' }) {
  const widths = Array.from({ length: lines }, (_, i) => (i === lines - 1 ? '60%' : '100%'));
  return (
    <div role="status" className={className}>
      <span className="sr-only">Loading</span>
      <div aria-hidden="true">
        {variant === 'card' ? (
          <div className="halite-card space-y-3 p-5">
            <div className={`${BLOCK} h-5 w-1/3`} />
            {widths.map((width, i) => <Line key={i} width={width} />)}
          </div>
        ) : (
          <div className="space-y-2">
            {widths.map((width, i) => <Line key={i} width={width} />)}
          </div>
        )}
      </div>
    </div>
  );
}
