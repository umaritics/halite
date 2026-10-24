export const ACTIVE_DIAGNOSTIC_WORKSPACE_KEY = 'halite-diagnostic-active-workspace';
export const ACTIVE_DIAGNOSTIC_WORKSPACE_VERSION = 1;
export const ACTIVE_DIAGNOSTIC_WORKSPACE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;

const CASE_FIELDS = ['symptoms', 'observations', 'checks_done', 'ruled_out', 'open_questions'];

function validCaseState(caseState) {
  return caseState
    && typeof caseState === 'object'
    && CASE_FIELDS.every(field => Array.isArray(caseState[field]) && caseState[field].every(value => typeof value === 'string'));
}

function validThread(thread) {
  return Array.isArray(thread) && thread.every(turn => {
    if (!turn || typeof turn !== 'object') return false;
    if (turn.role === 'user') return typeof turn.content === 'string';
    return turn.role === 'assistant'
      && turn.response
      && typeof turn.response === 'object'
      && (turn.content === null || typeof turn.content === 'string');
  });
}

function finiteScroll(value) {
  return Number.isFinite(value) && value >= 0 ? value : 0;
}

export function hasActiveDiagnosticWorkspace(snapshot) {
  return Boolean(
    snapshot
    && (
      snapshot.assetId
      || snapshot.draft
      || snapshot.thread?.length
      || CASE_FIELDS.some(field => snapshot.caseState?.[field]?.length)
    )
  );
}

export function loadActiveDiagnosticWorkspace(now = Date.now()) {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY) || 'null');
    const compatible = parsed
      && parsed.version === ACTIVE_DIAGNOSTIC_WORKSPACE_VERSION
      && Number.isFinite(parsed.updatedAt)
      && now - parsed.updatedAt <= ACTIVE_DIAGNOSTIC_WORKSPACE_MAX_AGE_MS
      && typeof parsed.assetId === 'string'
      && typeof parsed.draft === 'string'
      && (parsed.sessionId === null || typeof parsed.sessionId === 'string')
      && (parsed.selectedPartName === null || typeof parsed.selectedPartName === 'string')
      && parsed.inspectorRecords
      && typeof parsed.inspectorRecords === 'object'
      && !Array.isArray(parsed.inspectorRecords)
      && validThread(parsed.thread)
      && validCaseState(parsed.caseState);

    if (!compatible) {
      if (parsed !== null) window.localStorage.removeItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY);
      return null;
    }

    return {
      assetId: parsed.assetId,
      draft: parsed.draft.slice(0, 4000),
      sessionId: parsed.sessionId,
      selectedPartName: parsed.selectedPartName,
      inspectorRecords: parsed.inspectorRecords,
      thread: parsed.thread,
      caseState: parsed.caseState,
      scroll: {
        conversation: finiteScroll(parsed.scroll?.conversation),
        investigation: finiteScroll(parsed.scroll?.investigation),
        followConversation: parsed.scroll?.followConversation !== false,
      },
    };
  } catch {
    try {
      window.localStorage.removeItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY);
    } catch {
      // Storage may be unavailable; Diagnostics remains usable in memory.
    }
    return null;
  }
}

export function clearActiveDiagnosticWorkspace() {
  try {
    window.localStorage.removeItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY);
    return true;
  } catch {
    return false;
  }
}

export function storeActiveDiagnosticWorkspace(snapshot, now = Date.now()) {
  if (!hasActiveDiagnosticWorkspace(snapshot)) return clearActiveDiagnosticWorkspace();
  try {
    window.localStorage.setItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY, JSON.stringify({
      version: ACTIVE_DIAGNOSTIC_WORKSPACE_VERSION,
      updatedAt: now,
      assetId: snapshot.assetId || '',
      draft: (snapshot.draft || '').slice(0, 4000),
      sessionId: snapshot.sessionId || null,
      selectedPartName: snapshot.selectedPartName || null,
      inspectorRecords: snapshot.inspectorRecords || {},
      thread: snapshot.thread,
      caseState: snapshot.caseState,
      scroll: {
        conversation: finiteScroll(snapshot.scroll?.conversation),
        investigation: finiteScroll(snapshot.scroll?.investigation),
        followConversation: snapshot.scroll?.followConversation !== false,
      },
    }));
    return true;
  } catch {
    return false;
  }
}
