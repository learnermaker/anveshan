import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev, same-origin /api calls (VITE_API_BASE empty) are proxied to the local service,
// so no CORS setup is needed. Override the target with ANVESHAN_API_PROXY.
export default defineConfig({
  plugins: [react()],
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
});
