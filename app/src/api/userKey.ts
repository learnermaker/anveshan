/**
 * The visitor's own Gemini API key (bring your own key), kept only in this browser.
 *
 * - Default: sessionStorage (gone when the tab closes). "Remember on this device" uses localStorage.
 * - Sent only as the X-Gemini-Api-Key header to this app's own service, never in a URL.
 * - Storage can be unavailable (private mode, blocked site data): every access is wrapped and the
 *   key then lives in memory for this page only.
 */

const STORE_KEY = 'anveshan.gemini_key';
let memoryKey: string | null = null;
const listeners = new Set<(k: string | null) => void>();

function read(storage: () => Storage): string | null {
  try {
    return storage().getItem(STORE_KEY);
  } catch {
    return null;
  }
}

export function getUserKey(): string | null {
  return memoryKey ?? read(() => window.sessionStorage) ?? read(() => window.localStorage);
}

export function isRemembered(): boolean {
  return Boolean(read(() => window.localStorage));
}

export function setUserKey(key: string, remember: boolean): void {
  const k = key.trim();
  clearUserKey(false);
  memoryKey = k;
  try {
    (remember ? window.localStorage : window.sessionStorage).setItem(STORE_KEY, k);
  } catch {
    /* storage blocked: memory only */
  }
  listeners.forEach((l) => l(k));
}

export function clearUserKey(notify = true): void {
  memoryKey = null;
  for (const s of [() => window.sessionStorage, () => window.localStorage]) {
    try {
      s().removeItem(STORE_KEY);
    } catch {
      /* ignore */
    }
  }
  if (notify) listeners.forEach((l) => l(null));
}

export function subscribeUserKey(fn: (k: string | null) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/**
 * Loose client-side shape check (the server validates for real).
 * New Gemini auth keys (issued from May 2026) start with "AQ." and contain base64url characters
 * including dots. Older standard keys start with "AIza" and use only letters, digits, - and _.
 */
export function looksLikeKey(key: string): boolean {
  return /^[A-Za-z0-9_.+/=\-]{20,250}$/.test(key.trim());
}

export function maskKey(key: string): string {
  return key.length > 8 ? `${key.slice(0, 4)}…${key.slice(-4)}` : '••••';
}

/** Ask the app to open the key dialog (used by error messages). */
export function requestKeyDialog(): void {
  window.dispatchEvent(new CustomEvent('anveshan:open-key-dialog'));
}
