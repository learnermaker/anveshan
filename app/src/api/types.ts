/**
 * Anveshan service API view types (docs/plans/service-api.md §3–§5).
 *
 * These are VIEW / transport types for the HTTP API. The eight shared contracts are
 * imported from ../types/contracts (downstream mirror of tracks/common/schemas/) and are
 * never re-declared here. Case-pack sidecars (GoalModel, CriterionMap, SourceRecord) mirror
 * tracks/common/casedata.py and are case data, not contracts.
 */

import type {
  EvidenceRef,
  Evaluation,
  Feedback,
  KnowledgePackage,
  LearnerAttempt,
  PracticeTask,
  ReviewStatus,
  RubricDefinition,
  TransmissionRecord,
  CriterionStatus,
} from '../types/contracts';
import type { CaseAccess } from './types-product';

export * from './types-product';

// ---------------------------------------------------------------------------
// Runtime / health
// ---------------------------------------------------------------------------

export type ServiceMode = 'live' | 'recorded';

export interface HealthResponse {
  ok: boolean;
  mode: ServiceMode | string;
  /** false on the public demo: ?mode= is ignored and the runtime panel is hidden */
  mode_override?: boolean;
  /** false on the public demo: reviewing the curated cases needs an invitation token */
  curated_review_open?: boolean;
  /** the browser may send its own Gemini key (X-Gemini-Api-Key) */
  own_key_supported?: boolean;
  server_key_configured?: boolean;
  /** the steward console exists on this server (an access code is configured, or it is open) */
  steward_enabled?: boolean;
  /** local development: the steward console needs no access code */
  steward_open?: boolean;
  /** private skills and uploads are deleted after this many hours (0 = kept) */
  data_ttl_hours?: number;
  models: {
    text_image: string;
    video_frames: string;
    vision_fast?: string | null;
    embedding?: string | null;
    audio_enabled: boolean;
  };
}

export type RuntimeClass = 'LIVE' | 'RECORDED_LIVE' | 'DETERMINISTIC';

// ---------------------------------------------------------------------------
// Case data (sidecars, casedata.py)
// ---------------------------------------------------------------------------

export type GoalModality = 'kolam_image' | 'origami_video' | 'tabla_audio' | 'universal';
export type RuntimeLabel = 'INTERNET_REFERENCE' | 'OWNED_CONSENTED' | 'SYNTHETIC' | 'UPLOAD';

export interface CaseSummary {
  case_id: string;
  title: string;
  modality: GoalModality | string;
  hero: boolean;
  runtime_label: RuntimeLabel | string;
  review_status: ReviewStatus | string;
  derived_from?: string | null;
  /** True for cases created via the universal-pipeline composer. */
  composed?: boolean;
  /** Structure tags for composed cases (e.g. ["final_state", "procedure"]). */
  structures?: string[];
  /** library and ownership state for the current visitor (K9) */
  access?: CaseAccess;
}

export interface SourceRecord {
  source_id: string;
  role: string;
  mime_type: string;
  sha256: string;
  bytes: number;
  path?: string | null;
  url?: string | null;
  duration_sec?: number | null;
  dimensions?: number[] | null;
  window_sec?: number[] | null;
  creator: string;
  license: string;
  attribution: string;
  access_level?: string;
  runtime_label: RuntimeLabel | string;
  used_by_system?: boolean;
  notes?: string | null;
}

export interface CriterionMapEntry {
  order_index: number;
  source_claim_ids: string[];
  reference_evidence_ids: string[];
  why_it_matters: string;
  drill_hint: string;
}

export interface CriterionMap {
  rubric_id: string;
  package_id: string;
  criteria: Record<string, CriterionMapEntry>;
}

// --- goal ui_view per modality (small JSON produced by tracks/common/goals/<m>.py ui_view) ---

export interface KolamDot {
  id?: string;
  x: number;
  y: number;
  r?: number;
  relation?: 'on_line' | 'enclosed' | string;
}

