/**
 * MOCK DATA (SYNTHETIC) — Universal-pipeline Composer (K8 §4).
 *
 * Canned DraftView and CaseView responses selected by upload MIME type and file name.
 * Every response is labelled SYNTHETIC. No real model calls are made.
 */

import type {
  CaseProfile,
  CaseView,
  DraftView,
  IntakeResult,
  Observation,
  ProbeFacts,
  Segment,
  SkillCheck,
  SkillConstraint,
  SkillModel,
  SkillStep,
  TargetProperty,
} from '../types';
import { assembleResult, buildAttempt, buildEvaluation, evidence, type CriterionOutcome } from './builders';

const delay = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));
const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;

export const STRUCTURE_LABELS: Record<string, string> = {
  final_state: 'Reproduce a finished result (final state)',
  procedure: 'Follow a sequence of steps (procedure)',
  temporal_pattern: 'Reproduce a rhythm or timing pattern',
  utterance: 'Reproduce a spoken phrase',
};

export const SPECIALIST_LABELS: Record<string, string> = {
  line_art: 'Line-drawing geometry (precise coverage, stray lines, dots, continuity)',
  rhythm: 'Rhythm analysis (tempo, timing, bass and stroke types)',
  procedure_states: 'Procedure state tracking (ordered states with keyframes)',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function sha12(name: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < name.length; i++) {
    h ^= name.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, '0') + h.toString(16).padStart(8, '0').slice(0, 4);
}

function slugify(t: string): string {
  return t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 32) || 'skill';
}

