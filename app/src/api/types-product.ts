/**
 * Product-role view types (K9): library, creator publishing, insights and the steward console.
 *
 * These are service VIEW types (docs/plans/service-api.md §7), not the eight shared contracts.
 * Field names mirror service/anveshan_service/{library,insights,metrics}.py exactly.
 */

/** Where a skill is in its library lifecycle. Curated skills are 'published' or 'unlisted'. */
export type LibraryStatus = 'private' | 'submitted' | 'published' | 'returned' | 'rejected' | 'unlisted';

/** curated = shipped with the app (Featured); community = shared by a creator. */
export type Collection = 'curated' | 'community';

export type LicenceId = 'CC-BY-4.0' | 'CC-BY-SA-4.0' | 'CC0-1.0' | 'PRACTICE-ONLY';

/** Only one consent scope exists in the demo: listed in the library, anyone may practise. */
export type ConsentScope = 'public_practice';

/** Added by the service to every case summary and case view (GET /api/cases, GET /api/cases/{id}). */
export interface CaseAccess {
  /** the current visitor created this skill */
  owner: boolean;
  /** the current request carries a valid steward access code (or the steward console is open) */
  steward: boolean;
  library_status: LibraryStatus;
  collection: Collection;
  /** name shown to learners as credit; null when unknown */
  credit_name: string | null;
  licence: string | null;
  /** owner or steward may correct steps */
  can_edit: boolean;
  /** owner may submit right now */
  can_submit: boolean;
  /** plain-language reasons why submitting is not possible yet (empty when can_submit) */
  submit_blockers: string[];
  /** the steward's note when a submission was sent back or rejected */
  steward_note: string | null;
}

export interface LibraryHistoryEntry {
  at: string;
  actor: 'creator' | 'steward' | 'system';
  action: string;
  note: string | null;
}

/** GET /api/library/{case_id} (owner or steward; others get 404). */
export interface LibraryRecord {
  case_id: string;
  status: LibraryStatus;
  collection: Collection;
  credit_name: string | null;
  licence: string | null;
  consent_scope: ConsentScope | string;
  rights_confirmed: boolean;
  rights_confirmed_at: string | null;
  people_visible: boolean;
  people_consented: boolean;
  submitted_at: string | null;
  decided_at: string | null;
  steward_note: string | null;
  history: LibraryHistoryEntry[];
}

/** POST /api/library/{case_id}/submit */
export interface SubmitBody {
  credit_name: string;
  licence: LicenceId;
  consent_scope: ConsentScope;
  rights_confirmed: boolean;
  people_visible: boolean;
  people_consented: boolean;
  note?: string;
}

export type StewardDecisionKind = 'publish' | 'return' | 'reject' | 'unlist' | 'republish';

/** POST /api/steward/library/{case_id}/decide (note required for return, reject, unlist) */
export interface StewardDecision {
  decision: StewardDecisionKind;
  note?: string;
}

// ---------------------------------------------------------------------------
// Insights (aggregate, anonymous: no names, no media)
// ---------------------------------------------------------------------------

export interface InsightsAttemptStats {
  count: number;
  /** share of attempts that met every required check, 0..1; null when count is 0 */
  pass_rate: number | null;
  /** mean score as a share of the maximum, 0..1; null when unknown */
  avg_pct: number | null;
}

export interface InsightsCriterionCount {
  criterion_id: string;
  name: string;
  count: number;
  /** count / number of first tries that went off track, 0..1 */
  share: number;
}

export interface InsightsHardest {
  criterion_id: string;
  name: string;
  /** share of first tries where this check was not met, 0..1 */
  miss_rate: number;
  n: number;
}

export interface InsightsSuggestion {
  criterion_id: string | null;
  text: string;
  rule: string;
}

/** GET /api/insights/{case_id} (owner or steward) */
export interface InsightsView {
  case_id: string;
  since: string | null;
  learners: number;
  attempts: number;
  completed: number;
  baseline: InsightsAttemptStats;
  retry: InsightsAttemptStats;
  first_wrong: InsightsCriterionCount[];
  hardest: InsightsHardest[];
  feedback_helped: { sessions: number; improved: number; rate: number | null };
  suggestions: InsightsSuggestion[];
  /** false when fewer than 3 learners: the UI says to treat numbers as anecdotes */
  enough_data: boolean;
}

