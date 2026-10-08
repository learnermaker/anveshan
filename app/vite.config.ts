import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// - `--mode mock` (npm run dev:mock / build:mock) forces VITE_API_BASE=mock: canned SYNTHETIC
//   responses served in the browser, no backend needed.
// - In dev, same-origin /api calls (VITE_API_BASE empty) are proxied to the local service,
//   so no CORS setup is needed. Override the target with ANVESHAN_API_PROXY.
// - In non-mock builds, the mock backend is aliased to a stub so it is excluded from the bundle.
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  define: mode === 'mock' ? { 'import.meta.env.VITE_API_BASE': JSON.stringify('mock') } : {},
  resolve: mode !== 'mock' ? {
    alias: {
      // Exclude mock backend from production chunk — alias to a stub that throws.
      // Both the bare specifier form (resolved to dir) and the fully-resolved .ts form are
      // listed so the alias fires regardless of whether Vite canonicalises the path before
      // or after extension resolution (behaviour changed across Vite 5.x minor versions).
      [path.resolve(__dirname, 'src/api/mock.ts')]: path.resolve(__dirname, 'src/api/mock-empty.ts'),
      [path.resolve(__dirname, 'src/api/mock')]: path.resolve(__dirname, 'src/api/mock-empty.ts'),
    },
  } : {},
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Split vendor libs into a separate chunk to keep main chunk under 500 kB
          vendor: ['react', 'react-dom'],
          icons: ['lucide-react'],
        },
      },
    },
  },
  server: {
    port: 5173,
    host: true,
    // The app imports a few canonical files from ../tracks instead of keeping copies (single-copy rule).
    fs: { allow: [__dirname, path.resolve(__dirname, '../tracks')] },
    proxy: {
      '/api': {
        target: process.env.ANVESHAN_API_PROXY ?? 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
}));
