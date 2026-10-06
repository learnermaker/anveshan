/**
 * Production stub for the mock backend. Imported only in non-mock builds via Vite alias.
 * The api constant in client.ts is always httpApi in production; this export is never called.
 */
import type { Api } from './client';

export const mockApi: Api = new Proxy({} as Api, {
  get(_, prop) {
    return () => {
      throw new Error(`[anveshan] mock api called in production (${String(prop)}) — this is a bug`);
    };
  },
});
