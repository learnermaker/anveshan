/**
 * In-browser MOCK of the Anveshan service (VITE_API_BASE=mock).
 *
 * Every response is SYNTHETIC canned data (see ./mock/*.ts). The UI shows a "MOCK DATA" badge
 * whenever this module is active. It exists so the frontend can be built and demoed without
 * the backend; it is never evidence of a real evaluation.
 */

import type { Api, AttemptUpload, CallOptions, ComposerUploadOptions, ProgressFn } from './client';
import { ApiError } from './errors';
import type { AttemptResult, CaseSummary, CaseView, CreateFromDraftEdits, DraftView, HealthResponse, QueryAnswer, ReviewAction, SessionCreated, SessionResult, SessionView } from './types';
import { buildSessionResult } from './mock/builders';
import { evaluateKolamImage, evaluateKolamTrace, KOLAM_TARGET_SOURCE, KOLAM_TARGET_URL, kolamCaseView } from './mock/kolam';
import { evaluateOrigami, origamiCaseView, origamiGoalAsset } from './mock/origami';
import { evaluateTabla, TABLA_SOURCE, tablaAudioUrl, tablaCaseView } from './mock/tabla';
import {
  composedCaseView,
  composedMediaUrl,
  delay as composerDelay,
  evaluateUniversal,
  keyframeAssetUrl,
  loadDraft,
  refineDraft as composerRefineDraft,
  selectDraft,
  storeDraft,
} from './mock/composer';
import {
  MOCK_STEWARD_CODE,
  accessFor,
  mockConsent,
  mockDecide,
  mockInsights,
  mockOverview,
  mockQueue,
  mockStewardLibrary,
  mockSubmit,
  mockUsage,
  mockWithdraw,
  recordFor,
  requireMockSteward,
} from './mock/library';
import { getStewardToken } from './steward';
import type { ConsentRow, InsightsView, LibraryRecord, SampleAttempt, SampleSource, StewardDecision, StewardLibraryRow, StewardOverview, StewardQueueItem, SubmitBody, UsageView } from './types';
import { mockAnalyzeSampleFile, mockSampleSources, mockSamplesFor, mockSampleUpload } from './mock/samples';

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;

const cases = new Map<string, CaseView>([
  ['kolam', kolamCaseView()],
  // origami-crane is the universal-pipeline replacement for the experimental 'origami' case.
  // In mock mode we reuse origamiCaseView with the new case_id so the learner flow works.
  ['origami-crane', origamiCaseView('origami-crane')],
  ['tabla', tablaCaseView()],
]);
/** object URLs for uploaded derived-case sources: key = `${caseId}/${sourceId}` */
const uploadedMedia = new Map<string, string>();

interface MockSession {
  id: string;
  caseId: string;
  learner: string;
  attempts: AttemptResult[];
  state: string;
}
const sessions = new Map<string, MockSession>();
let seq = 0;

function getView(caseId: string): CaseView {
  const v = cases.get(caseId);
  if (!v) throw new ApiError('MISSING_EVIDENCE', `case ${caseId} not found`, 404);
  return v;
}

async function simulateUpload(onProgress?: ProgressFn, ms = 600): Promise<void> {
  const steps = 6;
  for (let i = 1; i <= steps; i++) {
    await delay(ms / steps);
    onProgress?.(i / steps);
  }
}

function baseOf(caseId: string): string {
  return caseId.split('~')[0];
}

async function sha12(file: Blob): Promise<string> {
  try {
    const buf = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
    return Array.from(new Uint8Array(buf).slice(0, 6))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  } catch {
    return Math.random().toString(16).slice(2, 14);
  }
}

