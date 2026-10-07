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
import { getUserKey } from './userKey';
import { getStewardToken } from './steward';
import type {
  ApiErrorBody,
  AttemptKind,
  AttemptResult,
  CaseSummary,
  CaseView,
  ConsentRow,
  CreateFromDraftEdits,
  DraftView,
  HealthResponse,
  InsightsView,
  LibraryRecord,
  QueryAnswer,
  ReviewAction,
  SampleAttempt,
  SampleSource,
  SessionCreated,
  SessionResult,
  SessionView,
  StewardDecision,
  StewardLibraryRow,
  StewardOverview,
  StewardQueueItem,
  SubmitBody,
  UsageView,
} from './types';

export { ApiError };

export type ProgressFn = (fraction: number) => void;

export interface CallOptions {
  /** Override the mode for this call (otherwise the runtime panel selection). */
  mode?: 'live' | 'recorded';
  signal?: AbortSignal;
  /** Invitation token for expert review of curated cases on the public demo (X-Review-Token). */
  reviewToken?: string;
}

function withMode(path: string, mode?: 'live' | 'recorded'): string {
  const m = mode ?? (getRequestedMode() === 'default' ? undefined : getRequestedMode());
  if (!m) return `${API_BASE}${path}`;
  return `${API_BASE}${path}${path.includes('?') ? '&' : '?'}mode=${encodeURIComponent(m)}`;
}

/** The visitor's own Gemini key, if they set one (bring your own key). Header only, never a URL. */
function userKeyHeader(): Record<string, string> {
  const k = getUserKey();
  return k ? { 'X-Gemini-Api-Key': k } : {};
}

/** The steward access code for this tab, if the visitor signed in to the steward console. Header only. */
function stewardHeader(): Record<string, string> {
  const t = getStewardToken();
  return t ? { 'X-Steward-Token': t } : {};
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
      headers: {
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(opts.reviewToken ? { 'X-Review-Token': opts.reviewToken } : {}),
        ...userKeyHeader(),
        ...stewardHeader(),
      },
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
    for (const [k, v] of Object.entries({ ...userKeyHeader(), ...stewardHeader() })) xhr.setRequestHeader(k, v);
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

/** GET a file download (e.g. a JSON export) with the steward header; returns the body as a Blob. */
async function requestBlob(path: string): Promise<Blob> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { headers: { ...stewardHeader() } });
  } catch (e) {
    throw new ApiError('NETWORK', `Service unreachable at ${API_BASE || window.location.origin}: ${(e as Error).message}`);
  }
  if (!res.ok) {
    let parsed: unknown = null;
    try {
      parsed = await res.json();
    } catch {
      parsed = null;
    }
    throw toApiError(res.status, parsed, `HTTP ${res.status} ${res.statusText}`);
  }
  return res.blob();
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

export interface ComposerUploadOptions {
  title?: string;
  description?: string;
  rightsConfirmed: boolean;
}

