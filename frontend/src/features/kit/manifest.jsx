import { lazy, Suspense } from 'react';

// Development-only component gallery. No nav entry, and the route list is
// empty in production builds so the gallery never ships.
export const routes = [];

if (import.meta.env.DEV) {
  const KitGallery = lazy(() => import('./KitGallery'));
  routes.push({
    path: '/app/_kit',
    element: (
      <Suspense fallback={null}>
        <KitGallery />
      </Suspense>
    ),
  });
}
