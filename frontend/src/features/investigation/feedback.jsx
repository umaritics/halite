import { formatDetail } from '../../utils/diagnostics';

export function investigationError(error) {
  const status = error?.response?.status;
  const detail = formatDetail(error?.response?.data?.detail);
  if (status === 401) return 'Please sign in again to access your investigations.';
  if (status === 403) return detail || 'You can view this investigation, but only its owner can change it.';
  if (status === 404) return 'This investigation or aircraft is unavailable to your account.';
  if (status === 409) return detail || 'This investigation changed. Reload it before continuing.';
  if (status === 422) return detail || 'Check the information you entered.';
  if (status === 429) return 'Too many requests. Wait briefly, then try again.';
  if (error?.code === 'ECONNABORTED') return 'The request timed out. Reload to check whether the server saved your change before retrying.';
  return detail || 'Halite could not complete this request. Check your connection and try again.';
}

export function ErrorCard({ message, onRetry, retryLabel = 'Try again' }) {
  if (!message) return null;
  return <div role="alert" className="halite-card border-red-500/40 p-4">
    <p className="text-sm text-primary">{message}</p>
    {onRetry && <button type="button" className="halite-btn-outline mt-3" onClick={onRetry}>{retryLabel}</button>}
  </div>;
}

export function PageHeader({ title, description, children }) {
  return <header className="flex flex-wrap items-start justify-between gap-4 border-b border-theme pb-4">
    <div className="min-w-0 max-w-full"><h1 className="break-words font-brand text-2xl text-primary">{title}</h1>
      {description && <p className="mt-1 text-sm text-secondary">{description}</p>}</div>
    {children}
  </header>;
}
