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

  it('serves the React entry point for direct auth and application routes only', () => {
    expect(config.services.frontend.rewrites).toEqual([
      {
        source: '/login',
        destination: '/index.html',
      },
      {
        source: '/accept-invite',
        destination: '/index.html',
      },
      {
        source: '/app/:path*',
        destination: '/index.html',
      },
    ]);

    const spaRoutes = [
      '/login',
      '/accept-invite',
      '/app',
      '/app/diagnostics',
      '/app/assets',
      '/app/records',
      '/app/graph',
      '/app/team',
      '/app/asset-history/aircraft-uuid',
    ];
    expect(
      spaRoutes.every(
        (path) =>
          path === '/login' ||
          path === '/accept-invite' ||
          path === '/app' ||
          path.startsWith('/app/'),
      ),
    ).toBe(true);

    const nonApplicationRoutes = ['/', '/api/health', '/api/maintenance/assets', '/assets/index.js'];
    expect(
      nonApplicationRoutes.some(
        (path) =>
          path === '/login' ||
          path === '/accept-invite' ||
          path === '/app' ||
          path.startsWith('/app/'),
      ),
    ).toBe(false);
  });
});
