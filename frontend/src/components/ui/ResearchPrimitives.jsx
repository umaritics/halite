// Compatibility re-exports for src/features/investigation. The research pages
// expect an outline Button by default, so only that default is adapted here.
import UiButton from './Button';

export function Button({ variant = 'outline', ...props }) {
  return <UiButton variant={variant} {...props} />;
}

export { default as PageHeader } from './PageHeader';
export { default as ErrorCard } from './ErrorCard';
export { default as EmptyState } from './EmptyState';
