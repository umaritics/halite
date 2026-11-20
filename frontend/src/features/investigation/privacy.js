export const LEGACY_INVESTIGATION_KEYS = [
  'halite-diagnostic-active-workspace',
  'halite-diagnostic-copilot-sessions',
];

// Legacy records have no owner. Never import them into an authenticated session.
export function clearLegacyInvestigations(storage) {
  try {
    const target = storage || window.localStorage;
    for (const key of LEGACY_INVESTIGATION_KEYS) target.removeItem(key);
    return true;
  } catch {
    return false;
  }
}
