/**
 * MOCK DATA (SYNTHETIC) — Kolam hero case.
 *
 * The target image is the real public-domain source (Ithayakkamalam - 2.jpg, Mayooranathan,
 * via Wikimedia Commons), copied to app/public/mock/kolam_target.jpg for offline UI work.
 * The geometry below (dots, curves) is the REAL builder output from the Track A kolam goal
 * builder, dumped from GET /api/cases/kolam. It replaces the earlier hand-approximated geometry.
 *
 * The mock trace evaluator is a simplified browser re-implementation of evaluation-core §3.2
 * (coverage / precision within τ, off-path runs, dot relations, curve completion, pen lifts)
 * so that drawing on the canvas produces plausible feedback in MOCK mode only.
 */

import type { EvidenceRef } from '../../types/contracts';
import type { AttemptResult, CaseView, DivergenceEvent, KolamCurveObj, KolamDot, KolamUiView, MetricView } from '../types';
import { assembleResult, buildAttempt, buildEvaluation, buildFirstDivergence, evidence, type CriterionOutcome } from './builders';
import REAL_UI_VIEW from './kolam-real-ui-view.json';

export const KOLAM_TARGET_SOURCE = 'src.kolam.target.v1';
export const KOLAM_TARGET_URL = '/mock/kolam_target.jpg';

// Real builder geometry (from GET /api/cases/kolam — replaces hand-approximated loops)
const W = REAL_UI_VIEW.canvas.width;
const H = REAL_UI_VIEW.canvas.height;
const TAU = REAL_UI_VIEW.tau ?? 6;
const LOOPS = REAL_UI_VIEW.rotation_order ?? 8;   // still 8-fold; used for rubric labels

// Real builder curves and dots (KolamCurveObj shape, not legacy number[][])
const curves = REAL_UI_VIEW.curves as KolamCurveObj[];
const dots = REAL_UI_VIEW.dots as KolamDot[];
const ON_LINE = dots.filter((d) => d.relation === 'on_line').length;

// Compute center for evidence regions from real dot data
const _cx = W / 2;
const _cy = H / 2;

export const kolamUiView: KolamUiView = {
  ...(REAL_UI_VIEW as KolamUiView),
  // Ensure target_source_id is set for mock URL lookup
  target_source_id: KOLAM_TARGET_SOURCE,
};

function pct(x: number, y: number, w: number, h: number): string {
  const cl = (v: number, lo = 0, hi = 100) => Math.min(hi, Math.max(lo, v));
  const px = cl((x / W) * 100);
  const py = cl((y / H) * 100);
  return `${KOLAM_TARGET_SOURCE}#xywh=percent:${px.toFixed(2)},${py.toFixed(2)},${cl((w / W) * 100, 0, 100 - px).toFixed(2)},${cl((h / H) * 100, 0, 100 - py).toFixed(2)}`;
}

function curveBox(k: number, pad = 8): string {
  // Support KolamCurveObj (real service format) and legacy number[][] (old mock)
  const pts = (curves[k] as KolamCurveObj).points ?? (curves[k] as unknown as number[][]);
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  const x0 = Math.min(...xs) - pad;
  const y0 = Math.min(...ys) - pad;
  return pct(x0, y0, Math.max(...xs) - x0 + pad, Math.max(...ys) - y0 + pad);
}

const ev = (src: string, state: EvidenceRef['verification_state'], conf: number, cue?: string) =>
  evidence(src, 'image', state, conf, cue ? { cue_excerpt: cue } : {});

