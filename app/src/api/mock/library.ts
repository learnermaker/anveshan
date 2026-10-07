/**
 * MOCK library, insights and steward console (VITE_API_BASE=mock). SYNTHETIC canned data only.
 *
 * Mirrors the service rules in docs/kiro/specs/K9-P1-BACKEND.md §3 closely enough for UI work:
 * curated cases are published; composed cases start private and belong to this browser; the mock
 * steward access code is "steward" (mock mode only, never on a real server).
 */

import { ApiError } from '../errors';
import { getStewardToken } from '../steward';
import type { CaseView } from '../types';
import type {
  CaseAccess,
  ConsentRow,
  InsightsView,
  LibraryRecord,
  LibraryStatus,
  StewardDecision,
  StewardLibraryRow,
  StewardOverview,
  StewardQueueItem,
  SubmitBody,
  UsageView,
} from '../types-product';

export const MOCK_STEWARD_CODE = 'steward';
const STARTED = new Date().toISOString();
const records = new Map<string, LibraryRecord>();

const now = () => new Date().toISOString();
const isCurated = (v: CaseView) => !v.case_id.includes('~');
const checked = (v: CaseView) => v.review_status === 'approved' || v.review_status === 'revised';

export function isMockSteward(): boolean {
  return getStewardToken() === MOCK_STEWARD_CODE;
}

function primaryAttribution(v: CaseView): { credit: string | null; licence: string | null } {
  const s = v.sources.find((x) => x.used_by_system !== false && x.role !== 'held_out_reference') ?? v.sources[0];
  return { credit: s?.attribution ?? null, licence: s?.license ?? null };
}

export function recordFor(v: CaseView): LibraryRecord {
  const existing = records.get(v.case_id);
  if (existing) return existing;
  const curated = isCurated(v);
  const { credit, licence } = primaryAttribution(v);
  const rec: LibraryRecord = {
    case_id: v.case_id,
    status: curated ? 'published' : 'private',
    collection: curated ? 'curated' : 'community',
    credit_name: curated ? credit : null,
    licence: curated ? licence : null,
    consent_scope: 'public_practice',
    rights_confirmed: !curated,
    rights_confirmed_at: curated ? null : now(),
    people_visible: false,
    people_consented: false,
    submitted_at: null,
    decided_at: null,
    steward_note: null,
    history: curated ? [] : [{ at: now(), actor: 'creator', action: 'created', note: null }],
  };
  records.set(v.case_id, rec);
  return rec;
}

function blockers(v: CaseView, rec: LibraryRecord): string[] {
  const out: string[] = [];
  if (!checked(v)) out.push('Check what the AI understood and confirm the steps first.');
  if (!['private', 'returned'].includes(rec.status)) out.push('This skill has already been sent to the library.');
  return out;
}

export function accessFor(v: CaseView): CaseAccess {
  const rec = recordFor(v);
  const owner = !isCurated(v);
  const steward = isMockSteward();
  const b = owner ? blockers(v, rec) : ['Only the creator can publish this skill.'];
  return {
    owner,
    steward,
    library_status: rec.status,
    collection: rec.collection,
    credit_name: rec.credit_name,
    licence: rec.licence,
    can_edit: owner || steward,
    can_submit: owner && b.length === 0,
    submit_blockers: owner ? b : [],
    steward_note: rec.steward_note,
  };
}

function push(rec: LibraryRecord, actor: 'creator' | 'steward' | 'system', action: string, note: string | null = null) {
  rec.history = [...rec.history, { at: now(), actor, action, note }].slice(-50);
}

function setStatus(rec: LibraryRecord, status: LibraryStatus) {
  rec.status = status;
}

export function mockSubmit(v: CaseView, body: SubmitBody): LibraryRecord {
  const rec = recordFor(v);
  if (isCurated(v)) throw new ApiError('INVALID_INPUT', 'Only the creator can publish this skill.', 403);
  const b = blockers(v, rec);
  if (!body.credit_name.trim()) b.push('Enter the name to credit.');
  if (!body.rights_confirmed) b.push('Confirm that you created this or have the right to share it.');
  if (body.people_visible && !body.people_consented) b.push('Confirm that the people shown agreed to it being shared.');
  if (b.length) throw new ApiError('INVALID_INPUT', b.join(' '), 400, { blockers: b });
  Object.assign(rec, {
    credit_name: body.credit_name.trim(),
    licence: body.licence,
    consent_scope: body.consent_scope,
    rights_confirmed: true,
    rights_confirmed_at: now(),
    people_visible: body.people_visible,
    people_consented: body.people_consented,
    submitted_at: now(),
    steward_note: null,
  });
  setStatus(rec, 'submitted');
  push(rec, 'creator', 'submitted', body.note?.trim() || null);
  return rec;
}

