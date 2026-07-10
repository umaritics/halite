export default function HaliteLogo({ className = 'h-8 w-8', alt = 'Halite' }) {
  return (
    <img
      src="/halite-logo.png"
      alt={alt}
      className={`shrink-0 object-contain ${className}`}
      decoding="async"
      fetchPriority="high"
    />
  );
}