export function kolamCaseView(caseId = 'kolam', extra: Partial<CaseView> = {}): CaseView {
  return {
    case_id: caseId,
    title: 'Kolam — Ithayakkamalam (final image only)',
    modality: 'kolam_image',
    hero: true,
    runtime_label: 'INTERNET_REFERENCE',
    review_status: 'pending',
    derived_from: null,
    warnings: ['MOCK DATA: real builder geometry (GET /api/cases/kolam); some package claims are mock-only.'],
    sources: [
      {
        source_id: KOLAM_TARGET_SOURCE,
        role: 'target_image',
        mime_type: 'image/jpeg',
        sha256: '0a3b13977ee4337c0e52d8cf53d66c6002d9fdf498b984784df89cbcbe38cc0e',
        bytes: 57663,
        path: 'source/ithayakkamalam_target.jpg',
        dimensions: [W, H],
        creator: 'Mayooranathan (Tamil Wikipedia)',
        license: 'Public domain',
        attribution: 'Ithayakkamalam - 2.jpg, by Mayooranathan, public domain, via Wikimedia Commons',
        runtime_label: 'INTERNET_REFERENCE',
        used_by_system: true,
      },
    ],
    goal: {
      case_id: caseId,
      version: 1,
      modality: 'kolam_image',
      source_ids: [KOLAM_TARGET_SOURCE],
      package_id: 'kp.kolam.v1',
      built_with: { builder: 'kolam_goal_v1 (real)', tau_px: TAU },
      warnings: [],
      ui_view: kolamUiView,
    },
    package: {
      package_id: 'kp.kolam.v1',
      skill_id: 'skill.kolam.ithayakkamalam',
      title: 'Ithayakkamalam kolam — goal model from the finished image',
      summary:
        'Built from the finished image only. Dots, symmetry and dot relations are computed (OBSERVED); the drawing path is one suggested decomposition (INFERRED); motif naming is UNVERIFIED.',
      claims: [
        {
          claim_id: 'CLM-KOLAM-001',
          claim_type: 'condition',
          statement: `The target has ${dots.length} pulli (dots): ${ON_LINE} lie on the line (including the 8 outer tips) and ${dots.length - ON_LINE} are enclosed.`,
          is_observed: true,
          evidence_refs: [ev(pct(15, 25, 462, 455), 'observed', 0.9, 'dot detection on the target image')],
        },
        {
          claim_id: 'CLM-KOLAM-002',
          claim_type: 'condition',
          statement: 'The pattern has 8-fold rotational symmetry about the centre dot; no mirror axis was found.',
          is_observed: true,
          evidence_refs: [ev(pct(15, 25, 462, 455), 'observed', 0.85, 'ink IoU under 45° rotation')],
        },
        {
          claim_id: 'CLM-KOLAM-003',
          claim_type: 'step',
          statement:
            'One suggested way to draw it: 8 closed loops, each passing through one outer-tip dot and around the centre. Start point and direction are arbitrary.',
          is_observed: false,
          evidence_refs: [ev(curveBox(0), 'inferred', 0.45, 'smooth-continuation decomposition of the skeleton')],
        },
        {
          claim_id: 'CLM-KOLAM-004',
          claim_type: 'condition',
          statement: 'Each outer-tip dot lies on the line; the dots marked enclosed (including the centre dot) are never touched.',
          is_observed: true,
          evidence_refs: [ev(pct(_cx - 60, _cy - 60, 120, 120), 'observed', 0.8, 'dot/curve relation')],
        },
        {
          claim_id: 'CLM-KOLAM-005',
          claim_type: 'failure_mode',
          statement: 'A stray line off the pattern cannot be erased in a powder kolam, so any off-path stroke stays visible.',
          is_observed: false,
          evidence_refs: [ev(pct(15, 25, 462, 455), 'inferred', 0.4)],
        },
        {
          claim_id: 'CLM-KOLAM-006',
          claim_type: 'cue',
          statement: 'The motif may be a lotus (kamalam) form — uncertain; not established by the image.',
          is_observed: false,
          evidence_refs: [],
        },
      ],
      consent: {
        contributor_name: 'Mayooranathan (public domain image)',
        consent_scope: 'public_domain_reference',
        revocable: false,
        notes: 'Internet reference, not an owned or consented expert recording.',
      },
      expert_review: { reviewer_name: 'unassigned', status: 'pending' },
    },
    rubric: {
      rubric_id: 'rubric.kolam.v1',
      skill_id: 'skill.kolam.ithayakkamalam',
      title: 'Kolam goal-trajectory rubric',
      description: 'Template from evaluation-core §3.2; bands in observers.v1.',
      criteria: [
        { criterion_id: 'CRIT-KOLAM-COVERAGE', name: 'Every curve of the target is drawn', description: 'Goal skeleton covered within τ.', observable_indicator: 'coverage ≥ 0.90', weight: 3, required: true },
        { criterion_id: 'CRIT-KOLAM-PRECISION', name: 'No stray lines off the pattern', description: 'Learner ink within τ of the goal.', observable_indicator: 'precision ≥ 0.92', weight: 2, required: true },
        { criterion_id: 'CRIT-KOLAM-DOTS', name: 'Each pulli kept in the same relation to the line', description: 'on_line / enclosed relation preserved.', observable_indicator: 'dot accuracy ≥ 0.95', weight: 2, required: true },
        { criterion_id: 'CRIT-KOLAM-CURVES', name: 'Each continuous curve completed', description: 'Curve coverage ≥ 0.9 for all K curves.', observable_indicator: 'all K curves', weight: 2, required: false },
        { criterion_id: 'CRIT-KOLAM-CONTINUITY', name: 'Drawn as continuous strokes', description: 'Pen lifts vs K.', observable_indicator: 'lifts ≤ K+1', weight: 1, required: false },
      ],
      passing_score: 7,
    },
    task: {
      task_id: 'task.kolam.v1',
      package_id: 'kp.kolam.v1',
      rubric_id: 'rubric.kolam.v1',
      title: 'Draw the Ithayakkamalam kolam from the dots',
      instructions:
        'Using the dots shown, draw the target pattern. Keep each line continuous where you can (CLM-KOLAM-003), keep the outer-tip dots on the line and never touch the enclosed dots (CLM-KOLAM-004), and avoid stray lines (CLM-KOLAM-005).',
      constraints: [
        { constraint_type: 'input', description: 'Canvas trace (preferred) or a photo of a drawn kolam.' },
        { constraint_type: 'evidence_boundary', description: 'A photo shows only the final state: process criteria become UNCERTAIN.' },
      ],
      target_criteria_ids: ['CRIT-KOLAM-COVERAGE', 'CRIT-KOLAM-PRECISION', 'CRIT-KOLAM-DOTS', 'CRIT-KOLAM-CURVES', 'CRIT-KOLAM-CONTINUITY'],
    },
    criterion_map: {
      rubric_id: 'rubric.kolam.v1',
      package_id: 'kp.kolam.v1',
      criteria: {
        'CRIT-KOLAM-COVERAGE': { order_index: 0, source_claim_ids: ['CLM-KOLAM-003'], reference_evidence_ids: [], why_it_matters: 'The target is only complete when all 8 loops are present (CLM-KOLAM-003).', drill_hint: 'Trace one loop at a time from its outer-tip dot, around the centre and back.' },
        'CRIT-KOLAM-PRECISION': { order_index: 1, source_claim_ids: ['CLM-KOLAM-005'], reference_evidence_ids: [], why_it_matters: 'Stray powder cannot be removed, so off-path ink changes the pattern (CLM-KOLAM-005).', drill_hint: 'Slow down near crossings; keep the line inside the corridor between neighbouring dots.' },
        'CRIT-KOLAM-DOTS': { order_index: 2, source_claim_ids: ['CLM-KOLAM-004'], reference_evidence_ids: [], why_it_matters: 'The dot relations define the kolam’s structure (CLM-KOLAM-004).', drill_hint: 'Before each loop, find its outer-tip dot (on the line) and the inner dots it must go around.' },
        'CRIT-KOLAM-CURVES': { order_index: 3, source_claim_ids: ['CLM-KOLAM-003'], reference_evidence_ids: [], why_it_matters: 'Each loop closes on itself in the suggested decomposition (CLM-KOLAM-003).', drill_hint: 'Finish each loop back at its starting dot before starting the next.' },
        'CRIT-KOLAM-CONTINUITY': { order_index: 4, source_claim_ids: ['CLM-KOLAM-003'], reference_evidence_ids: [], why_it_matters: 'A loop drawn without lifting keeps its curvature smooth (CLM-KOLAM-003).', drill_hint: 'Draw each loop in one stroke.' },
      },
    },
    ...extra,
  };
}

