/**
 * Client-side runtime settings: API base and the requested service mode.
 * The mode preference is a per-viewer convenience (localStorage, failure-tolerant);
 * the server remains the authority on what actually ran (runtime_class on each result).
 */

import type { ServiceMode } from './types';

const MODE_KEY = 'anveshan.requested_mode';

const rawBase: string | undefined = import.meta.env.VITE_API_BASE;

/** True when VITE_API_BASE === 'mock': all API calls are served by canned SYNTHETIC fixtures. */
export const IS_MOCK = rawBase === 'mock';

/** Base URL for the service ('' = same origin). */
export const API_BASE = IS_MOCK ? '' : (rawBase ?? '').replace(/\/+$/, '');

export type RequestedMode = ServiceMode | 'default';

let requestedMode: RequestedMode = readMode();
const listeners = new Set<(m: RequestedMode) => void>();

function readMode(): RequestedMode {
  try {
    const v = localStorage.getItem(MODE_KEY);
    if (v === 'live' || v === 'recorded') return v;
  } catch {
    /* storage unavailable */
  }
  return 'default';
}

export function getRequestedMode(): RequestedMode {
  return requestedMode;
}

export function setRequestedMode(mode: RequestedMode): void {
  requestedMode = mode;
  try {
    if (mode === 'default') localStorage.removeItem(MODE_KEY);
    else localStorage.setItem(MODE_KEY, mode);
  } catch {
    /* storage unavailable */
  }
  listeners.forEach((l) => l(mode));
}

export function subscribeMode(listener: (m: RequestedMode) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
