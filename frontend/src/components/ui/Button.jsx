import { forwardRef } from 'react';

const VARIANTS = {
  primary: 'halite-btn-primary',
  outline: 'halite-btn-outline',
  ghost: 'halite-btn-ghost',
  danger:
    'halite-btn rounded-md border border-red-600 px-4 py-2 text-red-600 ' +
    'hover:bg-red-600 hover:text-white',
};

const SIZES = {
  sm: '!px-3 !py-1.5 !text-xs',
  md: '',
};

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ' +
  'focus-visible:ring-offset-2 focus-visible:ring-offset-white ' +
  'dark:focus-visible:ring-offset-black';

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
  );
}

const Button = forwardRef(function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  type = 'button',
  className = '',
  children,
  ...props
}, ref) {
  const classes = [
    VARIANTS[variant] || VARIANTS.primary,
    SIZES[size] ?? '',
    FOCUS_RING,
    'disabled:cursor-not-allowed disabled:opacity-50',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      ref={ref}
      type={type}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <Spinner />}
      {children}
      {loading && <span className="sr-only">Loading</span>}
    </button>
  );
});

export default Button;