// ---------------------------------------------------------------------------
// Mock trace evaluator
// ---------------------------------------------------------------------------

interface Trace {
  canvas: { width: number; height: number };
  strokes: { points: number[][] }[];
  duration_ms?: number;
}

const goalSamples: { x: number; y: number; curve: number }[] = (() => {
  const out: { x: number; y: number; curve: number }[] = [];
  curves.forEach((c, k) => {
    // Support KolamCurveObj (real service format) and legacy number[][] (old mock)
    const pts = (c as KolamCurveObj).points ?? (c as unknown as number[][]);
    let carry = 0;
    for (let i = 1; i < pts.length; i++) {
      const [x0, y0] = pts[i - 1];
      const [x1, y1] = pts[i];
      const len = Math.hypot(x1 - x0, y1 - y0);
      let s = carry;
      while (s < len) {
        const t = s / len;
        out.push({ x: x0 + (x1 - x0) * t, y: y0 + (y1 - y0) * t, curve: k });
        s += 4;
      }
      carry = s - len;
    }
  });
  return out;
})();

function densify(points: number[][], step = 2): number[][] {
  const out: number[][] = [];
  for (let i = 0; i < points.length; i++) {
    if (i === 0) {
      out.push(points[0]);
      continue;
    }
    const [x0, y0] = points[i - 1];
    const [x1, y1] = points[i];
    const len = Math.hypot(x1 - x0, y1 - y0);
    const n = Math.max(1, Math.ceil(len / step));
    for (let j = 1; j <= n; j++) out.push([x0 + ((x1 - x0) * j) / n, y0 + ((y1 - y0) * j) / n]);
  }
  return out;
}