// ---------------------------------------------------------------------------
// Steward console
// ---------------------------------------------------------------------------

export interface StewardAttentionItem {
  kind: 'submissions_waiting' | 'curated_unchecked' | 'budget_high' | 'storage_high';
  text: string;
  /** case to open, when the item is about one skill */
  case_id: string | null;
  count: number;
}

/** GET /api/steward/overview */
export interface StewardOverview {
  library_skills: number;
  waiting_review: number;
  learners_today: number;
  attempts_today: number;
  live_calls_today: number;
  /** 0 = no daily budget configured */
  daily_budget: number;
  storage_bytes: number;
  /** 0 = no cap configured */
  storage_cap_bytes: number;
  attention: StewardAttentionItem[];
  /** true on servers whose runtime data is temporary (always true for the demo) */
  ephemeral: boolean;
}

/** GET /api/steward/queue */
export interface StewardQueueItem {
  case_id: string;
  title: string;
  kind: 'submission' | 'curated_unchecked';
  modality: string;
  library_status: LibraryStatus;
  review_status: string;
  credit_name: string | null;
  submitted_at: string | null;
  steps: number;
}

/** GET /api/steward/library */
export interface StewardLibraryRow {
  case_id: string;
  title: string;
  modality: string;
  collection: Collection;
  library_status: LibraryStatus;
  review_status: string;
  credit_name: string | null;
  licence: string | null;
  learners: number;
  attempts: number;
  last_activity: string | null;
}

export interface ConsentSourceRow {
  source_id: string;
  attribution: string;
  license: string;
  url: string | null;
}

/** GET /api/steward/consent (and /export as a JSON download) */
export interface ConsentRow {
  case_id: string;
  title: string;
  collection: Collection;
  library_status: LibraryStatus;
  credit_name: string | null;
  licence: string | null;
  consent_scope: string;
  rights_confirmed: boolean;
  rights_confirmed_at: string | null;
  people_visible: boolean;
  people_consented: boolean;
  sources: ConsentSourceRow[];
  history: LibraryHistoryEntry[];
}

/** GET /api/steward/usage */
export interface UsageView {
  started_at: string;
  uptime_s: number;
  mode: string;
  live_calls_today: number;
  daily_budget: number;
  own_key_calls: number;
  cache_hits: number;
  requests_by_class: Record<string, number>;
  rate_limited: Record<string, number>;
  errors_by_category: Record<string, number>;
  attempts_today: number;
  compose_today: number;
  storage_bytes: number;
  storage_cap_bytes: number;
  data_ttl_hours: number;
}

// ---------------------------------------------------------------------------
// Sample attempts and sample sources (WI-3.1): try a skill without your own materials
// ---------------------------------------------------------------------------

export type SampleQuality = 'good' | 'flawed' | 'unrelated';

/** GET /api/cases/{case_id}/samples: ready-made attempts a visitor can submit as their own try */
export interface SampleAttempt {
  sample_id: string;
  /** e.g. "A careful attempt", "An attempt with a mistake", "Something unrelated" */
  label: string;
  quality: SampleQuality;
  /** 'trace' | 'image' | 'audio' | 'video' (AttemptKind) */
  attempt_kind: string;
  /** one sentence: what this sample shows and what to look for in the feedback */
  description: string;
  /** media preview URL, or null when there is nothing to preview (e.g. a trace) */
  preview_url: string | null;
  /** true when the sample was made for the demo (synthetic); shown to the visitor */
  synthetic: boolean;
  /** credit line for third-party media in the sample, if any */
  credit: string | null;
}

/** GET /api/compose/samples: example sources for "Share a skill you know" */
export interface SampleSource {
  sample_id: string;
  label: string;
  description: string;
  mime_type: string;
  preview_url: string;
  credit: string;
  licence: string;
}
