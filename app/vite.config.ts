import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// - `--mode mock` (npm run dev:mock / build:mock) forces VITE_API_BASE=mock: canned SYNTHETIC
//   responses served in the browser, no backend needed.
// - In dev, same-origin /api calls (VITE_API_BASE empty) are proxied to the local service,
//   so no CORS setup is needed. Override the target with ANVESHAN_API_PROXY.
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  define: mode === 'mock' ? { 'import.meta.env.VITE_API_BASE': JSON.stringify('mock') } : {},
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: process.env.ANVESHAN_API_PROXY ?? 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
}));