function distToGoal(x: number, y: number): number {
  let best = Infinity;
  for (const g of goalSamples) {
    const d = (g.x - x) ** 2 + (g.y - y) ** 2;
    if (d < best) best = d;
  }
  return Math.sqrt(best);
}

function band(v: number, sat: number, partial: number): CriterionOutcome['status'] {
  return v >= sat ? 'satisfied' : v >= partial ? 'partially_satisfied' : 'not_satisfied';
}

export function evaluateKolamTrace(view: CaseView, sessionId: string, learner: string, n: number, traceText: string): AttemptResult {
  const trace = JSON.parse(traceText) as Trace;
  const sourceId = `src.attempt.${view.case_id}.${sessionId}.${n}`;
  const covered = new Uint8Array(goalSamples.length);
  const curve: number[][] = [[0, 0]];
  const events: DivergenceEvent[] = [];
  let onPath = 0;
  let total = 0;
  const allPts: number[][] = [];

  trace.strokes.forEach((s, k) => {
    const pts = densify(s.points);
    let run: number[][] = [];
    const flush = () => {
      if (run.length * 2 > 2 * TAU) {
        const xs = run.map((p) => p[0]);
        const ys = run.map((p) => p[1]);
        const x0 = Math.min(...xs);
        const y0 = Math.min(...ys);
        events.push({
          metric: 'precision',
          kind: 'off_path_ink',
          position: k + 1,
          position_kind: 'stroke',
          evidence: evidence(`${sourceId}#stroke=${k}`, 'image', 'observed', 1, {
            cue_excerpt: `stroke ${k + 1}: ${Math.round(run.length * 2)} px of ink outside the τ=${TAU}px corridor`,
          }),
          detail: `Stroke ${k + 1} leaves the pattern for ~${Math.round(run.length * 2)} px near (${Math.round(x0)}, ${Math.round(y0)}).`,
          severity: 'material',
        });
        (events[events.length - 1] as DivergenceEvent & { _box?: number[] })._box = [x0, y0, Math.max(...xs) - x0, Math.max(...ys) - y0];
      }
      run = [];
    };
    for (const [x, y] of pts) {
      total++;
      allPts.push([x, y]);
      const d = distToGoal(x, y);
      if (d <= TAU) {
        onPath++;
        flush();
      } else run.push([x, y]);
      for (let i = 0; i < goalSamples.length; i++) {
        if (!covered[i] && Math.abs(goalSamples[i].x - x) <= TAU && Math.abs(goalSamples[i].y - y) <= TAU && Math.hypot(goalSamples[i].x - x, goalSamples[i].y - y) <= TAU) covered[i] = 1;
      }
    }
    flush();
    let c = 0;
    for (let i = 0; i < covered.length; i++) c += covered[i];
    curve.push([k + 1, Number((c / goalSamples.length).toFixed(4))]);
  });

  const coverage = curve[curve.length - 1][1];
  const precision = total ? onPath / total : 0;
  const perCurve = curves.map((_, k) => {
    let c = 0;
    let t = 0;
    goalSamples.forEach((g, i) => {
      if (g.curve === k) {
        t++;
        c += covered[i];
      }
    });
    return t ? c / t : 0;
  });
  const curvesDone = perCurve.filter((v) => v >= 0.9).length;
  const numCurves = curves.length;

  // dot relations for dots in covered regions
  let dotChecked = 0;
  let dotOk = 0;
  let firstDotError: KolamDot | null = null;
  for (const dot of dots) {
    let near = Infinity;
    for (const [x, y] of allPts) near = Math.min(near, Math.hypot(x - dot.x, y - dot.y));
    if (near > 3 * TAU * 3) continue; // region not drawn
    dotChecked++;
    const rel = near <= TAU ? 'on_line' : 'enclosed';
    if (rel === dot.relation) dotOk++;
    else if (!firstDotError) firstDotError = dot;
  }
  const dotAcc = dotChecked ? dotOk / dotChecked : 0;
  const lifts = Math.max(0, trace.strokes.length - 1);

  const outcomes: Record<string, CriterionOutcome> = {
    'CRIT-KOLAM-COVERAGE': { status: band(coverage, 0.9, 0.7), finding: `coverage ${coverage.toFixed(2)} of the goal skeleton within τ=${TAU}px` },
    'CRIT-KOLAM-PRECISION': {
      status: band(precision, 0.92, 0.8),
      finding: `precision ${precision.toFixed(2)}; ${events.length} off-path segment(s)`,
      evidence: events[0]?.evidence,
    },
    'CRIT-KOLAM-DOTS': dotChecked
      ? { status: band(dotAcc, 0.95, 0.8), finding: `dot relations ${dotOk}/${dotChecked} correct in drawn regions` }
      : { status: 'uncertain', finding: 'No drawn region near any dot.', deviation: 'no dots in covered regions' },
    'CRIT-KOLAM-CURVES': {
      status: curvesDone === numCurves ? 'satisfied' : curvesDone === numCurves - 1 ? 'partially_satisfied' : 'not_satisfied',
      finding: `${curvesDone}/${numCurves} curves completed (coverage ≥ 0.9 each)`,
    },
    'CRIT-KOLAM-CONTINUITY': {
      status: lifts <= numCurves + 1 ? 'satisfied' : lifts <= 2 * numCurves ? 'partially_satisfied' : 'not_satisfied',
      finding: `${lifts} pen lifts for K=${numCurves} curves`,
    },
  };

  const evaluation = buildEvaluation(view.rubric, `att.mock.${sessionId}.${n}`, outcomes, 'deterministic', n);
  const metrics: Record<string, MetricView> = {
    coverage: { value: coverage, finding: outcomes['CRIT-KOLAM-COVERAGE'].finding },
    precision: { value: precision, finding: outcomes['CRIT-KOLAM-PRECISION'].finding },
    dot_relations: { value: dotChecked ? dotAcc : null, finding: outcomes['CRIT-KOLAM-DOTS'].finding, uncertain_reason: dotChecked ? null : 'no dots in covered regions' },
    curves_completed: { value: curvesDone, finding: outcomes['CRIT-KOLAM-CURVES'].finding },
    pen_lifts: { value: lifts, finding: outcomes['CRIT-KOLAM-CONTINUITY'].finding },
    order: { value: null, finding: 'Curve order is reported, not scored: the image does not establish the original order.', uncertain_reason: 'order not source-established' },
  };

  let first = null;
  const firstEvent = events[0] as (DivergenceEvent & { _box?: number[] }) | undefined;
  if (firstEvent) {
    const b = firstEvent._box ?? [0, 0, 20, 20];
    first = buildFirstDivergence(view, evaluation, 'CRIT-KOLAM-PRECISION', firstEvent.position, 'stroke', firstEvent.evidence, ev(pct(b[0] - 20, b[1] - 20, b[2] + 40, b[3] + 40), 'observed', 0.9, 'goal pattern in this region'), firstEvent.detail);
  } else if (firstDotError) {
    first = buildFirstDivergence(view, evaluation, 'CRIT-KOLAM-DOTS', null, 'stroke', null, ev(pct(firstDotError.x - 25, firstDotError.y - 25, 50, 50), 'observed', 0.8), `Dot at (${Math.round(firstDotError.x)}, ${Math.round(firstDotError.y)}) should be ${firstDotError.relation === 'on_line' ? 'on the line' : 'enclosed'}.`);
  } else {
    const missing = perCurve.findIndex((v) => v < 0.9);
    if (missing >= 0) {
      first = buildFirstDivergence(view, evaluation, 'CRIT-KOLAM-COVERAGE', null, 'stroke', null, ev(curveBox(missing), 'inferred', 0.45, `suggested curve ${missing + 1}`), `Curve ${missing + 1} of ${numCurves} is ${Math.round(perCurve[missing] * 100)}% drawn.`);
    }
  }
  for (const e of events) delete (e as DivergenceEvent & { _box?: number[] })._box;

  return assembleResult({
    view,
    attempt: buildAttempt(view, sessionId, learner, n, 'trace', sourceId),
    evaluation,
    trajectory: {
      curve,
      curve_kind: 'stroke',
      events,
      process_observable: true,
      artifacts: { off_path_strokes: Array.from(new Set(events.map((e) => e.position - 1))), per_curve_coverage: perCurve },
      final_state: { coverage, precision, curves_completed: curvesDone },
    },
    metrics,
    first,
    expertRefFor: (cid) => {
      if (cid === 'CRIT-KOLAM-DOTS') return ev(pct(W / 2 - 60, H / 2 - 60, 120, 120), 'observed', 0.8);
      return ev(curveBox(Math.max(0, perCurve.findIndex((v) => v < 0.9))), 'inferred', 0.45, 'suggested curve');
    },
    runtimeClass: 'DETERMINISTIC',
  });
}

