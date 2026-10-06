/**
 * MOCK DATA (SYNTHETIC) — Origami hero case.
 * Source metadata mirrors tracks/cases/origami/source/source.json (OrigamiCrane.ogv, Tavin, CC BY 3.0).
 * The paper states, timestamps and keyframe drawings below are ILLUSTRATIVE placeholders for the
 * Track A origami goal builder output; keyframes are generated SVG diagrams, not video frames.
 */

import type { AttemptResult, CaseView, DivergenceEvent, OrigamiFrameLabel, OrigamiUiView } from '../types';
import { assembleResult, buildAttempt, buildEvaluation, buildFirstDivergence, evidence, type CriterionOutcome } from './builders';

export const ORIGAMI_SOURCE = 'src.origami.demo.v1';

const STATES: { name: string; props: string[]; s: number; e: number; poly: string }[] = [
  { name: 'Flat square', props: ['single square sheet', 'coloured side down'], s: 4, e: 14, poly: '10,10 90,10 90,90 10,90' },
  { name: 'Diagonal and book creases', props: ['both diagonals creased', 'both midlines creased'], s: 14, e: 48, poly: '10,10 90,10 90,90 10,90' },
  { name: 'Preliminary (square) base', props: ['four-layer square', 'open end pointing down'], s: 48, e: 96, poly: '50,8 92,50 50,92 8,50' },
  { name: 'Kite folds creased', props: ['lower edges folded to centre line', 'top triangle creased'], s: 96, e: 142, poly: '50,8 78,50 50,92 22,50' },
  { name: 'Front petal fold', props: ['front flap lifted and flattened', 'long diamond on front'], s: 142, e: 196, poly: '50,4 70,50 50,96 30,50' },
  { name: 'Bird base', props: ['both sides petal-folded', 'two free flaps at bottom'], s: 196, e: 236, poly: '50,4 66,50 50,96 34,50' },
];