/** Minimal SVG data-URL that looks like a keyframe (solid colour + label text). */
function syntheticKeyframe(label: string, bg = '#1e2235'): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="80" height="60" viewBox="0 0 80 60"><rect width="80" height="60" fill="${bg}"/><text x="40" y="34" text-anchor="middle" font-size="9" fill="#ccc" font-family="monospace">${label.slice(0, 12)}</text></svg>`;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
}

function makeIntake(teachable: 'yes' | 'no' | 'unclear', reason = '', skillKind: string | null = null): IntakeResult {
  return {
    safety: { decision: 'safe', categories: ['none'] },
    teachable,
    teachable_reason: reason,
    skill_kind: skillKind,
  };
}

function makeProbe(mime: string, bytes: number, extra: Partial<ProbeFacts> = {}): ProbeFacts {
  const modality = mime.startsWith('image/') ? 'image' : mime.startsWith('video/') ? 'video' : 'audio';
  return {
    modality,
    mime_type: mime,
    bytes,
    sha256: 'mock000000000000000000000000000000000000000000000000000000000000',
    structures_available: [],
    specialists_available: [],
    reasons: {},
    ...extra,
  };
}

function makeCheck(id: string, kind: string, name: string, indicator: string, method: SkillCheck['method'], targets: string[], weight = 2, required = false): SkillCheck {
  return {
    check_id: id,
    kind,
    name,
    observable_indicator: indicator,
    targets,
    metric_id: `u.${kind}.${targets[0] ?? 'all'}`,
    method,
    weight,
    required,
    enabled: true,
  };
}

// ---------------------------------------------------------------------------
// Scenario builders
// ---------------------------------------------------------------------------

function imageProposal(title: string): CaseProfile {
  const props: TargetProperty[] = [
    { prop_id: 'prop-01', statement: 'All outline strokes are continuous (INFERRED)', region: [10, 10, 40, 40], certainty: 'inferred', keep: true },
    { prop_id: 'prop-02', statement: 'No stray marks outside the design area (INFERRED)', region: [0, 0, 100, 100], certainty: 'inferred', keep: true },
    { prop_id: 'prop-03', statement: 'Symmetry along the vertical axis (INFERRED)', region: [45, 5, 10, 90], certainty: 'inferred', keep: true },
    { prop_id: 'prop-04', statement: 'Ink fraction between 5–25% of the canvas (OBSERVED)', region: null, certainty: 'observed', keep: true },
  ];
  const constraints: SkillConstraint[] = [
    { constraint_id: 'con-01', statement: 'Do not use a ruler or stencil (INFERRED)', certainty: 'inferred', keep: false },
  ];
  const checks: SkillCheck[] = [
    makeCheck('CHK-FS-SIM', 'final_similarity', 'Overall structural similarity', '≥ 0.72 cosine', 'specialist', ['prop-01'], 2, true),
    makeCheck('CHK-FS-P01', 'final_property', 'Continuous outline strokes', 'No gaps > 2 px (INFERRED)', 'model_status', ['prop-01'], 2),
    makeCheck('CHK-FS-P02', 'final_property', 'No stray marks', 'Stray-mark count ≤ 2 (INFERRED)', 'model_status', ['prop-02'], 1),
    makeCheck('CHK-FS-P03', 'final_property', 'Ink fraction in range', '5–25% of canvas (OBSERVED)', 'deterministic', ['prop-04'], 2, true),
    makeCheck('CHK-LA-COV', 'line_art', 'Coverage against the reference', '≥ 0.75 coverage', 'specialist', ['prop-01'], 3, true),
    makeCheck('CHK-LA-STR', 'line_art', 'Stray lines below threshold', '≤ 5 stray segments', 'specialist', ['prop-01'], 2),
    makeCheck('CHK-LA-CON', 'line_art', 'Continuous curves', 'No break > 4 px', 'specialist', ['prop-01'], 2),
  ];
  const model: SkillModel = {
    skill_title: title,
    summary: 'Reproduce the line-art design with matching coverage, continuity and layout (INFERRED from image analysis).',
    source_modality: 'image',
    structures: ['final_state'],
    goal_state: props,
    constraints,
    specialists: { line_art: { type: 'kolam', dots: [], curves: [] } },
    relevance: { expected_kinds: ['trace', 'image'], min_similarity: 0.72 },
    checks,
  };
  return {
    case_id: `${slugify(title)}~${sha12(title)}`,
    title,
    skill_summary: model.summary,
    domain: 'visual art',
    transmission_mode: 'goal-conditioned',
    learner_input_kinds: ['trace', 'image'],
    probe: makeProbe('image/jpeg', 250000, { width: 512, height: 512, structures_available: ['final_state'], specialists_available: ['line_art'], reasons: { final_state: 'image available', line_art: 'separation OK, ink fraction in range' } }),
    intake: makeIntake('yes', '', 'line-drawing / pattern art'),
    skill_model: model,
    warnings: ['AI-perceived elements are INFERRED and require expert review before use.'],
  };
}

function videoProposal(title: string): CaseProfile {
  const steps: SkillStep[] = [
    { step_id: 'step-01', index: 0, name: 'Fold base (INFERRED)', state_after: 'base folded', start_sec: 0, end_sec: 8, keyframe_asset: 'kf_step01.jpg', certainty: 'inferred', source_established: true, critical: false },
    { step_id: 'step-02', index: 1, name: 'Form petal shape (INFERRED)', state_after: 'petal formed', start_sec: 8, end_sec: 18, keyframe_asset: 'kf_step02.jpg', certainty: 'inferred', source_established: true, critical: true },
    { step_id: 'step-03', index: 2, name: 'Reverse-fold corners (INFERRED)', state_after: 'corners reversed', start_sec: 18, end_sec: 28, keyframe_asset: 'kf_step03.jpg', certainty: 'inferred', source_established: true, critical: false },
    { step_id: 'step-04', index: 3, name: 'Open centre (INFERRED)', state_after: 'centre open', start_sec: 28, end_sec: 38, keyframe_asset: 'kf_step04.jpg', certainty: 'inferred', source_established: true, critical: false },
    { step_id: 'step-05', index: 4, name: 'Final shaping (INFERRED)', state_after: 'complete', start_sec: 38, end_sec: 50, keyframe_asset: 'kf_step05.jpg', certainty: 'inferred', source_established: true, critical: false },
  ];
  const checks: SkillCheck[] = [
    makeCheck('CHK-PR-COV', 'step_coverage', 'All 5 steps visible', '5/5 steps detected (INFERRED)', 'model_status', ['step-01', 'step-02', 'step-03', 'step-04', 'step-05'], 3, true),
    makeCheck('CHK-PR-ORD', 'step_order', 'Steps in the right order', 'Order matches source (INFERRED)', 'model_status', ['step-01', 'step-02', 'step-03', 'step-04', 'step-05'], 2, true),
    makeCheck('CHK-PR-OFF', 'off_path', 'No off-path detours', 'No unrecognised states (INFERRED)', 'model_status', [], 1),
    makeCheck('CHK-PR-FIN', 'final_similarity', 'Final result matches', '≥ 0.72 cosine (INFERRED)', 'specialist', ['step-05'], 2),
    makeCheck('CHK-PR-Q01', 'step_quality', 'Critical fold (step 2) quality', 'Shape correct within tolerance (INFERRED)', 'model_status', ['step-02'], 2, true),
  ];
  const model: SkillModel = {
    skill_title: title,
    summary: 'Follow the five-step procedure in order; the critical fold must be correct (INFERRED from video analysis).',
    source_modality: 'video',
    structures: ['procedure'],
    steps,
    order: 'strict',
    specialists: {},
    relevance: { expected_kinds: ['video', 'image'], min_similarity: 0.65 },
    checks,
  };
  return {
    case_id: `${slugify(title)}~${sha12(title)}`,
    title,
    skill_summary: model.summary,
    domain: 'craft / origami',
    transmission_mode: 'forward',
    learner_input_kinds: ['video'],
    probe: makeProbe('video/mp4', 4000000, { duration_sec: 50, has_audio: false, structures_available: ['procedure', 'final_state'], specialists_available: ['procedure_states'], reasons: { procedure: '≥ 2 distinct states detected', final_state: 'last still segment available' } }),
    intake: makeIntake('yes', '', 'folding procedure'),
    skill_model: model,
    warnings: ['AI-perceived steps are INFERRED; times and step names require expert review.'],
  };
}

function speechProposal(title: string): CaseProfile {
  const checks: SkillCheck[] = [
    makeCheck('CHK-UT-TXT', 'utterance_match', 'Transcript accuracy', 'Levenshtein distance ≤ 20% (INFERRED)', 'model_status', [], 3, true),
    makeCheck('CHK-UT-PACE', 'pace_match', 'Speaking pace in range', '± 30% of source pace (INFERRED)', 'model_status', [], 2),
  ];
  const model: SkillModel = {
    skill_title: title,
    summary: 'Reproduce the spoken phrase accurately at a similar pace (INFERRED from audio analysis).',
    source_modality: 'audio',
    structures: ['utterance'],
    utterance: { transcript: 'namaste, how are you', language: 'hi-en', duration_sec: 1.8 },
    specialists: {},
    relevance: { expected_kinds: ['audio'], min_similarity: 0.60 },
    checks,
  };
  return {
    case_id: `${slugify(title)}~${sha12(title)}`,
    title,
    skill_summary: model.summary,
    domain: 'language / greeting',
    transmission_mode: 'forward',
    learner_input_kinds: ['audio'],
    probe: makeProbe('audio/wav', 80000, { duration_sec: 3, structures_available: ['utterance'], specialists_available: [], reasons: { utterance: 'speech-likeness score > threshold' } }),
    intake: makeIntake('yes', '', 'spoken greeting'),
    skill_model: model,
    warnings: ['Transcript is INFERRED by the AI model; verify before publishing.'],
  };
}

function rhythmProposal(title: string): CaseProfile {
  const checks: SkillCheck[] = [
    makeCheck('CHK-RT-TEMPO', 'rhythm', 'Tempo within 5%', '± 5% BPM (MEASURED)', 'specialist', [], 2, true),
    makeCheck('CHK-RT-TIMING', 'rhythm', 'Onset timing accuracy', 'Median deviation ≤ 50 ms (MEASURED)', 'specialist', [], 3, true),
    makeCheck('CHK-RT-PATTERN', 'rhythm', 'Pattern matches source', 'Bass pattern accuracy ≥ 0.9 (MEASURED)', 'specialist', [], 3, true),
  ];
  const model: SkillModel = {
    skill_title: title,
    summary: 'Reproduce the rhythm pattern at the source tempo with accurate onset timing (MEASURED).',
    source_modality: 'audio',
    structures: ['temporal_pattern'],
    temporal: { tempo_bpm: 100, cycle_length: 8, onset_count: 32 },
    specialists: { rhythm: { onset_rate: 4, percussive_contrast: 2.5 } },
    relevance: { expected_kinds: ['audio'], min_similarity: 0.68 },
    checks,
  };
  return {
    case_id: `${slugify(title)}~${sha12(title)}`,
    title,
    skill_summary: model.summary,
    domain: 'music / percussion',
    transmission_mode: 'forward',
    learner_input_kinds: ['audio'],
    probe: makeProbe('audio/wav', 120000, { duration_sec: 8, structures_available: ['temporal_pattern'], specialists_available: ['rhythm'], reasons: { temporal_pattern: 'rhythm available', rhythm: 'onset rate ≥ 1.5/s, percussive contrast ≥ 1.5' } }),
    intake: makeIntake('yes', '', 'rhythmic percussion'),
    skill_model: model,
    warnings: [],
  };
}

// ---------------------------------------------------------------------------
// Draft segment / observation helpers
// ---------------------------------------------------------------------------

function makeSegments(modality: 'image' | 'video' | 'audio'): Segment[] {
  if (modality === 'image') {
    return [
      { segment_id: 'seg-000', kind: 'whole' },
      { segment_id: 'seg-001', kind: 'region', region: [10, 10, 40, 40] },
      { segment_id: 'seg-002', kind: 'region', region: [0, 0, 100, 100] },
      { segment_id: 'seg-003', kind: 'region', region: [45, 5, 10, 90] },
    ];
  }
  if (modality === 'video') {
    return [
      { segment_id: 'seg-000', kind: 'whole' },
      { segment_id: 'seg-001', kind: 'time', start_sec: 0, end_sec: 10, keyframe_sec: 4, keyframe_asset: 'kf_step01.jpg', stability: 0.9 },
      { segment_id: 'seg-002', kind: 'time', start_sec: 10, end_sec: 20, keyframe_sec: 14, keyframe_asset: 'kf_step02.jpg', stability: 0.85 },
      { segment_id: 'seg-003', kind: 'time', start_sec: 20, end_sec: 30, keyframe_sec: 24, keyframe_asset: 'kf_step03.jpg', stability: 0.88 },
      { segment_id: 'seg-004', kind: 'time', start_sec: 30, end_sec: 40, keyframe_sec: 34, keyframe_asset: 'kf_step04.jpg', stability: 0.92 },
      { segment_id: 'seg-005', kind: 'time', start_sec: 40, end_sec: 50, keyframe_sec: 44, keyframe_asset: 'kf_step05.jpg', stability: 0.95 },
    ];
  }
  // audio
  return [
    { segment_id: 'seg-000', kind: 'whole' },
    { segment_id: 'seg-001', kind: 'time', start_sec: 0, end_sec: 4 },
    { segment_id: 'seg-002', kind: 'time', start_sec: 4, end_sec: 8 },
  ];
}

function makeObservations(modality: 'image' | 'video' | 'audio', isSpeech = false): Observation[] {
  if (modality === 'image') {
    return [
      { obs_id: 'obs-000', segment_id: 'seg-000', kind: 'measurement', label: 'ink fraction', value: 0.12, unit: 'fraction', certainty: 'observed', producer: 'det:image_basic' },
      { obs_id: 'obs-001', segment_id: 'seg-000', kind: 'measurement', label: 'blur score', value: 420, certainty: 'observed', producer: 'det:image_basic' },
      { obs_id: 'obs-002', segment_id: 'seg-001', kind: 'property', label: 'continuous outline strokes', detail: 'Outline appears unbroken (INFERRED)', certainty: 'inferred', producer: 'model:vision_fast' },
      { obs_id: 'obs-003', segment_id: 'seg-002', kind: 'quality', label: 'avoid: stray marks outside design', detail: 'Keep marks within the pattern boundary (INFERRED)', certainty: 'inferred', producer: 'model:vision_fast' },
      { obs_id: 'obs-004', segment_id: 'seg-003', kind: 'property', label: 'vertical axis symmetry', detail: 'Left-right symmetry visible (INFERRED)', certainty: 'inferred', producer: 'model:vision_fast' },
    ];
  }
  if (modality === 'video') {
    return [
      { obs_id: 'obs-000', segment_id: 'seg-000', kind: 'measurement', label: 'duration', value: 50, unit: 's', certainty: 'observed', producer: 'det:video_segment' },
      { obs_id: 'obs-001', segment_id: 'seg-000', kind: 'measurement', label: 'segment count', value: 5, certainty: 'observed', producer: 'det:video_segment' },
      { obs_id: 'obs-002', segment_id: 'seg-001', kind: 'state', label: 'base folded', detail: 'Initial fold forms the base (INFERRED)', certainty: 'inferred', producer: 'model:vision_fast' },
      { obs_id: 'obs-003', segment_id: 'seg-002', kind: 'action', label: 'form petal shape', detail: 'Critical fold step (INFERRED)', certainty: 'inferred', producer: 'model:vision_fast' },
      { obs_id: 'obs-004', segment_id: 'seg-003', kind: 'action', label: 'reverse-fold corners', detail: '(INFERRED)', certainty: 'inferred', producer: 'model:vision_fast' },
      { obs_id: 'obs-005', segment_id: 'seg-004', kind: 'action', label: 'open centre', detail: '(INFERRED)', certainty: 'inferred', producer: 'model:vision_fast' },
      { obs_id: 'obs-006', segment_id: 'seg-005', kind: 'state', label: 'complete form', detail: 'Final state (INFERRED)', certainty: 'inferred', producer: 'model:vision_fast' },
    ];
  }
  // audio
  if (isSpeech) {
    return [
      { obs_id: 'obs-000', segment_id: 'seg-000', kind: 'measurement', label: 'duration', value: 1.8, unit: 's', certainty: 'observed', producer: 'det:audio_signal' },
      { obs_id: 'obs-001', segment_id: 'seg-000', kind: 'speech', label: 'transcript: namaste, how are you', detail: 'INFERRED — verify manually', certainty: 'inferred', producer: 'model:audio' },
    ];
  }
  return [
    { obs_id: 'obs-000', segment_id: 'seg-000', kind: 'measurement', label: 'onset count', value: 32, certainty: 'observed', producer: 'det:audio_signal' },
    { obs_id: 'obs-001', segment_id: 'seg-000', kind: 'measurement', label: 'onset rate', value: 4.0, unit: '/s', certainty: 'observed', producer: 'det:audio_signal' },
    { obs_id: 'obs-002', segment_id: 'seg-001', kind: 'event', label: 'percussive onset cluster', detail: 'Regular intervals detected (INFERRED)', certainty: 'inferred', producer: 'model:audio' },
  ];
}

// ---------------------------------------------------------------------------
// Draft builder
// ---------------------------------------------------------------------------

let draftSeq = 0;

export function buildImageDraft(name: string, size: number, title = ''): DraftView {
  const id = sha12(`img-${name}-${++draftSeq}`);
  const t = title || `Line-art skill from ${name}`;
  return {
    draft_id: id,
    probe: makeProbe('image/jpeg', size, { width: 512, height: 512, structures_available: ['final_state'], specialists_available: ['line_art'], reasons: { final_state: 'image available', line_art: 'ink fraction and separation OK' } }),
    intake: makeIntake('yes', '', 'line-drawing / pattern art'),
    proposal: imageProposal(t),
    refused: false,
    refusal_message: null,
    warnings: ['AI-perceived elements are INFERRED. MOCK DATA — no real analysis performed.'],
    structure_labels: STRUCTURE_LABELS,
    specialist_labels: SPECIALIST_LABELS,
    perception: { segments: makeSegments('image'), observations: makeObservations('image') },
  };
}

export function buildRefusedDraft(name: string): DraftView {
  const id = sha12(`refuse-${name}-${++draftSeq}`);
  return {
    draft_id: id,
    probe: makeProbe('image/jpeg', 10000, { width: 100, height: 100, structures_available: [], specialists_available: [], reasons: { final_state: 'image available' } }),
    intake: { safety: { decision: 'refuse', categories: ['weapon_or_harm'] }, teachable: 'no', teachable_reason: 'Content refused by the safety gate', skill_kind: null },
    proposal: null,
    refused: true,
    refusal_message: "We can't use this file: it may contain harmful content. Please upload a different image.",
    warnings: [],
    structure_labels: STRUCTURE_LABELS,
    specialist_labels: SPECIALIST_LABELS,
    perception: { segments: [{ segment_id: 'seg-000', kind: 'whole' }], observations: [] },
  };
}

export function buildUnclearDraft(name: string): DraftView {
  const id = sha12(`unclear-${name}-${++draftSeq}`);
  return {
    draft_id: id,
    probe: makeProbe('image/jpeg', 200000, { width: 400, height: 400, structures_available: ['final_state'], specialists_available: [], reasons: { final_state: 'image available', line_art: 'separation below threshold' } }),
    intake: makeIntake('unclear', 'AI could not determine the skill type from the image alone', 'unknown visual artefact'),
    proposal: null,
    refused: false,
    refusal_message: null,
    warnings: ['Tell us what skill this is (title and what a learner should achieve) to continue.'],
    structure_labels: STRUCTURE_LABELS,
    specialist_labels: SPECIALIST_LABELS,
    perception: { segments: makeSegments('image'), observations: makeObservations('image') },
  };
}

export function buildVideoDraft(name: string, size: number, title = ''): DraftView {
  const id = sha12(`vid-${name}-${++draftSeq}`);
  const t = title || `Folding procedure from ${name}`;
  return {
    draft_id: id,
    probe: makeProbe('video/mp4', size, { duration_sec: 50, has_audio: false, structures_available: ['procedure', 'final_state'], specialists_available: ['procedure_states'], reasons: { procedure: '5 distinct still segments', final_state: 'last still segment available', procedure_states: '≥ 2 keyframe embeddings differ' } }),
    intake: makeIntake('yes', '', 'folding procedure'),
    proposal: videoProposal(t),
    refused: false,
    refusal_message: null,
    warnings: ['Step times and names are INFERRED. MOCK DATA — no real analysis performed.'],
    structure_labels: STRUCTURE_LABELS,
    specialist_labels: SPECIALIST_LABELS,
    perception: { segments: makeSegments('video'), observations: makeObservations('video') },
  };
}

export function buildSpeechDraft(name: string, size: number, title = ''): DraftView {
  const id = sha12(`speech-${name}-${++draftSeq}`);
  const t = title || `Spoken greeting from ${name}`;
  return {
    draft_id: id,
    probe: makeProbe('audio/wav', size, { duration_sec: 3, structures_available: ['utterance'], specialists_available: [], reasons: { utterance: 'speech-likeness above threshold' } }),
    intake: makeIntake('yes', '', 'spoken greeting'),
    proposal: speechProposal(t),
    refused: false,
    refusal_message: null,
    warnings: ['Transcript is INFERRED. MOCK DATA — no real analysis performed.'],
    structure_labels: STRUCTURE_LABELS,
    specialist_labels: SPECIALIST_LABELS,
    perception: { segments: makeSegments('audio'), observations: makeObservations('audio', true) },
  };
}

export function buildRhythmDraft(name: string, size: number, title = ''): DraftView {
  const id = sha12(`rhy-${name}-${++draftSeq}`);
  const t = title || `Rhythm pattern from ${name}`;
  return {
    draft_id: id,
    probe: makeProbe('audio/wav', size, { duration_sec: 8, structures_available: ['temporal_pattern'], specialists_available: ['rhythm'], reasons: { temporal_pattern: 'rhythm specialist available', rhythm: 'onset rate and percussive contrast pass thresholds' } }),
    intake: makeIntake('yes', '', 'rhythmic percussion'),
    proposal: rhythmProposal(t),
    refused: false,
    refusal_message: null,
    warnings: ['MOCK DATA — no real analysis performed.'],
    structure_labels: STRUCTURE_LABELS,
    specialist_labels: SPECIALIST_LABELS,
    perception: { segments: makeSegments('audio'), observations: makeObservations('audio', false) },
  };
}

// ---------------------------------------------------------------------------
// Route: select draft type by MIME + file name
// ---------------------------------------------------------------------------

export function selectDraft(file: { name: string; type: string; size: number }, title = ''): DraftView {
  const name = file.name.toLowerCase();
  const mime = file.type || 'application/octet-stream';
  if (name.includes('unclear')) return buildUnclearDraft(file.name);
  if (name.includes('refuse') || name.includes('refus')) return buildRefusedDraft(file.name);
  if (mime.startsWith('video/')) return buildVideoDraft(file.name, file.size, title);
  if (mime.startsWith('audio/')) {
    if (name.includes('speech') || name.includes('voice') || name.includes('speak')) return buildSpeechDraft(file.name, file.size, title);
    return buildRhythmDraft(file.name, file.size, title);
  }
  // default: image
  return buildImageDraft(file.name, file.size, title);
}

// ---------------------------------------------------------------------------
// refine: re-runs step 5 only, returns a proposal
// ---------------------------------------------------------------------------

export function refineDraft(existing: DraftView, title: string, description: string): DraftView {
  const refined = clone(existing);
  // If it was unclear, now we have a title/description → build a proposal
  if (refined.proposal === null) {
    const probe = refined.probe;
    const t = title.trim() || 'Composed skill';
    if (probe.modality === 'image') refined.proposal = imageProposal(t);
    else if (probe.modality === 'video') refined.proposal = videoProposal(t);
    else if (description.toLowerCase().includes('speech') || description.toLowerCase().includes('speak') || description.toLowerCase().includes('word') || description.toLowerCase().includes('phrase')) refined.proposal = speechProposal(t);
    else refined.proposal = rhythmProposal(t);
    refined.warnings = ['AI-perceived elements are INFERRED. MOCK DATA — no real analysis performed.'];
  }
  if (refined.proposal) {
    refined.proposal.title = title.trim() || refined.proposal.title;
    if (description.trim()) refined.proposal.skill_model.summary = description.trim();
  }
  return refined;
}

// ---------------------------------------------------------------------------
// createFromDraft → CaseView
// ---------------------------------------------------------------------------

export function composedCaseView(profile: CaseProfile, sourceObjectUrl: string | null): CaseView {
  const sm = profile.skill_model;
  const structures = sm.structures;
  const caseId = profile.case_id;

  // Build rubric criteria from enabled checks
  const criteria = sm.checks.filter((c) => c.enabled !== false).map((c) => ({
    criterion_id: `CRIT-U-${c.check_id}`,
    name: c.name,
    description: c.observable_indicator,
    observable_indicator: c.observable_indicator,
    weight: c.weight ?? 2,
    required: c.required ?? false,
  }));

  const passingScore = criteria.filter((c) => c.required).reduce((s, c) => s + c.weight, 0);

  // Build claims from enabled checks + properties
  const claims = [
    ...((sm.goal_state ?? []).filter((p) => p.keep !== false).map((p, i) => ({
      claim_id: `CLM-U-PROP-${String(i + 1).padStart(2, '0')}`,
      claim_type: 'condition' as const,
      statement: p.statement,
      is_observed: p.certainty === 'observed',
      evidence_refs: [] as [],
    }))),
    ...((sm.steps ?? []).map((s, i) => ({
      claim_id: `CLM-U-STEP-${String(i + 1).padStart(2, '0')}`,
      claim_type: 'step' as const,
      statement: `${s.name} (step ${s.index + 1}${s.source_established ? ', demonstrated' : ', suggested'})`,
      is_observed: s.certainty === 'observed',
      evidence_refs: [] as [],
    }))),
  ];

  if (claims.length === 0) {
    claims.push({ claim_id: 'CLM-U-001', claim_type: 'condition', statement: `Skill goal: ${sm.summary}`, is_observed: false, evidence_refs: [] });
  }

  const sourceId = `upload.${caseId.split('~')[1]}`;

  // universal ui_view
  const uiView = {
    structures,
    goal_state: sm.goal_state?.filter((p) => p.keep !== false),
    steps: sm.steps,
    checks: sm.checks.filter((c) => c.enabled !== false).map((c) => ({ check_id: c.check_id, name: c.name, method: c.method, enabled: true, weight: c.weight, required: c.required, observable_indicator: c.observable_indicator })),
    reference_assets: [],
    transcript: (sm.utterance as { transcript?: string } | null | undefined)?.transcript ?? null,
  };

  const sourceRecordRole = profile.probe.modality === 'image' ? 'target_image' : profile.probe.modality === 'video' ? 'expert_video' : 'expert_audio';

  return {
    case_id: caseId,
    title: profile.title,
    modality: 'universal',
    hero: false,
    runtime_label: 'UPLOAD',
    review_status: 'pending',
    derived_from: null,
    warnings: [
      'Composed skill · AI-perceived elements are inferred until reviewed.',
      ...(profile.warnings ?? []),
      'MOCK DATA — no real analysis performed.',
    ],
    sources: [{
      source_id: sourceId,
      role: sourceRecordRole,
      mime_type: profile.probe.mime_type,
      sha256: 'mock',
      bytes: profile.probe.bytes,
      duration_sec: profile.probe.duration_sec,
      creator: 'uploader',
      license: 'uploader-provided',
      attribution: profile.title,
      runtime_label: 'UPLOAD',
      used_by_system: true,
    }],
    goal: {
      case_id: caseId,
      version: 1,
      modality: 'universal',
      source_ids: [sourceId],
      package_id: `kp.${caseId}`,
      ui_view: uiView,
      warnings: profile.warnings ?? [],
    },
    package: {
      package_id: `kp.${caseId}`,
      skill_id: `skill.${caseId}`,
      title: profile.title,
      summary: profile.skill_summary,
      claims,
      consent: { contributor_name: 'uploader', consent_scope: 'uploader-provided', revocable: true },
      expert_review: { reviewer_name: 'unassigned', status: 'pending' },
    },
    rubric: {
      rubric_id: `rubric.${caseId}`,
      skill_id: `skill.${caseId}`,
      title: `${profile.title} — rubric`,
      criteria,
      passing_score: passingScore,
    },
    task: {
      task_id: `task.${caseId}`,
      package_id: `kp.${caseId}`,
      rubric_id: `rubric.${caseId}`,
      title: `Practice: ${profile.title}`,
      instructions: profile.skill_summary,
      constraints: profile.learner_input_kinds.map((k) => ({ constraint_type: 'input', description: `Upload: ${k}` })),
      target_criteria_ids: criteria.map((c) => c.criterion_id),
    },
    profile,
  };
}

// In-memory store for drafts during mock session
const draftStore = new Map<string, DraftView>();
const objectUrlStore = new Map<string, string | null>();

export function storeDraft(draft: DraftView, fileObjectUrl: string | null): void {
  draftStore.set(draft.draft_id, draft);
  objectUrlStore.set(draft.draft_id, fileObjectUrl);
}

export function loadDraft(id: string): DraftView | undefined {
  return draftStore.get(id);
}

export function composedMediaUrl(caseId: string, sourceId: string): string | null {
  for (const [draftId, draft] of draftStore.entries()) {
    const profile = draft.proposal;
    if (!profile) continue;
    if (profile.case_id === caseId) {
      const sid = sourceId.split('#')[0];
      if (sid === `upload.${caseId.split('~')[1]}`) {
        return objectUrlStore.get(draftId) ?? null;
      }
    }
  }
  return null;
}

/** Synthetic keyframe assets for video mocks — returns a data-URL. */
export function keyframeAssetUrl(_caseId: string, asset: string): string {
  const labels: Record<string, string> = {
    'kf_step01.jpg': 'Step 1',
    'kf_step02.jpg': 'Step 2',
    'kf_step03.jpg': 'Step 3',
    'kf_step04.jpg': 'Step 4',
    'kf_step05.jpg': 'Step 5',
  };
  return syntheticKeyframe(labels[asset] ?? asset);
}

// ---------------------------------------------------------------------------
// Evaluate a universal attempt (very simple mock)
// ---------------------------------------------------------------------------

export function evaluateUniversal(view: CaseView, sessionId: string, learner: string, n: number, _kind: string): import('../types').AttemptResult {
  const rubric = view.rubric;
  const isRetry = n > 1;
  const outcomes: Record<string, CriterionOutcome> = {};
  for (const c of rubric.criteria) {
    if (isRetry) {
      outcomes[c.criterion_id] = { status: 'satisfied', finding: 'Goal criteria met after retry (MOCK).' };
    } else {
      outcomes[c.criterion_id] = c.required ? { status: 'partially_satisfied', finding: 'Goal criteria partially met (MOCK).' } : { status: 'satisfied', finding: 'Criterion satisfied (MOCK).' };
    }
  }
  const evaluation = buildEvaluation(rubric, `att.mock.${sessionId}.${n}`, outcomes, 'model_assisted', n);
  const sourceId = view.goal.source_ids[0] ?? 'mock';
  const ev = evidence(`${sourceId}#mock`, view.profile?.probe.modality ?? 'image', 'inferred', 0.7, {});
  return assembleResult({
    view,
    attempt: buildAttempt(view, sessionId, learner, n, 'image', `att.${sessionId}.${n}`),
    evaluation,
    trajectory: {
      curve: [[0, 0], [1, isRetry ? 0.85 : 0.55]],
      curve_kind: 'frame',
      events: isRetry ? [] : [{ metric: 'similarity', kind: 'below_threshold', position: 0, position_kind: 'frame', evidence: ev, detail: 'Similarity below threshold (MOCK)', severity: 'material' }],
      process_observable: false,
      artifacts: {},
      final_state: { score: isRetry ? 0.85 : 0.55 },
    },
    metrics: { similarity: { value: isRetry ? 0.85 : 0.55, finding: `Overall similarity: ${isRetry ? '0.85' : '0.55'} (MOCK)` } },
    first: isRetry ? null : {
      criterion_id: rubric.criteria[0]?.criterion_id ?? '',
      criterion_name: rubric.criteria[0]?.name ?? '',
      status: 'partially_satisfied',
      position: 0,
      position_kind: 'frame',
      learner_evidence: ev,
      expert_evidence: ev,
      observed_finding: 'Below the similarity threshold (MOCK).',
      why_it_matters: rubric.criteria[0]?.description ?? '',
      source_claim_ids: [],
      drill_hint: 'Review the reference properties and try again.',
    },
    expertRefFor: () => ev,
    runtimeClass: 'RECORDED_LIVE',
    warnings: ['MOCK evaluation — no real model analysis performed.'],
  });
}

export { delay };