export function evaluateKolamImage(view: CaseView, sessionId: string, learner: string, n: number): AttemptResult {
  const sourceId = `upload.mock${n}`;
  const better = n > 1;
  const coverage = better ? 0.93 : 0.78;
  const precision = better ? 0.94 : 0.86;
  const outcomes: Record<string, CriterionOutcome> = {
    'CRIT-KOLAM-COVERAGE': { status: band(coverage, 0.9, 0.7), finding: `coverage ${coverage} after similarity registration to the goal` },
    'CRIT-KOLAM-PRECISION': { status: band(precision, 0.92, 0.8), finding: `precision ${precision}` },
    'CRIT-KOLAM-DOTS': { status: better ? 'satisfied' : 'partially_satisfied', finding: better ? 'dot relations 24/25' : 'dot relations 21/25' },
    'CRIT-KOLAM-CURVES': { status: 'uncertain', finding: 'Curve continuity cannot be separated in a final photo.', deviation: 'process not observable from a final photo' },
    'CRIT-KOLAM-CONTINUITY': { status: 'uncertain', finding: 'Pen lifts are not visible in a final photo.', deviation: 'process not observable from a final photo' },
  };
  const evaluation = buildEvaluation(view.rubric, `att.mock.${sessionId}.${n}`, outcomes, 'deterministic', n);
  const region = ev(pct(300, 120, 140, 140), 'observed', 0.85, 'goal region');
  const first = better ? null : buildFirstDivergence(view, evaluation, 'CRIT-KOLAM-COVERAGE', null, 'stroke', evidence(`${sourceId}#xywh=percent:60.00,24.00,28.00,28.00`, 'image', 'observed', 0.8), region, 'Upper-right loop is missing about a third of its arc.');
  return assembleResult({
    view,
    attempt: buildAttempt(view, sessionId, learner, n, 'image', sourceId),
    evaluation,
    trajectory: { curve: [[0, 0], [1, coverage]], curve_kind: 'stroke', events: [], process_observable: false, artifacts: { registration: { scale: 0.97, rotation_deg: 3.5 } }, final_state: { coverage, precision } },
    metrics: {
      coverage: { value: coverage, finding: outcomes['CRIT-KOLAM-COVERAGE'].finding },
      precision: { value: precision, finding: outcomes['CRIT-KOLAM-PRECISION'].finding },
      pen_lifts: { value: null, finding: 'not observable', uncertain_reason: 'process not observable from a final photo' },
    },
    first,
    expertRefFor: () => region,
    runtimeClass: 'DETERMINISTIC',
    warnings: ['Photo input: only the final state is observable; process criteria are UNCERTAIN.'],
  });
}
