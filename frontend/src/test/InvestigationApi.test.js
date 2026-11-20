import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api/client';
import { sessionsAPI } from '../features/investigation/api';

vi.mock('../api/client', () => ({ default: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => vi.resetAllMocks());

describe('Investigation transport contracts', () => {
  it('opts quick diagnosis into model-off operation on the existing authenticated client', () => {
    sessionsAPI.diagnose('asset-uuid', 'pump leak');
    expect(api.post).toHaveBeenCalledWith('/maintenance/diagnose', {
      asset_id: 'asset-uuid', symptom_text: 'pump leak', allow_degraded: true,
    }, { timeout: 300000 });
  });
  it('encodes a session ID as one path segment and bounds every request', () => {
    const signal = new AbortController().signal;
    sessionsAPI.get('id/extra', signal);
    expect(api.get).toHaveBeenCalledWith('/sessions/id%2Fextra', { signal, timeout: 15000 });
    sessionsAPI.turn('id', { message: 'test' });
    expect(api.post).toHaveBeenCalledWith('/sessions/id/turns', { message: 'test' }, { timeout: 300000 });
    sessionsAPI.close('id', { outcome_note: 'found seal' });
    expect(api.post).toHaveBeenCalledWith('/sessions/id/close', { outcome_note: 'found seal' }, { timeout: 15000 });
  });
  it('fetches printable reports with the shared JWT client rather than an unauthenticated link', () => {
    sessionsAPI.report('id');
    expect(api.get).toHaveBeenCalledWith('/sessions/id/report', { timeout: 15000, responseType: 'text' });
  });
});
