const TONES = {
  neutral: 'border-theme text-secondary',
  accent: 'border-accent/50 bg-accent/10 text-accent',
  success: 'border-green-600/40 bg-green-600/10 text-green-700 dark:text-green-400',
  warning: 'border-amber-600/40 bg-amber-500/10 text-amber-700 dark:text-amber-400',
  danger: 'border-red-600/40 bg-red-600/10 text-red-700 dark:text-red-400',
};

export default function Badge({ tone = 'neutral', className = '', children }) {
  return (
    <span
      className={[
        'inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium',
        TONES[tone] || TONES.neutral,
        className,
      ].join(' ')}
    >
      {children}
    </span>
  );
}
