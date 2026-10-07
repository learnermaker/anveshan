/**
 * The steward access code, kept for this browser tab only (sessionStorage; memory when storage is
 * blocked). Sent only as the X-Steward-Token header to this app's own service, never in a URL.
 */

const STORE_KEY = 'anveshan.steward_token';
let memoryToken: string | null = null;
const listeners = new Set<(t: string | null) => void>();

export function getStewardToken(): string | null {
  if (memoryToken) return memoryToken;
  try {
    return window.sessionStorage.getItem(STORE_KEY);
  } catch {
    return null;
  }
}

export function setStewardToken(token: string): void {
  memoryToken = token.trim();
  try {
    window.sessionStorage.setItem(STORE_KEY, memoryToken);
  } catch {
    /* storage blocked: memory only */
  }
  listeners.forEach((l) => l(memoryToken));
}

export function clearStewardToken(): void {
  memoryToken = null;
  try {
    window.sessionStorage.removeItem(STORE_KEY);
  } catch {
    /* ignore */
  }
  listeners.forEach((l) => l(null));
}

export function subscribeStewardToken(fn: (t: string | null) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
