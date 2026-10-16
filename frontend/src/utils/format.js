// Display helpers shared by the maintenance pages.

// Show a date, or say plainly that none was recorded. `new Date(undefined)` would
// otherwise render the literal text "Invalid Date" on screen.
export function formatDate(value) {
  if (!value) return 'Date not recorded';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? 'Date not recorded' : d.toLocaleDateString();
}

// Timestamp for sorting; records with no usable date sort after dated ones.
export function dateValue(value) {
  const t = value ? Date.parse(value) : NaN;
  return Number.isNaN(t) ? Number.POSITIVE_INFINITY : t;
}