export function mockWithdraw(v: CaseView): LibraryRecord {
  const rec = recordFor(v);
  if (isCurated(v)) throw new ApiError('INVALID_INPUT', 'Only the creator can change this skill.', 403);
  if (!['submitted', 'returned', 'published', 'rejected'].includes(rec.status)) throw new ApiError('INVALID_INPUT', 'This skill is already private.', 409);
  setStatus(rec, 'private');
  push(rec, 'creator', 'made_private');
  return rec;
}

export function requireMockSteward(): void {
  if (!isMockSteward()) throw new ApiError('STEWARD_REQUIRED', 'Enter the steward access code to use the steward console.', 401);
}

export function mockDecide(v: CaseView, d: StewardDecision): LibraryRecord {
  requireMockSteward();
  const rec = recordFor(v);
  const note = d.note?.trim() || null;
  if (['return', 'reject', 'unlist'].includes(d.decision) && !note) throw new ApiError('INVALID_INPUT', 'Add a short note explaining the decision.', 400);
  const allowed: Record<string, LibraryStatus[]> = {
    publish: ['submitted'],
    return: ['submitted'],
    reject: ['submitted'],
    unlist: ['published'],
    republish: ['unlisted'],
  };
  if (!allowed[d.decision]?.includes(rec.status)) throw new ApiError('INVALID_INPUT', `Cannot ${d.decision} a skill that is ${rec.status}.`, 409);
  const next: Record<string, LibraryStatus> = { publish: 'published', return: 'returned', reject: 'rejected', unlist: 'unlisted', republish: 'published' };
  setStatus(rec, next[d.decision]);
  rec.decided_at = now();
  rec.steward_note = note;
  push(rec, 'steward', d.decision, note);
  return rec;
}

/** Canned SYNTHETIC insights so the UI can be built without a backend. */
export function mockInsights(v: CaseView): InsightsView {
  const crit = v.rubric.criteria;
  if (!isCurated(v) || crit.length === 0) {
    return {
      case_id: v.case_id,
      since: null,
      learners: 0,
      attempts: 0,
      completed: 0,
      baseline: { count: 0, pass_rate: null, avg_pct: null },
      retry: { count: 0, pass_rate: null, avg_pct: null },
      first_wrong: [],
      hardest: [],
      feedback_helped: { sessions: 0, improved: 0, rate: null },
      suggestions: [],
      enough_data: false,
    };
  }
  const a = crit[0];
  const b = crit[Math.min(1, crit.length - 1)];
  return {
    case_id: v.case_id,
    since: STARTED,
    learners: 7,
    attempts: 12,
    completed: 5,
    baseline: { count: 7, pass_rate: 0.29, avg_pct: 0.58 },
    retry: { count: 5, pass_rate: 0.6, avg_pct: 0.74 },
    first_wrong: [
      { criterion_id: a.criterion_id, name: a.name, count: 3, share: 0.6 },
      { criterion_id: b.criterion_id, name: b.name, count: 2, share: 0.4 },
    ],
    hardest: [
      { criterion_id: a.criterion_id, name: a.name, miss_rate: 0.57, n: 7 },
      { criterion_id: b.criterion_id, name: b.name, miss_rate: 0.43, n: 7 },
    ],
    feedback_helped: { sessions: 5, improved: 3, rate: 0.6 },
    suggestions: [
      { criterion_id: a.criterion_id, rule: 'R1', text: `About 57% of learners miss “${a.name}” on their first try. Consider showing this step more slowly or describing it more clearly.` },
      { criterion_id: a.criterion_id, rule: 'R2', text: `Most learners first go wrong at “${a.name}”. Make sure the source shows this moment clearly.` },
    ],
    enough_data: true,
  };
}