export interface KolamCurveStage {
  id: string;
  start: number;
  end: number;
}

/** Real-service curve shape: each curve is an object with id, closed, points, stages. */
export interface KolamCurveObj {
  id: string;
  closed: boolean;
  /** [x, y] pairs in goal-image pixels */
  points: number[][];
  stages: KolamCurveStage[];
}

export interface KolamUiView {
  canvas: { width: number; height: number };
  dots: KolamDot[];
  /** Real service: array of KolamCurveObj; legacy mock: number[][][] for backward compat. */
  curves: KolamCurveObj[] | number[][][];
  stroke_width?: number;
  tau?: number;
  /** Real service: rotation_order at top level. */
  rotation_order?: number;
  curve_count?: number;
  kind?: string;
  /** Legacy mock: symmetry object. Real service uses rotation_order at top level. */
  symmetry?: { rotational_order?: number | null; mirror_axes?: number[]; center?: number[] };
  target_source_id?: string;
}

export interface OrigamiState {
  index: number;
  name: string;
  properties?: string[];
  start_sec: number;
  end_sec: number;
  keyframe_sec?: number;
  /** asset name under GET /api/media/{case_id}/goal/{asset} */
  keyframe_asset?: string;
  label?: string;
}

export interface OrigamiUiView {
  states: OrigamiState[];
  /** Real service: 'window'. Legacy mock: 'window_sec'. Both kept. */
  window?: number[];
  window_sec?: number[];
  source_id?: string;
  kind?: string;
  final_state_index?: number;
  key_state_index?: number | null;
}

export interface TablaBeat {
  /** Real service field name. */
  i: number;
  /** Real service field name (seconds from window start). */
  t: number;
  bass: boolean;
  strength?: number;
  /** Legacy mock aliases — kept for backward compat during transition. */
  index?: number;
  time_sec?: number;
}

export interface TablaUiView {
  beats: TablaBeat[];
  /** Real service: stroke_pulse_sec. Legacy mock: period_sec. */
  stroke_pulse_sec?: number;
  period_sec?: number;
  tempo_bpm?: number;
  /** Real service: cycle_length_pulses + cycle_length_beats. Legacy mock: cycle_length. */
  cycle_length_pulses?: number;
  cycle_length_beats?: number;
  cycle_length?: number;
  beat_pulses?: number;
  duration_sec?: number;
  window_sec?: number[];
  strokes_per_min?: number;
  strokes?: Array<{ i: number; t: number; bass: boolean; strength: number }>;
  bols?: unknown;
  bols_status?: string;
  tolerances?: { timing_ms: number; tempo_pct: number };
  /** Legacy mock: source_id. Real service uses source_ids from goal. */
  source_id?: string;
  modality?: string;
}

export type GoalUiView = KolamUiView | OrigamiUiView | TablaUiView | UniversalUiView;

export interface UniversalUiView {
  structures: string[];
  steps?: Array<{
    step_id: string;
    name: string;
    state_after: string;
    critical?: boolean;
    source_established?: boolean;
    keyframe_asset?: string | null;
    start_sec?: number | null;
    end_sec?: number | null;
  }>;
  goal_state?: Array<{
    prop_id: string;
    statement: string;
    region?: number[] | null;
    keep?: boolean;
    certainty?: string;
  }>;
  checks?: Array<{
    check_id: string;
    name: string;
    metric_id?: string;
    method: string;
    enabled?: boolean;
    weight?: number;
    required?: boolean;
    observable_indicator?: string;
  }>;
  reference_assets?: string[];
  transcript?: string | null;
}

export interface GoalView {
  case_id: string;
  version: number;
  modality: GoalModality;
  source_ids: string[];
  package_id: string;
  built_with?: Record<string, unknown>;
  warnings?: string[];
  ui_view: GoalUiView;
}

