import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// Base relativa: o mesmo dist/ serve no Worker (raiz) e no pacote offline (qualquer pasta).
export default defineConfig({
  base: './',
  plugins: [svelte()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true },
  build: { target: 'es2022', chunkSizeWarningLimit: 900 },
});
