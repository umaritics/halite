# App registry

The signed-in shell (`App.jsx`) and the sidebar (`components/Sidebar.jsx`) hold
no page lists. Both render from `registry.js`, which collects every
`src/features/*/manifest.jsx`.

## Manifest contract

A manifest exports two arrays, either may be omitted:

    export const routes = [{ path, element, roles? }];
    export const nav = [{ to, label, icon, order, roles?, useBadge? }];

- `path` is absolute, for example `/app/assets` or `/app/asset-history/:assetId`.
- `roles` limits a route or nav item to those user roles. Routes are wrapped in
  `ProtectedRoute`; nav items are hidden from other roles.
- `order` sorts the sidebar ascending (Home 0, Assets 10 ... Settings 80).
- `icon` is a component such as a heroicon.
- `useBadge` is a React hook returning a number or null. A positive number is
  shown as a count on the nav item. Each item renders in its own component, so
  the hook is called safely.

## Adding a feature

1. Create `src/features/<name>/manifest.jsx` with `routes` and `nav`.
2. Nothing else. No edits to `App.jsx` or `Sidebar.jsx`.

Every `nav.to` should have a matching route path; a test enforces this.
Routes with no nav entry (detail pages, redirects) are fine.