/** GET /api/cases/{case_id} → CaseHandoff.to_view() */
export interface CaseView {
  case_id: string;
  title: string;
  modality: GoalModality;
  hero: boolean;
  runtime_label: RuntimeLabel | string;
  review_status: ReviewStatus | string;
  derived_from?: string | null;
  warnings: string[];
  sources: SourceRecord[];
  goal: GoalView;
  package: KnowledgePackage;
  rubric: RubricDefinition;
  task: PracticeTask;
  criterion_map?: CriterionMap | null;
  /** Composer: full CaseProfile for universal cases (null for hero cases). */
  profile?: CaseProfile | null;
  /** Real service extra fields (additive; ignored by UI if absent). */
  manifest?: Record<string, unknown>;
  observers?: Record<string, unknown>;
  versions?: Record<string, number>;
  lesson?: Record<string, unknown>;
  /** library and ownership state for the current visitor (K9) */
  access?: CaseAccess;
}

// ---------------------------------------------------------------------------
// Query / review
// ---------------------------------------------------------------------------

export interface QueryAnswer {
  answer: string;
  cited_claim_ids: string[];
  evidence: EvidenceRef[];
  sufficient: boolean;
  run?: Record<string, unknown>;
}

export type ReviewActionKind = 'approve' | 'revise_claim' | 'reject_claim' | 'reject_package';

export interface ReviewAction {
  action: ReviewActionKind;
  reviewer: string;
  note: string;
  claim_id?: string;
  new_statement?: string;
}

// ---------------------------------------------------------------------------
// Sessions / attempts (Track B)
// ---------------------------------------------------------------------------

export type AttemptKind = 'trace' | 'image' | 'audio' | 'video';
export type PositionKind = 'time' | 'stroke' | 'beat' | 'frame';

export interface DivergenceEvent {
  metric: string;
  kind: string;
  position: number;
  position_kind: PositionKind;
  evidence: EvidenceRef;
  detail: string;
  severity: 'material' | 'minor';
}

export interface TablaAlignmentRow {
  /** Real service fields (from track_b evaluator). */
  goal?: number | null;
  learner?: number | null;
  goal_t?: number | null;
  learner_t?: number | null;
  dev_ms?: number | null;
  bass_goal?: boolean | null;
  bass_learner?: boolean | null;
  bass_ok?: boolean | null;
  on_time?: boolean | null;
  /** Legacy mock field aliases. */
  goal_index?: number | null;
  goal_time_sec?: number | null;
  learner_time_sec?: number | null;
  deviation_ms?: number | null;
  status?: 'ok' | 'late' | 'early' | 'missing' | 'extra' | string;
  bass_expected?: boolean | null;
  bass_played?: boolean | null;
}

export interface OrigamiFrameLabel {
  t: number;
  /** Real service: raw label per frame. */
  raw?: number | 'transition' | 'off_path' | 'unclear' | string;
  /** Real service: filtered label per frame. */
  filtered?: number | 'transition' | 'off_path' | 'unclear' | string;
  /** Legacy mock field. */
  state?: number | 'transition' | 'off_path' | 'unclear' | string;
  note?: string;
}