export function mockOverview(views: CaseView[]): StewardOverview {
  requireMockSteward();
  const recs = views.map((v) => ({ v, r: recordFor(v) }));
  const waiting = recs.filter(({ r }) => r.status === 'submitted');
  const unchecked = recs.filter(({ v, r }) => r.collection === 'curated' && r.status === 'published' && !checked(v));
  const attention = [
    ...(waiting.length ? [{ kind: 'submissions_waiting' as const, text: `${waiting.length} shared skill${waiting.length > 1 ? 's are' : ' is'} waiting for review`, case_id: null, count: waiting.length }] : []),
    ...unchecked.map(({ v }) => ({ kind: 'curated_unchecked' as const, text: `“${v.title}” has not been checked by an expert yet`, case_id: v.case_id, count: 1 })),
  ];
  return {
    library_skills: recs.filter(({ r }) => r.status === 'published').length,
    waiting_review: waiting.length,
    learners_today: 7,
    attempts_today: 12,
    live_calls_today: 41,
    daily_budget: 2000,
    storage_bytes: 38 * 1024 * 1024,
    storage_cap_bytes: 600 * 1024 * 1024,
    attention,
    ephemeral: true,
  };
}

export function mockQueue(views: CaseView[]): StewardQueueItem[] {
  requireMockSteward();
  return views
    .map((v) => ({ v, r: recordFor(v) }))
    .filter(({ v, r }) => r.status === 'submitted' || (r.collection === 'curated' && r.status === 'published' && !checked(v)))
    .map(({ v, r }) => ({
      case_id: v.case_id,
      title: v.title,
      kind: r.status === 'submitted' ? ('submission' as const) : ('curated_unchecked' as const),
      modality: v.modality,
      library_status: r.status,
      review_status: v.review_status,
      credit_name: r.credit_name,
      submitted_at: r.submitted_at,
      steps: v.package.claims.length,
    }));
}

export function mockStewardLibrary(views: CaseView[]): StewardLibraryRow[] {
  requireMockSteward();
  return views
    .map((v) => ({ v, r: recordFor(v) }))
    .filter(({ r }) => r.status !== 'private')
    .map(({ v, r }) => {
      const ins = mockInsights(v);
      return {
        case_id: v.case_id,
        title: v.title,
        modality: v.modality,
        collection: r.collection,
        library_status: r.status,
        review_status: v.review_status,
        credit_name: r.credit_name,
        licence: r.licence,
        learners: ins.learners,
        attempts: ins.attempts,
        last_activity: ins.since,
      };
    });
}

export function mockConsent(views: CaseView[]): ConsentRow[] {
  requireMockSteward();
  return views
    .map((v) => ({ v, r: recordFor(v) }))
    .filter(({ r }) => r.status !== 'private')
    .map(({ v, r }) => ({
      case_id: v.case_id,
      title: v.title,
      collection: r.collection,
      library_status: r.status,
      credit_name: r.credit_name,
      licence: r.licence,
      consent_scope: r.consent_scope,
      rights_confirmed: r.rights_confirmed,
      rights_confirmed_at: r.rights_confirmed_at,
      people_visible: r.people_visible,
      people_consented: r.people_consented,
      sources: v.sources
        .filter((s) => s.used_by_system !== false)
        .map((s) => ({ source_id: s.source_id, attribution: s.attribution ?? '', license: s.license ?? '', url: s.url ?? null })),
      history: r.history,
    }));
}

export function mockUsage(): UsageView {
  requireMockSteward();
  return {
    started_at: STARTED,
    uptime_s: Math.round((Date.now() - Date.parse(STARTED)) / 1000),
    mode: 'recorded',
    live_calls_today: 41,
    daily_budget: 2000,
    own_key_calls: 6,
    cache_hits: 19,
    requests_by_class: { compose: 4, compose_step: 6, attempt: 12, query: 9, auth: 2 },
    rate_limited: { attempt: 1 },
    errors_by_category: { INVALID_INPUT: 2 },
    attempts_today: 12,
    compose_today: 4,
    storage_bytes: 38 * 1024 * 1024,
    storage_cap_bytes: 600 * 1024 * 1024,
    data_ttl_hours: 6,
  };
}