const httpApi = {
  health: (o?: CallOptions) => request<HealthResponse>('GET', '/api/health', undefined, o),
  checkKey: (o?: CallOptions) => request<{ ok: boolean; model: string }>('POST', '/api/key/check', {}, o),
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
  /** POST /api/compose/analyze — multipart upload to start a draft. */
  analyzeSource: (file: File, opts: ComposerUploadOptions, onProgress?: ProgressFn, o?: CallOptions) => {
    const form = new FormData();
    form.append('file', file, file.name);
    if (opts.title) form.append('title', opts.title);
    if (opts.description) form.append('description', opts.description);
    form.append('rights_confirmed', opts.rightsConfirmed ? 'true' : 'false');
    return upload<DraftView>('/api/compose/analyze', form, onProgress, o);
  },
  /** GET /api/compose/{draft_id} */
  getDraft: (draftId: string, o?: CallOptions) =>
    request<DraftView>('GET', `/api/compose/${enc(draftId)}`, undefined, o),
  /** POST /api/compose/{draft_id}/refine */
  refineDraft: (draftId: string, body: { title: string; description: string }, o?: CallOptions) =>
    request<DraftView>('POST', `/api/compose/${enc(draftId)}/refine`, body, o),
  /** POST /api/compose/{draft_id}/create */
  createFromDraft: (draftId: string, edits: CreateFromDraftEdits, o?: CallOptions) =>
    request<CaseView>('POST', `/api/compose/${enc(draftId)}/create`, edits, o),

  // ---- K9: library (creator) ----
  /** GET /api/library/{case_id} (owner or steward) */
  getLibraryRecord: (caseId: string, o?: CallOptions) => request<LibraryRecord>('GET', `/api/library/${enc(caseId)}`, undefined, o),
  /** POST /api/library/{case_id}/submit: send the visitor's own skill to the steward review queue */
  submitToLibrary: (caseId: string, body: SubmitBody, o?: CallOptions) => request<LibraryRecord>('POST', `/api/library/${enc(caseId)}/submit`, body, o),
  /** POST /api/library/{case_id}/withdraw: make the visitor's own skill private again */
  withdrawFromLibrary: (caseId: string, o?: CallOptions) => request<LibraryRecord>('POST', `/api/library/${enc(caseId)}/withdraw`, {}, o),
  /** GET /api/insights/{case_id} (owner or steward): aggregate, anonymous learner outcomes */
  getInsights: (caseId: string, o?: CallOptions) => request<InsightsView>('GET', `/api/insights/${enc(caseId)}`, undefined, o),

  // ---- K9: steward console (X-Steward-Token) ----
  stewardCheck: (o?: CallOptions) => request<{ ok: boolean }>('POST', '/api/steward/check', {}, o),
  stewardOverview: (o?: CallOptions) => request<StewardOverview>('GET', '/api/steward/overview', undefined, o),
  stewardQueue: (o?: CallOptions) => request<StewardQueueItem[]>('GET', '/api/steward/queue', undefined, o),
  stewardLibrary: (o?: CallOptions) => request<StewardLibraryRow[]>('GET', '/api/steward/library', undefined, o),
  stewardDecide: (caseId: string, d: StewardDecision, o?: CallOptions) => request<LibraryRecord>('POST', `/api/steward/library/${enc(caseId)}/decide`, d, o),
  stewardConsent: (o?: CallOptions) => request<ConsentRow[]>('GET', '/api/steward/consent', undefined, o),
  stewardUsage: (o?: CallOptions) => request<UsageView>('GET', '/api/steward/usage', undefined, o),
  /** JSON download of the consent and licence ledger */
  stewardConsentExport: () => requestBlob('/api/steward/consent/export'),
  /** JSON download of one skill's latest reviewed steps and review record (commit it with tools/apply_expert_review.py) */
  stewardReviewExport: (caseId: string) => requestBlob(`/api/steward/review-export/${enc(caseId)}`),

  // ---- K9: sample attempts and sample sources (WI-3.1) ----
  /** GET /api/cases/{case_id}/samples */
  listSamples: (caseId: string, o?: CallOptions) => request<SampleAttempt[]>('GET', `/api/cases/${enc(caseId)}/samples`, undefined, o),
  /** POST /api/sessions/{sid}/attempts/sample/{sample_id}: submit a ready-made sample as this try */
  submitSampleAttempt: (sid: string, sampleId: string, o?: CallOptions) => request<AttemptResult>('POST', `/api/sessions/${enc(sid)}/attempts/sample/${enc(sampleId)}`, {}, o),
  /** GET /api/compose/samples */
  listSampleSources: (o?: CallOptions) => request<SampleSource[]>('GET', '/api/compose/samples', undefined, o),
  /** POST /api/compose/sample/{sample_id}: start a draft from an example source */
  analyzeSampleSource: (sampleId: string, o?: CallOptions) => request<DraftView>('POST', `/api/compose/sample/${enc(sampleId)}`, {}, o),
};

export type Api = typeof httpApi;

export const api: Api = IS_MOCK ? mockApi : httpApi;
