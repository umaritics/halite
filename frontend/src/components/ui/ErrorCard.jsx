import Button from './Button';

export default function ErrorCard({ message, onRetry, retryLabel = 'Try again' }) {
  return (
    <div role="alert" className="halite-card space-y-3 border-red-500/40 p-5">
      <p className="text-primary">{message}</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  );
}
