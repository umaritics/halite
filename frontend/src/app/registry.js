// Single source for signed-in routes and navigation. Each feature exposes
// `routes` and `nav` from features/<name>/manifest.jsx (see README.md).
const manifests = Object.values(import.meta.glob('../features/*/manifest.jsx', { eager: true }));

const byOrder = (a, b) => (a.order ?? 100) - (b.order ?? 100);

export const featureRoutes = manifests.flatMap(manifest => manifest.routes || []);
export const featureNav = manifests.flatMap(manifest => manifest.nav || []).sort(byOrder);
