import { afterEach, describe, expect, it, vi } from 'vitest';
import api, {
  applyAuthHeaders,
  maintenanceAPI,
  setSessionTokenGetter,
} from '../api/client';
import { describeLoadError } from '../utils/loadError';
import { describeDiagnosticError } from '../utils/diagnostics';

describe('API client security & ingest wiring', () => {
  afterEach(() => {
    setSessionTokenGetter(null);
    vi.restoreAllMocks();
  });

  it('posts to the multipart upload route, not the JSON csv_path route', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: {} });
    const body = new FormData();
    await maintenanceAPI.ingestFile(body);
    expect(post).toHaveBeenCalledWith('/maintenance/ingest/upload', body, expect.anything());
  });

  it('attaches Bearer token from env key when present', () => {
    const cfg = applyAuthHeaders({ headers: { 'Content-Type': 'application/json' } }, 'env-secret-key');
    expect(cfg.headers.Authorization).toBe('Bearer env-secret-key');
  });

  it('prefers runtime session token over static env key for upcoming user auth', () => {
    setSessionTokenGetter(() => 'user-jwt-token');
    const cfg = applyAuthHeaders({ headers: {} }, 'env-secret-key');
    expect(cfg.headers.Authorization).toBe('Bearer user-jwt-token');
  });

  it('does not overwrite an explicit Authorization header or inject blank Bearer', () => {
    const empty = applyAuthHeaders({ headers: {} }, '   ');
    expect(empty.headers.Authorization).toBeUndefined();

    const explicit = applyAuthHeaders(
      { headers: { Authorization: 'Bearer custom-override' } },
      'env-secret-key',
    );
    expect(explicit.headers.Authorization).toBe('Bearer custom-override');
  });

  it('maps HTTP 401/403 and 429 cleanly in loadError and diagnostic helpers', () => {
    const load401 = describeLoadError({
      response: { status: 401, data: { detail: 'Invalid or missing API key.' } },
    });
    expect(load401.kind).toBe('unauthorized');
    expect(load401.message).toContain('Invalid or missing API key');

    const load429 = describeLoadError({
      response: { status: 429, data: { detail: 'API rate limit exceeded.' } },
    });
    expect(load429.kind).toBe('rate-limited');

    const diag401 = describeDiagnosticError({
      response: { status: 401, data: { detail: 'Invalid or missing API key.' } },
    });
    expect(diag401.kind).toBe('unauthorized');
    expect(diag401.retryable).toBe(false);
  });
});