export const mockApi: Api = {
  async health(_o?: CallOptions): Promise<HealthResponse> {
    await delay(120);
    return { ok: true, mode: 'recorded', own_key_supported: true, steward_enabled: true, steward_open: false, data_ttl_hours: 6, models: { text_image: 'gemma-4-26b-a4b-it (mock)', video_frames: 'gemma-4-26b-a4b-it (mock)', audio_enabled: false } };
  },

  async checkKey(_o?: CallOptions): Promise<{ ok: boolean; model: string }> {
    await delay(200);
    return { ok: true, model: 'gemini (mock)' };
  },

  async listCases(): Promise<CaseSummary[]> {
    await delay(150);
    return [...cases.values()].map((v) => ({
      case_id: v.case_id,
      title: v.title,
      modality: v.modality,
      hero: v.hero,
      runtime_label: v.runtime_label,
      review_status: v.review_status,
      derived_from: v.derived_from ?? null,
      composed: v.modality === 'universal',
      structures: v.modality === 'universal' ? ((v.goal.ui_view as { structures?: string[] }).structures ?? []) : undefined,
      access: accessFor(v),
    }));
  },

  async getCase(caseId: string): Promise<CaseView> {
    await delay(150);
    return { ...clone(getView(caseId)), access: accessFor(getView(caseId)) };
  },

  async uploadSource(caseId: string, file: File, onProgress?: ProgressFn): Promise<{ case_id: string }> {
    const base = baseOf(caseId);
    const baseView = getView(base);
    await simulateUpload(onProgress, 900);
    const id = `${base}~${await sha12(file)}`;
    const sourceId = `upload.${id.split('~')[1]}`;
    uploadedMedia.set(`${id}/${sourceId}`, URL.createObjectURL(file));
    const make = base === 'kolam' ? kolamCaseView : base === 'origami-crane' ? origamiCaseView : tablaCaseView;
    const v = make(id, {
      title: `${baseView.title.split(' — ')[0]} — your upload (${file.name})`,
      runtime_label: 'UPLOAD',
      review_status: 'pending',
      derived_from: base,
      hero: false,
      warnings: [
        'MOCK DATA: the mock does not analyse uploads; the goal model below is the base case’s canned model shown against your media.',
      ],
    });
    v.sources = [{ ...v.sources[0], source_id: sourceId, mime_type: file.type || 'application/octet-stream', bytes: file.size, sha256: 'mock', runtime_label: 'UPLOAD', creator: 'uploader', license: 'uploader-provided', attribution: file.name, path: null, url: null }];
    v.goal.source_ids = [sourceId];
    if (base === 'kolam') (v.goal.ui_view as { target_source_id?: string }).target_source_id = sourceId;
    else (v.goal.ui_view as { source_id?: string }).source_id = sourceId;
    v.goal.version = 0;
    cases.set(id, v);
    return { case_id: id };
  },

  async buildCase(caseId: string): Promise<CaseView> {
    const v = getView(caseId);
    await delay(1400);
    v.goal.version += 1;
    v.review_status = 'pending';
    if (v.package.expert_review) v.package.expert_review.status = 'pending';
    return clone(v);
  },

  async queryCase(caseId: string, question: string): Promise<QueryAnswer> {
    const v = getView(caseId);
    await delay(700);
    const words = question.toLowerCase().split(/\W+/).filter((w) => w.length > 3);
    const hits = v.package.claims.filter((c) => c.evidence_refs.length && words.some((w) => c.statement.toLowerCase().includes(w)));
    if (!hits.length) {
      return { answer: 'INSUFFICIENT_EVIDENCE: no claim in the approved package supports an answer.', cited_claim_ids: [], evidence: [], sufficient: false, run: { mock: true } };
    }
    const top = hits.slice(0, 2);
    return {
      answer: top.map((c) => `${c.statement} [${c.claim_id}]`).join(' '),
      cited_claim_ids: top.map((c) => c.claim_id),
      evidence: top.flatMap((c) => c.evidence_refs),
      sufficient: true,
      run: { mock: true },
    };
  },

  async reviewCase(caseId: string, action: ReviewAction): Promise<CaseView> {
    const v = getView(caseId);
    await delay(300);
    const pkg = v.package;
    if (action.action === 'approve') v.review_status = 'approved';
    if (action.action === 'reject_package') v.review_status = 'rejected';
    if (action.action === 'revise_claim' && action.claim_id && action.new_statement) {
      const c = pkg.claims.find((x) => x.claim_id === action.claim_id);
      if (c) c.statement = action.new_statement;
      v.review_status = 'revised';
    }
    if (action.action === 'reject_claim' && action.claim_id) {
      pkg.claims = pkg.claims.filter((x) => x.claim_id !== action.claim_id);
      v.review_status = 'revised';
    }
    pkg.expert_review = { reviewer_name: action.reviewer, status: v.review_status as 'approved', reviewed_at: new Date().toISOString(), notes: action.note };
    return clone(v);
  },

  async createSession(caseId: string, learnerName: string): Promise<SessionCreated> {
    getView(caseId);
    await delay(200);
    const id = `mock-${Date.now().toString(36)}-${++seq}`;
    sessions.set(id, { id, caseId, learner: learnerName, attempts: [], state: 'awaiting_baseline' });
    return { session_id: id, state: 'awaiting_baseline' };
  },

  async getSession(sid: string): Promise<SessionView> {
    const s = sessions.get(sid);
    if (!s) throw new ApiError('MISSING_EVIDENCE', `session ${sid} not found`, 404);
    return { session_id: s.id, case_id: s.caseId, learner_name: s.learner, state: s.state, attempts: clone(s.attempts) };
  },

  async submitAttempt(sid: string, a: AttemptUpload, onProgress?: ProgressFn): Promise<AttemptResult> {
    const s = sessions.get(sid);
    if (!s) throw new ApiError('MISSING_EVIDENCE', `session ${sid} not found`, 404);
    if (s.attempts.length >= 2) throw new ApiError('INVALID_INPUT', 'baseline and retry already submitted; complete the session', 400);
    const v = getView(s.caseId);
    const base = baseOf(s.caseId);
    const allowed: Record<string, string[]> = { kolam: ['trace', 'image'], 'origami-crane': ['video'], tabla: ['audio'] };
    if (v.modality === 'universal') {
      const profile = v.profile;
      const allowedKinds = profile?.learner_input_kinds ?? ['image', 'audio', 'video', 'trace'];
      if (!allowedKinds.includes(a.kind)) throw new ApiError('INVALID_INPUT', `kind ${a.kind} not accepted for this universal skill`, 400);
      await simulateUpload(onProgress, 800);
      const n = s.attempts.length + 1;
      await delay(1500);
      const result = evaluateUniversal(v, sid, s.learner, n, a.kind);
      s.attempts.push(result);
      s.state = n === 1 ? 'awaiting_retry' : 'awaiting_complete';
      return clone(result);
    }
    if (!allowed[base]?.includes(a.kind)) throw new ApiError('INVALID_INPUT', `kind ${a.kind} not accepted for ${base}`, 400);
    await simulateUpload(onProgress, Math.min(1500, 300 + a.file.size / 20000));
    const n = s.attempts.length + 1;
    let result: AttemptResult;
    if (base === 'kolam' && a.kind === 'trace') {
      await delay(600);
      result = evaluateKolamTrace(v, sid, s.learner, n, await a.file.text());
    } else if (base === 'kolam') {
      await delay(1500);
      result = evaluateKolamImage(v, sid, s.learner, n);
    } else if (base === 'origami-crane') {
      await delay(3000);
      result = evaluateOrigami(v, sid, s.learner, n);
    } else {
      await delay(1200);
      result = evaluateTabla(v, sid, s.learner, n, Boolean(a.video));
    }
    s.attempts.push(result);
    s.state = n === 1 ? 'awaiting_retry' : 'awaiting_complete';
    return clone(result);
  },

  async completeSession(sid: string): Promise<SessionResult> {
    const s = sessions.get(sid);
    if (!s) throw new ApiError('MISSING_EVIDENCE', `session ${sid} not found`, 404);
    if (s.attempts.length < 2) throw new ApiError('INVALID_INPUT', 'a baseline and a retry are required', 400);
    await delay(400);
    s.state = 'complete';
    return buildSessionResult(getView(s.caseId), sid, s.attempts[0], s.attempts[s.attempts.length - 1]);
  },

  mediaUrl(caseId: string, sourceId: string): string {
    const sid = sourceId.split('#')[0];
    const up = uploadedMedia.get(`${caseId}/${sid}`);
    if (up) return up;
    if (sid === KOLAM_TARGET_SOURCE) return KOLAM_TARGET_URL;
    if (sid === TABLA_SOURCE) return tablaAudioUrl();
    const composed = composedMediaUrl(caseId, sid);
    if (composed) return composed;
    return ''; // origami expert video is not bundled in mock mode
  },

  goalAssetUrl(caseId: string, asset: string): string {
    if (baseOf(caseId) === 'origami-crane') return origamiGoalAsset(asset);
    // Universal composed cases use synthetic keyframe SVGs
    const v = cases.get(caseId);
    if (v?.modality === 'universal') return keyframeAssetUrl(caseId, asset);
    return '';
  },

  // ---- Composer (K8) ----

  async analyzeSource(file: File, opts: ComposerUploadOptions, onProgress?: ProgressFn): Promise<DraftView> {
    // Simulate upload progress + processing
    await simulateUpload(onProgress, 1000);
    await composerDelay(3000); // 4 s total (spec: "usually 10-40 s")
    const draft = selectDraft(file, opts.title ?? '');
    const objectUrl = URL.createObjectURL(file);
    storeDraft(draft, objectUrl);
    return clone(draft);
  },

  async getDraft(draftId: string): Promise<DraftView> {
    await delay(100);
    const d = loadDraft(draftId);
    if (!d) throw new ApiError('MISSING_EVIDENCE', `draft ${draftId} not found`, 404);
    return clone(d);
  },

  async refineDraft(draftId: string, body: { title: string; description: string }): Promise<DraftView> {
    await composerDelay(2000);
    const existing = loadDraft(draftId);
    if (!existing) throw new ApiError('MISSING_EVIDENCE', `draft ${draftId} not found`, 404);
    const refined = composerRefineDraft(existing, body.title, body.description);
    storeDraft(refined, null);
    return clone(refined);
  },

  async createFromDraft(draftId: string, edits: CreateFromDraftEdits): Promise<CaseView> {
    await composerDelay(3000);
    const draft = loadDraft(draftId);
    if (!draft) throw new ApiError('MISSING_EVIDENCE', `draft ${draftId} not found`, 404);
    if (draft.refused || !draft.proposal) throw new ApiError('INVALID_INPUT', 'draft is refused or has no proposal', 400);
    if (!edits.learner_input_kinds.length) throw new ApiError('INVALID_INPUT', 'at least one learner input kind is required', 400);
    if (!edits.skill_model.checks.some((c) => c.enabled !== false)) throw new ApiError('INVALID_INPUT', 'at least one check must be enabled', 400);
    // Build updated profile from edits
    const profile: import('./types').CaseProfile = {
      ...draft.proposal,
      title: edits.title,
      skill_summary: edits.skill_summary,
      domain: edits.domain,
      transmission_mode: edits.transmission_mode as 'forward' | 'goal-conditioned' | 'corrective',
      learner_input_kinds: edits.learner_input_kinds,
      goal_hint: edits.goal_hint ?? null,
      skill_model: edits.skill_model,
      confirmed_by_user: true,
      confirmed_at: new Date().toISOString(),
    };
    const view = composedCaseView(profile, null);
    cases.set(view.case_id, view);
    return clone(view);
  },

  // ---- K9: library, insights and steward console (SYNTHETIC mock state) ----
  async getLibraryRecord(caseId: string): Promise<LibraryRecord> {
    await delay(100);
    return clone(recordFor(getView(caseId)));
  },
  async submitToLibrary(caseId: string, body: SubmitBody): Promise<LibraryRecord> {
    await delay(400);
    return clone(mockSubmit(getView(caseId), body));
  },
  async withdrawFromLibrary(caseId: string): Promise<LibraryRecord> {
    await delay(300);
    return clone(mockWithdraw(getView(caseId)));
  },
  async getInsights(caseId: string): Promise<InsightsView> {
    await delay(200);
    return mockInsights(getView(caseId));
  },
  async stewardCheck(): Promise<{ ok: boolean }> {
    await delay(300);
    if (getStewardToken() !== MOCK_STEWARD_CODE) throw new ApiError('STEWARD_REQUIRED', 'That access code is not right.', 401);
    return { ok: true };
  },
  async stewardOverview(): Promise<StewardOverview> {
    await delay(200);
    return mockOverview([...cases.values()]);
  },
  async stewardQueue(): Promise<StewardQueueItem[]> {
    await delay(200);
    return mockQueue([...cases.values()]);
  },
  async stewardLibrary(): Promise<StewardLibraryRow[]> {
    await delay(200);
    return mockStewardLibrary([...cases.values()]);
  },
  async stewardDecide(caseId: string, d: StewardDecision): Promise<LibraryRecord> {
    await delay(300);
    return clone(mockDecide(getView(caseId), d));
  },
  async stewardConsent(): Promise<ConsentRow[]> {
    await delay(200);
    return mockConsent([...cases.values()]);
  },
  async stewardUsage(): Promise<UsageView> {
    await delay(200);
    return mockUsage();
  },
  async stewardConsentExport(): Promise<Blob> {
    const rows = mockConsent([...cases.values()]);
    return new Blob([JSON.stringify({ exported_at: new Date().toISOString(), synthetic_mock: true, skills: rows }, null, 2)], { type: 'application/json' });
  },
  async listSamples(caseId: string): Promise<SampleAttempt[]> {
    await delay(120);
    return mockSamplesFor(getView(caseId));
  },
  async submitSampleAttempt(sid: string, sampleId: string): Promise<AttemptResult> {
    const s = sessions.get(sid);
    if (!s) throw new ApiError('MISSING_EVIDENCE', `session ${sid} not found`, 404);
    return mockApi.submitAttempt(sid, mockSampleUpload(getView(s.caseId), sampleId));
  },
  async listSampleSources(): Promise<SampleSource[]> {
    await delay(120);
    return mockSampleSources();
  },
  async analyzeSampleSource(sampleId: string): Promise<DraftView> {
    return mockApi.analyzeSource(mockAnalyzeSampleFile(sampleId), { rightsConfirmed: true });
  },
  async stewardReviewExport(caseId: string): Promise<Blob> {
    requireMockSteward();
    const v = getView(caseId);
    return new Blob([JSON.stringify({ case_id: caseId, synthetic_mock: true, review_status: v.review_status, knowledge_package: v.package }, null, 2)], { type: 'application/json' });
  },
};