function keyframeSvg(i: number): string {
  const st = STATES[i];
  const creases =
    i >= 1
      ? '<line x1="10" y1="10" x2="90" y2="90" stroke="#00e5ff" stroke-width="0.6" stroke-dasharray="2 2"/><line x1="90" y1="10" x2="10" y2="90" stroke="#00e5ff" stroke-width="0.6" stroke-dasharray="2 2"/>'
      : '';
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#0f1214"/><polygon points="${st.poly}" fill="#e9e4d8" stroke="#e67e22" stroke-width="1"/>${i < 2 ? creases : `<line x1="50" y1="8" x2="50" y2="92" stroke="#00e5ff" stroke-width="0.6" stroke-dasharray="2 2"/>`}<text x="4" y="97" font-family="monospace" font-size="6" fill="#9ba1a6">R${i} · SYNTHETIC</text></svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

export function origamiGoalAsset(asset: string): string {
  const m = /keyframe_(\d+)/.exec(asset);
  return keyframeSvg(m ? Math.min(STATES.length - 1, Number(m[1])) : 0);
}

export const origamiUiView: OrigamiUiView = {
  states: STATES.map((st, i) => ({
    index: i,
    name: st.name,
    properties: st.props,
    start_sec: st.s,
    end_sec: st.e,
    keyframe_sec: Math.round((st.s + st.e) / 2),
    keyframe_asset: `keyframe_${i}.jpg`,
  })),
  window_sec: [0, 240],
  source_id: ORIGAMI_SOURCE,
};

const vev = (i: number, state: 'observed' | 'inferred', conf: number, cue?: string) =>
  evidence(`${ORIGAMI_SOURCE}#step=${i}`, 'video', state, conf, { start_sec: STATES[i].s, end_sec: STATES[i].e, ...(cue ? { cue_excerpt: cue } : {}) });

export function origamiCaseView(caseId = 'origami', extra: Partial<CaseView> = {}): CaseView {
  return {
    case_id: caseId,
    title: 'Origami — crane up to the bird base (video)',
    modality: 'origami_video',
    hero: true,
    runtime_label: 'INTERNET_REFERENCE',
    review_status: 'approved',
    derived_from: null,
    warnings: ['MOCK DATA: state timings and keyframes are illustrative; expert video is not bundled in mock mode.'],
    sources: [
      {
        source_id: ORIGAMI_SOURCE,
        role: 'expert_video',
        mime_type: 'video/ogg',
        sha256: '4489d37966da1be348742b9cb8f0e99abda7553078bfce2e7abe94062f32b485',
        bytes: 25026185,
        duration_sec: 335,
        dimensions: [400, 226],
        window_sec: [0, 240],
        creator: 'Tavin',
        license: 'CC BY 3.0',
        attribution: 'OrigamiCrane.ogv by Tavin, CC BY 3.0, via Wikimedia Commons',
        runtime_label: 'INTERNET_REFERENCE',
        used_by_system: true,
      },
    ],
    goal: {
      case_id: caseId,
      version: 1,
      modality: 'origami_video',
      source_ids: [ORIGAMI_SOURCE],
      package_id: 'kp.origami.v1',
      built_with: { builder: 'mock (illustrative)', fps: 1 },
      warnings: [],
      ui_view: origamiUiView,
    },
    package: {
      package_id: 'kp.origami.v1',
      skill_id: 'skill.origami.bird_base',
      title: 'Crane to bird base — demonstrated paper states',
      summary: 'Ordered paper states recognised from the demonstration video. The order is source-established because the expert performed it.',
      claims: [
        ...STATES.map((st, i) => ({
          claim_id: `CLM-ORI-00${i + 1}`,
          claim_type: 'step' as const,
          statement: `State R${i} “${st.name}”: ${st.props.join('; ')}.`,
          is_observed: true,
          evidence_refs: [vev(i, 'observed', 0.8, `keyframe at ${Math.round((st.s + st.e) / 2)}s`)],
        })),
        {
          claim_id: 'CLM-ORI-007',
          claim_type: 'cue' as const,
          statement: 'The petal fold works only if the kite creases are sharp first; the flap lifts along those creases.',
          is_observed: false,
          evidence_refs: [vev(4, 'inferred', 0.5)],
        },
        {
          claim_id: 'CLM-ORI-008',
          claim_type: 'failure_mode' as const,
          statement: 'Skipping the kite creases makes the petal fold tear or bunch at the top point.',
          is_observed: false,
          evidence_refs: [vev(3, 'inferred', 0.4)],
        },
      ],
      consent: { contributor_name: 'Tavin (CC BY 3.0)', consent_scope: 'cc_by_3.0_reference', revocable: false },
      expert_review: { reviewer_name: 'Mock Reviewer', status: 'approved', notes: 'MOCK review state' },
    },
    rubric: {
      rubric_id: 'rubric.origami.v1',
      skill_id: 'skill.origami.bird_base',
      title: 'Origami goal-trajectory rubric',
      criteria: [
        { criterion_id: 'CRIT-ORI-FINAL', name: 'Reaches the target form (bird base)', description: 'Last stable state is R5.', observable_indicator: 'final state = R5', weight: 3, required: true },
        { criterion_id: 'CRIT-ORI-ORDER', name: 'Folds in the demonstrated order', description: 'No regressions ≥2 states.', observable_indicator: 'order consistent', weight: 2, required: true },
        { criterion_id: 'CRIT-ORI-COMPLETE', name: 'Every demonstrated state reached', description: 'No skipped states.', observable_indicator: 'all states', weight: 2, required: false },
        { criterion_id: 'CRIT-ORI-CLEAN', name: 'No off-path folds', description: 'No off_path runs ≥2 frames.', observable_indicator: '0 off-path runs', weight: 1, required: false },
        { criterion_id: 'CRIT-ORI-KEYSTEP', name: 'Petal fold executed as shown', description: 'R3 → R4 transition matches the source.', observable_indicator: 'R3 then R4', weight: 2, required: false },
      ],
      passing_score: 7,
    },
    task: {
      task_id: 'task.origami.v1',
      package_id: 'kp.origami.v1',
      rubric_id: 'rubric.origami.v1',
      title: 'Fold a square into the bird base',
      instructions: 'Record yourself folding a square sheet into the bird base, following the demonstrated states R0–R5 (CLM-ORI-001…006). Keep the paper in view.',
      constraints: [{ constraint_type: 'input', description: 'Video upload; frames sampled at 1 fps (max 90).' }],
      target_criteria_ids: ['CRIT-ORI-FINAL', 'CRIT-ORI-ORDER', 'CRIT-ORI-COMPLETE', 'CRIT-ORI-CLEAN', 'CRIT-ORI-KEYSTEP'],
    },
    criterion_map: {
      rubric_id: 'rubric.origami.v1',
      package_id: 'kp.origami.v1',
      criteria: {
        'CRIT-ORI-FINAL': { order_index: 0, source_claim_ids: ['CLM-ORI-006'], reference_evidence_ids: [], why_it_matters: 'The bird base is the goal state of this segment (CLM-ORI-006).', drill_hint: 'Compare your last frame with keyframe R5.' },
        'CRIT-ORI-ORDER': { order_index: 1, source_claim_ids: ['CLM-ORI-003'], reference_evidence_ids: [], why_it_matters: 'Each fold builds on the previous state (CLM-ORI-003).', drill_hint: 'Pause after each state and match it to the keyframe strip.' },
        'CRIT-ORI-COMPLETE': { order_index: 2, source_claim_ids: ['CLM-ORI-004'], reference_evidence_ids: [], why_it_matters: 'The kite creases (CLM-ORI-004) guide the petal fold.', drill_hint: 'Fold both lower edges to the centre line, crease sharply, then unfold.' },
        'CRIT-ORI-CLEAN': { order_index: 3, source_claim_ids: ['CLM-ORI-008'], reference_evidence_ids: [], why_it_matters: 'Off-path folds leave creases that fight the base (CLM-ORI-008).', drill_hint: 'If a fold does not match the next keyframe, unfold before continuing.' },
        'CRIT-ORI-KEYSTEP': { order_index: 4, source_claim_ids: ['CLM-ORI-007'], reference_evidence_ids: [], why_it_matters: 'The petal fold lifts along the kite creases (CLM-ORI-007).', drill_hint: 'Lift the bottom point of the front layer along the creases and flatten.' },
      },
    },
    ...extra,
  };
}

export function evaluateOrigami(view: CaseView, sessionId: string, learner: string, n: number): AttemptResult {
  const sourceId = `src.attempt.${view.case_id}.${sessionId}.${n}`;
  const retry = n > 1;
  // frame labels at 1 fps (SYNTHETIC)
  const plan: [number, OrigamiFrameLabel['state']][] = retry
    ? [[0, 0], [6, 1], [20, 2], [38, 'transition'], [40, 3], [55, 4], [72, 5]]
    : [[0, 0], [5, 1], [18, 2], [34, 'transition'], [36, 4], [44, 'off_path'], [48, 2], [52, 4], [66, 'unclear'], [70, 4]];
  const end = retry ? 80 : 78;
  const labels: OrigamiFrameLabel[] = [];
  for (let t = 0; t <= end; t++) {
    let s: OrigamiFrameLabel['state'] = 0;
    for (const [pt, ps] of plan) if (t >= pt) s = ps;
    labels.push({ t, state: s });
  }
  const k = STATES.length - 1;
  let best = 0;
  const curve: number[][] = labels.map((l) => {
    if (typeof l.state === 'number') best = Math.max(best, l.state);
    return [l.t, Number((best / k).toFixed(3))];
  });
  const events: DivergenceEvent[] = retry
    ? []
    : [
        { metric: 'complete', kind: 'missing_state', position: 36, position_kind: 'time', evidence: evidence(`${sourceId}#frame=36.000`, 'video', 'observed', 0.7, { start_sec: 34, end_sec: 37 }), detail: 'Jumped from R2 (preliminary base) to R4 (petal fold) — R3 kite creases never seen.', severity: 'material' },
        { metric: 'clean', kind: 'off_path', position: 44, position_kind: 'time', evidence: evidence(`${sourceId}#frame=44.000`, 'video', 'observed', 0.7, { start_sec: 44, end_sec: 47 }), detail: 'Paper in a state not on the demonstrated path for 4 frames (bunched top point).', severity: 'material' },
        { metric: 'order', kind: 'regression', position: 48, position_kind: 'time', evidence: evidence(`${sourceId}#frame=48.000`, 'video', 'observed', 0.7, { start_sec: 48, end_sec: 51 }), detail: 'Unfolded back to R2 (regression of 2 states).', severity: 'minor' },
      ];
  const outcomes: Record<string, CriterionOutcome> = retry
    ? {
        'CRIT-ORI-FINAL': { status: 'satisfied', finding: 'Last stable state R5 from 72 s; pairwise check matches R5 checklist (3/3).' },
        'CRIT-ORI-ORDER': { status: 'satisfied', finding: 'States reached in order R0→R5.' },
        'CRIT-ORI-COMPLETE': { status: 'satisfied', finding: 'All 6 states observed.' },
        'CRIT-ORI-CLEAN': { status: 'satisfied', finding: '0 off-path runs.' },
        'CRIT-ORI-KEYSTEP': { status: 'satisfied', finding: 'R3 (40–54 s) then R4 (55–71 s).' },
      }
    : {
        'CRIT-ORI-FINAL': { status: 'not_satisfied', finding: 'Last stable state R4 (front petal fold); R5 never reached.' },
        'CRIT-ORI-ORDER': { status: 'partially_satisfied', finding: '1 regression of 2 states at 48 s.', evidence: events[2].evidence },
        'CRIT-ORI-COMPLETE': { status: 'not_satisfied', finding: 'R3 (kite creases) skipped at 36 s; frames around the jump are clear.', evidence: events[0].evidence },
        'CRIT-ORI-CLEAN': { status: 'not_satisfied', finding: '1 off-path run (44–47 s).', evidence: events[1].evidence },
        'CRIT-ORI-KEYSTEP': { status: 'uncertain', finding: 'Petal fold attempted without R3; frames 66–69 s unclear.', deviation: 'key step not clearly visible (unclear frames)' },
      };
  const evaluation = buildEvaluation(view.rubric, `att.mock.${sessionId}.${n}`, outcomes, 'model_assisted', n);
  const first = retry
    ? null
    : buildFirstDivergence(view, evaluation, 'CRIT-ORI-COMPLETE', 36, 'time', events[0].evidence, vev(3, 'observed', 0.8, 'expected state R3: kite folds creased'), events[0].detail);
  return assembleResult({
    view,
    attempt: buildAttempt(view, sessionId, learner, n, 'video', sourceId),
    evaluation,
    trajectory: { curve, curve_kind: 'time', events, process_observable: true, artifacts: { frame_labels: labels }, final_state: { last_stable_state: retry ? 5 : 4 } },
    metrics: {
      final_match: { value: retry ? 1 : 0, finding: outcomes['CRIT-ORI-FINAL'].finding },
      skipped_states: { value: retry ? 0 : 1, finding: outcomes['CRIT-ORI-COMPLETE'].finding },
      off_path_runs: { value: retry ? 0 : 1, finding: outcomes['CRIT-ORI-CLEAN'].finding },
    },
    first,
    expertRefFor: (cid) => vev(cid === 'CRIT-ORI-FINAL' ? 5 : cid === 'CRIT-ORI-KEYSTEP' ? 4 : 3, 'observed', 0.8),
    runtimeClass: 'RECORDED_LIVE',
    warnings: ['Origami frame states would come from Gemma over sampled frames; these labels are SYNTHETIC.'],
  });
}
