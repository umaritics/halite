// Shared registration point proposed for Shahmeer's frontend preparation.
const manifests = Object.values(import.meta.glob('../features/*/manifest.jsx', { eager: true }));
export const featureRoutes = manifests.flatMap(manifest => manifest.routes || []);
export const featureNav = manifests.flatMap(manifest => manifest.nav || []);
