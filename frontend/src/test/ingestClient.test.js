import { afterEach, describe, expect, it, vi } from 'vitest';
import api, { maintenanceAPI } from '../api/client';

describe('maintenanceAPI.ingestFile', () => {
  afterEach(() => vi.restoreAllMocks());

  it('posts to the multipart upload route, not the JSON csv_path route', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: {} });
    const body = new FormData();
    await maintenanceAPI.ingestFile(body);
    expect(post).toHaveBeenCalledWith('/maintenance/ingest/upload', body, expect.anything());
  });
});
