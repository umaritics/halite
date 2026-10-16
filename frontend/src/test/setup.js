import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Node >= 25 ships an experimental global `localStorage` that shadows jsdom's
// and is unusable without --localstorage-file. Install an in-memory Storage so
// tests behave the same on every Node version (CI runs Node 20).
if (typeof localStorage === 'undefined' || typeof localStorage.clear !== 'function') {
  const store = new Map();
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => { store.set(String(k), String(v)); },
      removeItem: (k) => { store.delete(k); },
      clear: () => { store.clear(); },
      key: (i) => Array.from(store.keys())[i] ?? null,
      get length() { return store.size; },
    },
  });
}

afterEach(() => {
  cleanup();
});
