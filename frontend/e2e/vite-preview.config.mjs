import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const root = fileURLToPath(new URL('..', import.meta.url));
export default defineConfig({
  root,
  plugins: [react()],
  build: {
    // Task-owned temporary output; never changes the production app entry point.
    outDir: '/tmp/halite-investigation-preview-dist',
    emptyOutDir: true,
    rollupOptions: { input: resolve(root, 'e2e/investigation-preview.html') },
  },
});
