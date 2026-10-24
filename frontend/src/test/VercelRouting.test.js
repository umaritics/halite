import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const config = JSON.parse(
  readFileSync(resolve(process.cwd(), '../vercel.json'), 'utf8'),
);

describe('Vercel routing', () => {
  it('keeps API routing ahead of the frontend service', () => {
    expect(config.rewrites[0]).toEqual({
      source: '/api(/.*)?',
      destination: {
        type: 'service',
        service: 'backend',
      },
    });
    expect(config.rewrites[1].destination).toEqual({
      type: 'service',
      service: 'frontend',
    });
  });

  it('serves the React entry point for direct application routes only', () => {
    expect(config.services.frontend.rewrites).toEqual([
      {
        source: '/app/:path*',
        destination: '/index.html',
      },
    ]);

    const applicationRoutes = [
      '/app',
      '/app/diagnostics',
      '/app/assets',
      '/app/records',
      '/app/graph',
      '/app/asset-history/aircraft-uuid',
    ];
    expect(applicationRoutes.every((path) => path === '/app' || path.startsWith('/app/'))).toBe(true);

    const nonApplicationRoutes = ['/', '/api/health', '/api/maintenance/assets', '/assets/index.js'];
    expect(nonApplicationRoutes.some((path) => path === '/app' || path.startsWith('/app/'))).toBe(false);
  });
});
