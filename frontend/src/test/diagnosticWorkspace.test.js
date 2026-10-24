import { beforeEach, describe, expect, it } from 'vitest';
import {
  ACTIVE_DIAGNOSTIC_WORKSPACE_KEY,
  ACTIVE_DIAGNOSTIC_WORKSPACE_MAX_AGE_MS,
  ACTIVE_DIAGNOSTIC_WORKSPACE_VERSION,
  clearActiveDiagnosticWorkspace,
  loadActiveDiagnosticWorkspace,
  storeActiveDiagnosticWorkspace,
} from '../utils/diagnosticWorkspace';

const snapshot = {
  assetId: 'asset-1',
  draft: 'unsent note',
  sessionId: 'session-1',
  selectedPartName: 'DRAG ANGLE',
  inspectorRecords: { SWIA2024010100001: { record_id: 'SWIA2024010100001', part_name: 'DRAG ANGLE' } },
  thread: [
    { role: 'user', content: 'crack found' },
    { role: 'assistant', content: 'Inspect the drag angle.', response: { ranked_checks: [{ part_name: 'DRAG ANGLE', rank: 1 }], evidence: [] } },
  ],
  caseState: {
    symptoms: ['crack found'], observations: [], checks_done: [], ruled_out: [], open_questions: [],
  },
  composerExpanded: true,
  scroll: { conversation: 48, investigation: 72, followConversation: false },
};

describe('active diagnostic workspace persistence', () => {
  beforeEach(() => window.localStorage.clear());

  it('round-trips the active workspace independently of manual saved sessions', () => {
    const manualSessions = JSON.stringify([
      { id: 'manual-1', title: 'Saved investigation' },
      { id: 'manual-2', title: 'Second saved investigation' },
    ]);
    window.localStorage.setItem('halite-diagnostic-copilot-sessions', manualSessions);
    expect(storeActiveDiagnosticWorkspace(snapshot, 1000)).toBe(true);
    expect(loadActiveDiagnosticWorkspace(1000)).toEqual(snapshot);
    expect(window.localStorage.getItem('halite-diagnostic-copilot-sessions')).toBe(manualSessions);
  });

  it('migrates prior snapshots to the compact state after a completed turn but keeps drafts expanded', () => {
    const priorSnapshot = { ...snapshot };
    delete priorSnapshot.composerExpanded;
    window.localStorage.setItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY, JSON.stringify({
      ...priorSnapshot, draft: '', version: ACTIVE_DIAGNOSTIC_WORKSPACE_VERSION, updatedAt: 1000,
    }));
    expect(loadActiveDiagnosticWorkspace(1000).composerExpanded).toBe(false);

    window.localStorage.setItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY, JSON.stringify({
      ...priorSnapshot, version: ACTIVE_DIAGNOSTIC_WORKSPACE_VERSION, updatedAt: 1000,
    }));
    expect(loadActiveDiagnosticWorkspace(1000).composerExpanded).toBe(true);
  });

  it('clears empty, corrupt, expired, and incompatible snapshots safely', () => {
    expect(storeActiveDiagnosticWorkspace({ ...snapshot, assetId: '', draft: '', thread: [], caseState: {
      symptoms: [], observations: [], checks_done: [], ruled_out: [], open_questions: [],
    } })).toBe(true);
    expect(window.localStorage.getItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY)).toBeNull();

    window.localStorage.setItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY, '{broken');
    expect(loadActiveDiagnosticWorkspace()).toBeNull();
    expect(window.localStorage.getItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY)).toBeNull();

    window.localStorage.setItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY, JSON.stringify({
      ...snapshot, version: ACTIVE_DIAGNOSTIC_WORKSPACE_VERSION, updatedAt: 1000,
    }));
    expect(loadActiveDiagnosticWorkspace(1000 + ACTIVE_DIAGNOSTIC_WORKSPACE_MAX_AGE_MS + 1)).toBeNull();

    window.localStorage.setItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY, JSON.stringify({
      ...snapshot, version: ACTIVE_DIAGNOSTIC_WORKSPACE_VERSION + 1, updatedAt: 2000,
    }));
    expect(loadActiveDiagnosticWorkspace(2000)).toBeNull();
  });

  it('explicit clearing removes only the active workspace', () => {
    storeActiveDiagnosticWorkspace(snapshot);
    window.localStorage.setItem('halite-diagnostic-copilot-sessions', '[{"id":"manual"}]');
    expect(clearActiveDiagnosticWorkspace()).toBe(true);
    expect(window.localStorage.getItem(ACTIVE_DIAGNOSTIC_WORKSPACE_KEY)).toBeNull();
    expect(window.localStorage.getItem('halite-diagnostic-copilot-sessions')).toBe('[{"id":"manual"}]');
  });
});
