// Plain-language names for the conflict engine's analysis labels and for record
// review statuses. Shared by StatusChip and the review queue.

export const ANALYSIS_LABELS = {
  no_conflict: { text: 'No conflict', tone: 'neutral' },
  scope_disjoint: { text: 'Different scope', tone: 'neutral' },
  supersedes: { text: 'Supersedes', tone: 'accent' },
  partial_supersedes: { text: 'Partially supersedes', tone: 'warning' },
  contradicts: { text: 'Contradicts', tone: 'danger' },
};

export const STATUS_LABELS = {
  unscored: { text: 'Not analysed', tone: 'neutral' },
  no_action: { text: 'No action needed', tone: 'neutral' },
  auto_accepted: { text: 'Auto Accepted', tone: 'accent' },
  needs_review: { text: 'Needs Review', tone: 'warning' },
  accepted: { text: 'Accepted', tone: 'success' },
  rejected: { text: 'Rejected', tone: 'neutral' },
  superseded: { text: 'Superseded', tone: 'neutral' },
};

// "some_new_value" becomes "Some new value" so an unknown value never shows raw.
function humanize(value) {
  const words = String(value ?? '').replace(/_/g, ' ').trim();
  if (!words) return 'Unknown';
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function describeLabel(value) {
  const known = STATUS_LABELS[value] || ANALYSIS_LABELS[value];
  return known || { text: humanize(value), tone: 'neutral' };
}

export function labelText(value) {
  return describeLabel(value).text;
}
