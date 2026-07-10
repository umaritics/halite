export default function OctahedronIcon({ className = 'h-5 w-5', pulse = false }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`${className} ${pulse ? 'animate-pulse' : ''}`}
      aria-hidden="true"
    >
      <polygon points="10,1 19,6 19,14 10,19 1,14 1,6" stroke="#E8650A" strokeWidth="1.5" />
      <line x1="10" y1="1" x2="10" y2="19" stroke="#E8650A" strokeWidth="0.75" opacity="0.6" />
      <line x1="1" y1="6" x2="19" y2="14" stroke="#E8650A" strokeWidth="0.75" opacity="0.6" />
      <line x1="19" y1="6" x2="1" y2="14" stroke="#E8650A" strokeWidth="0.75" opacity="0.6" />
    </svg>
  );
}