/** Derived per-modality data for the UI. All keys optional; the UI degrades gracefully. */
export interface TrajectoryArtifacts {
  /** tabla: DTW alignment rows */
  alignment?: TablaAlignmentRow[];
  /** origami: filtered per-frame state labels */
  frame_labels?: OrigamiFrameLabel[];
  /** kolam: stroke indices flagged off-path (mock only; real uses per_stroke) */
  off_path_strokes?: number[];
  /** kolam real service: per-stroke detail */
  per_stroke?: unknown[];
  stage_completion_order?: unknown;
  tau_px?: number;
  /** kolam image upload: registration result */
  registration?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface Trajectory {
  curve: number[][]; // [[position, progress 0..1]]
  curve_kind: PositionKind | string;
  events: DivergenceEvent[];
  process_observable: boolean;
  artifacts: TrajectoryArtifacts;
  final_state: Record<string, unknown>;
}

export interface MetricView {
  value: number | null;
  finding: string;
  uncertain_reason?: string | null;
}

export interface FirstDivergence {
  criterion_id: string;
  criterion_name: string;
  status: CriterionStatus;
  position: number | null;
  position_kind: PositionKind | string;
  learner_evidence: EvidenceRef | null;
  expert_evidence: EvidenceRef | null;
  observed_finding: string;
  why_it_matters: string;
  source_claim_ids: string[];
  drill_hint: string;
}

/** How the feedback advice was worded: by the AI (guarded) or the deterministic template. */
export interface CoachingView {
  status: 'ai_worded' | 'template' | string;
  reason?: string | null;
  model_id?: string | null;
  run_key?: string | null;
  /** the template advice per criterion, kept when the AI wording was used */
  template_advice?: Record<string, string>;
}

/** Unscored drill. Never carries a score. */
export interface DrillView {
  criterion_id?: string;
  title?: string;
  /** service field (track_b/drill.py) */
  instruction?: string;
  /** legacy mock field */
  instructions?: string;
  drill_hint?: string;
  /** what success looks like (the criterion's observable indicator) */
  success_hint?: string;
  kind?: 'practice' | 're_record' | string;
  source_claim_ids?: string[];
  reference_evidence?: EvidenceRef | null;
  [key: string]: unknown;
}

export interface AttemptResult {
  attempt: LearnerAttempt;
  evaluation: Evaluation;
  trajectory: Trajectory;
  metrics: Record<string, MetricView>;
  first_divergence: FirstDivergence | null;
  feedback: Feedback | null;
  drill: DrillView | null;
  /** AI wording of the advice (never scores); absent on older results */
  coaching?: CoachingView | null;
  runtime_class: RuntimeClass;
  warnings: string[];
  run_keys: string[];
}

export interface SessionCreated {
  session_id: string;
  state: string;
}

export interface SessionView {
  session_id: string;
  case_id?: string;
  learner_name?: string;
  state: string;
  attempts: AttemptResult[];
}

export interface TargetedChange {
  criterion_id?: string | null;
  /** Real service field names. */
  before?: CriterionStatus | string | null;
  after?: CriterionStatus | string | null;
  improved?: boolean;
  changed?: boolean;
  /** Legacy mock field names. */
  baseline_status?: CriterionStatus | null;
  retry_status?: CriterionStatus | null;
  kind?: string;
  [key: string]: unknown;
}

export interface SessionResult {
  /** the 9 canonical bundle keys (case_id, knowledge_package, rubric, practice_task, attempts, evaluations, feedback, transmission_record ...) */
  bundle: Record<string, unknown>;
  transmission_record: TransmissionRecord;
  comparison: {
    transitions: Record<string, string>;
    targeted_change: TargetedChange;
    skill_gain_excluding_observability: number;
    curves: { baseline: number[][]; retry: number[][] };
  };
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export type ErrorCategory =
  | 'INVALID_INPUT'
  | 'MISSING_EVIDENCE'
  | 'REPLAY_MISMATCH'
  | 'HUMAN_REVIEW_REQUIRED'
  | 'MODEL_FAILURE'
  | 'MODEL_TIMEOUT'
  | 'CONTRACT_VIOLATION'
  | 'NETWORK'
  | 'UNKNOWN';

export interface ApiErrorBody {
  error: { category: ErrorCategory | string; message: string; details?: unknown };
}

// ---------------------------------------------------------------------------
// Composer: universal-pipeline types (tracks/common/perception.py,
// skill_model.py, profile.py) — case data, NOT the 8 frozen contracts.
// Field names mirror the Python models exactly.
// ---------------------------------------------------------------------------

export type Certainty = 'observed' | 'inferred' | 'unverified';

export interface Segment {
  segment_id: string;
  kind: 'time' | 'region' | 'whole';
  start_sec?: number | null;
  end_sec?: number | null;
  region?: number[] | null;
  keyframe_sec?: number | null;
  keyframe_asset?: string | null;
  stability?: number | null;
}

export type ObservationKind = 'state' | 'action' | 'object' | 'property' | 'event' | 'speech' | 'measurement' | 'quality';

export interface Observation {
  obs_id: string;
  segment_id: string;
  kind: ObservationKind;
  label: string;
  detail?: string | null;
  value?: number | null;
  unit?: string | null;
  certainty: Certainty;
  producer: string;
}

export interface ProbeFacts {
  modality: 'image' | 'video' | 'audio';
  mime_type: string;
  bytes: number;
  sha256: string;
  width?: number | null;
  height?: number | null;
  duration_sec?: number | null;
  has_audio?: boolean | null;
  metrics?: Record<string, number>;
  structures_available: string[];
  specialists_available?: string[];
  reasons?: Record<string, string>;
}

export interface IntakeResult {
  safety: Record<string, unknown>;
  teachable: 'yes' | 'no' | 'unclear';
  teachable_reason?: string;
  skill_kind?: string | null;
}

export interface TargetProperty {
  prop_id: string;
  statement: string;
  region?: number[] | null;
  evidence?: string[];
  certainty: Certainty;
  keep?: boolean;
}

export interface SkillStep {
  step_id: string;
  index: number;
  name: string;
  state_after: string;
  action?: string | null;
  start_sec?: number | null;
  end_sec?: number | null;
  keyframe_asset?: string | null;
  segment_id?: string | null;
  evidence?: string[];
  certainty: Certainty;
  source_established: boolean;
  critical?: boolean;
}

export interface SkillConstraint {
  constraint_id: string;
  statement: string;
  evidence?: string[];
  certainty: Certainty;
  keep?: boolean;
}

export interface SkillRelevance {
  expected_kinds: string[];
  min_similarity?: number;
  ambiguous_band?: number;
  reference_segment_ids?: string[];
}

export type CheckMethod = 'deterministic' | 'model_status' | 'specialist';

export interface SkillCheck {
  check_id: string;
  kind: string;
  name: string;
  observable_indicator: string;
  targets?: string[];
  metric_id: string;
  method: CheckMethod;
  params?: Record<string, unknown>;
  weight?: number;
  required?: boolean;
  process?: boolean;
  enabled?: boolean;
}

export interface SkillModel {
  schema_version?: '1.0';
  skill_title: string;
  summary: string;
  source_modality: 'image' | 'video' | 'audio';
  structures: string[];
  goal_state?: TargetProperty[];
  steps?: SkillStep[];
  order?: 'strict' | 'partial' | 'none';
  constraints?: SkillConstraint[];
  temporal?: Record<string, unknown> | null;
  utterance?: Record<string, unknown> | null;
  specialists?: Record<string, unknown>;
  relevance: SkillRelevance;
  checks: SkillCheck[];
  vocabulary?: Record<string, string>;
  warnings?: string[];
}

export interface CaseProfile {
  schema_version?: '2.0';
  case_id: string;
  title: string;
  skill_summary: string;
  domain: string;
  transmission_mode: 'forward' | 'goal-conditioned' | 'corrective';
  learner_input_kinds: string[];
  vocabulary?: Record<string, string>;
  goal_hint?: string | null;
  probe: ProbeFacts;
  intake: IntakeResult;
  skill_model: SkillModel;
  perception_file?: string | null;
  confirmed_by_user?: boolean;
  confirmed_at?: string | null;
  warnings?: string[];
}

export interface DraftView {
  draft_id: string;
  probe: ProbeFacts;
  intake: IntakeResult;
  proposal: CaseProfile | null;
  refused: boolean;
  refusal_message: string | null;
  warnings: string[];
  structure_labels: Record<string, string>;
  specialist_labels: Record<string, string>;
  perception: { segments: Segment[]; observations: Observation[] };
}

export interface CreateFromDraftEdits {
  title: string;
  skill_summary: string;
  domain: string;
  transmission_mode: string;
  learner_input_kinds: string[];
  goal_hint?: string | null;
  skill_model: SkillModel;
}
