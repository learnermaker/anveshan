/**
 * Typed client for the Anveshan service HTTP API (docs/plans/service-api.md §5).
 *
 * - Base URL: import.meta.env.VITE_API_BASE ('' = same origin).
 * - VITE_API_BASE === 'mock' routes every call to ./mock (canned SYNTHETIC fixtures).
 * - Errors are normalised to ApiError from {"error": {category, message, details}}.
 * - Optional ?mode=live|recorded is appended from the runtime panel's selection.
 * - Multipart uploads use XHR so upload progress can be reported.
 */

import { API_BASE, IS_MOCK, getRequestedMode } from './runtime';
import { mockApi } from './mock';
import { ApiError } from './errors';
import type {
  ApiErrorBody,
  AttemptKind,
  AttemptResult,
  CaseSummary,
  CaseView,
  HealthResponse,
  QueryAnswer,
  ReviewAction,
  SessionCreated,
  SessionResult,
  SessionView,
} from './types';

export { ApiError };

export type ProgressFn = (fraction: number) => void;

export interface CallOptions {
  /** Override the mode for this call (otherwise the runtime panel selection). */
  mode?: 'live' | 'recorded';
  signal?: AbortSignal;
}

function withMode(path: string, mode?: 'live' | 'recorded'): string {
  const m = mode ?? (getRequestedMode() === 'default' ? undefined : getRequestedMode());
  if (!m) return `${API_BASE}${path}`;
  return `${API_BASE}${path}${path.includes('?') ? '&' : '?'}mode=${encodeURIComponent(m)}`;
}

function toApiError(status: number, body: unknown, fallback: string): ApiError {
  const err = (body as ApiErrorBody | null)?.error;
  if (err && typeof err.message === 'string') {
    return new ApiError(err.category ?? 'UNKNOWN', err.message, status, err.details ?? null);
  }
  return new ApiError('UNKNOWN', fallback, status, body);
}

async function request<T>(method: 'GET' | 'POST', path: string, body?: unknown, opts: CallOptions = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(withMode(path, opts.mode), {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: opts.signal,
    });
  } catch (e) {
    throw new ApiError('NETWORK', `Service unreachable at ${API_BASE || window.location.origin}: ${(e as Error).message}`);
  }
  const text = await res.text();
  let parsed: unknown = null;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = text;
  }
  if (!res.ok) throw toApiError(res.status, parsed, `HTTP ${res.status} ${res.statusText}`);
  return parsed as T;
}

function upload<T>(path: string, form: FormData, onProgress?: ProgressFn, opts: CallOptions = {}): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', withMode(path, opts.mode));
    xhr.responseType = 'text';
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total);
    };
    xhr.upload.onload = () => onProgress?.(1);
    xhr.onerror = () => reject(new ApiError('NETWORK', `Upload failed: service unreachable at ${API_BASE || window.location.origin}`));
    xhr.onabort = () => reject(new ApiError('NETWORK', 'Upload aborted'));
    xhr.onload = () => {
      let parsed: unknown = null;
      try {
        parsed = xhr.responseText ? JSON.parse(xhr.responseText) : null;
      } catch {
        parsed = xhr.responseText;
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(parsed as T);
      else reject(toApiError(xhr.status, parsed, `HTTP ${xhr.status}`));
    };
    opts.signal?.addEventListener('abort', () => xhr.abort());
    xhr.send(form);
  });
}

const enc = encodeURIComponent;

/** Strip a locator fragment (#xywh=..., #stroke=...) to get the stable source id. */
export function baseSourceId(sourceId: string): string {
  const i = sourceId.indexOf('#');
  return i < 0 ? sourceId : sourceId.slice(0, i);
}

export interface AttemptUpload {
  kind: AttemptKind;
  file: Blob;
  fileName: string;
  raster?: Blob;
  video?: File;
}

const httpApi = {
  health: (o?: CallOptions) => request<HealthResponse>('GET', '/api/health', undefined, o),
  listCases: (o?: CallOptions) => request<CaseSummary[]>('GET', '/api/cases', undefined, o),
  getCase: (caseId: string, o?: CallOptions) => request<CaseView>('GET', `/api/cases/${enc(caseId)}`, undefined, o),
  uploadSource: (caseId: string, file: File, onProgress?: ProgressFn, o?: CallOptions) => {
    const form = new FormData();
    form.append('file', file, file.name);
    return upload<{ case_id: string }>(`/api/cases/${enc(caseId)}/sources`, form, onProgress, o);
  },
  buildCase: (caseId: string, sourceId?: string, o?: CallOptions) =>
    request<CaseView>('POST', `/api/cases/${enc(caseId)}/build`, sourceId ? { source_id: sourceId } : {}, o),
  queryCase: (caseId: string, question: string, o?: CallOptions) =>
    request<QueryAnswer>('POST', `/api/cases/${enc(caseId)}/query`, { question }, o),
  reviewCase: (caseId: string, action: ReviewAction, o?: CallOptions) =>
    request<CaseView>('POST', `/api/cases/${enc(caseId)}/review`, action, o),
  createSession: (caseId: string, learnerName: string, o?: CallOptions) =>
    request<SessionCreated>('POST', '/api/sessions', { case_id: caseId, learner_name: learnerName }, o),
  getSession: (sid: string, o?: CallOptions) => request<SessionView>('GET', `/api/sessions/${enc(sid)}`, undefined, o),
  submitAttempt: (sid: string, a: AttemptUpload, onProgress?: ProgressFn, o?: CallOptions) => {
    const form = new FormData();
    form.append('kind', a.kind);
    form.append('file', a.file, a.fileName);
    if (a.raster) form.append('raster', a.raster, 'trace.png');
    if (a.video) form.append('video', a.video, a.video.name);
    return upload<AttemptResult>(`/api/sessions/${enc(sid)}/attempts`, form, onProgress, o);
  },
  completeSession: (sid: string, o?: CallOptions) =>
    request<SessionResult>('POST', `/api/sessions/${enc(sid)}/complete`, undefined, o),
  /** URL for committed/cached source media (fragment stripped). */
  mediaUrl: (caseId: string, sourceId: string) => `${API_BASE}/api/media/${enc(caseId)}/${enc(baseSourceId(sourceId))}`,
  /** URL for a goal asset (e.g. an origami keyframe JPEG). */
  goalAssetUrl: (caseId: string, asset: string) => `${API_BASE}/api/media/${enc(caseId)}/goal/${enc(asset)}`,
};

export type Api = typeof httpApi;

export const api: Api = IS_MOCK ? mockApi : httpApi;
