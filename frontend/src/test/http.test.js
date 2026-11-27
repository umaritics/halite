import { describe, it, expect, vi, beforeEach } from 'vitest';
import api, { setRefreshSessionHandler } from '../api/http';
import { maintenanceAPI } from '../api/client';

function mockAdapter(statusFor) {
  const calls = [];
  api.defaults.adapter = async (config) => {
    calls.push(config);
    const status = statusFor(config, calls.length);
    const response = { data: {}, status, statusText: '', headers: {}, config };
    if (status >= 400) {
      const error = new Error(`status ${status}`);
      error.config = config;
      error.response = response;
      throw error;
    }
    return response;
  };
  return calls;
}

describe('http layer', () => {
  beforeEach(() => {
    setRefreshSessionHandler(null);
  });

  it('sets a default timeout of 30 seconds', () => {
    expect(api.defaults.timeout).toBe(30000);
  });

  it('refreshes once and retries once on a 401 for a normal route', async () => {
    const refresh = vi.fn().mockResolvedValue('new-token');
    setRefreshSessionHandler(refresh);
    const calls = mockAdapter((config, n) => (n === 1 ? 401 : 200));

    const res = await api.get('/maintenance/assets');

    expect(res.status).toBe(200);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(calls).toHaveLength(2);
    expect(calls[1].headers.Authorization).toBe('Bearer new-token');
  });

  it('does not refresh on a 401 from an auth handshake route', async () => {
    const refresh = vi.fn().mockResolvedValue('new-token');
    setRefreshSessionHandler(refresh);
    const calls = mockAdapter(() => 401);

    await expect(api.post('/auth/login', {})).rejects.toBeTruthy();

    expect(refresh).not.toHaveBeenCalled();
    expect(calls).toHaveLength(1);
  });

  it('keeps the maintenanceAPI keys unchanged', () => {
    expect(Object.keys(maintenanceAPI).sort()).toEqual(
      [
        'accept',
        'analysisStatus',
        'assetHistory',
        'assets',
        'corrections',
        'getRecord',
        'ingest',
        'ingestFile',
        'records',
        'reject',
        'reviewQueue',
        'submitRecord',
      ].sort(),
    );
  });
});
