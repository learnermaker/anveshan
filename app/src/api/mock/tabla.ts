/**
 * MOCK DATA (SYNTHETIC) — Tabla hero case.
 * A 16-beat cycle (two cycles) at 80 BPM with a theka-like bass pattern. The "expert audio" is a
 * click/bass track SYNTHESISED in the browser from these beats; it is not a recording of anyone.
 */

import type { AttemptResult, CaseView, DivergenceEvent, TablaAlignmentRow, TablaBeat, TablaUiView } from '../types';
import { assembleResult, buildAttempt, buildEvaluation, buildFirstDivergence, evidence, type CriterionOutcome } from './builders';

export const TABLA_SOURCE = 'src.tabla.synthetic.v1';

const PERIOD = 0.75;
const OFFSET = 0.5;
// Dha Dhin Dhin Dha | Dha Dhin Dhin Dha | Dha Tin Tin Ta | Ta Dhin Dhin Dha
const BASS16 = [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1];

const beats: TablaBeat[] = Array.from({ length: 32 }, (_, i) => ({
  i,                                                    // real service field name
  t: Number((OFFSET + i * PERIOD).toFixed(3)),          // real service field name
  bass: BASS16[i % 16] === 1,
  strength: i % 16 === 0 ? 1 : 0.7,
  // Legacy aliases for backward compat during transition
  index: i,
  time_sec: Number((OFFSET + i * PERIOD).toFixed(3)),
}));

export const tablaUiView: TablaUiView = {
  beats,
  stroke_pulse_sec: PERIOD,    // real service field name
  period_sec: PERIOD,          // legacy alias
  tempo_bpm: 80,
  cycle_length_pulses: 16,     // real service field name
  cycle_length_beats: 16,
  cycle_length: 16,            // legacy alias
  duration_sec: OFFSET + 32 * PERIOD + 0.5,
  // Real service: no source_id in ui_view; mock keeps it for URL lookup
  source_id: TABLA_SOURCE,
};

let wavUrl: string | null = null;

/** Synthesise a 16 kHz mono WAV of the beat pattern (bass = low decaying tone + click). */
export function tablaAudioUrl(): string {
  if (wavUrl) return wavUrl;
  const sr = 16000;
  const n = Math.ceil((tablaUiView.duration_sec ?? 25) * sr);
  const data = new Float32Array(n);
  for (const b of beats) {
    const bt = b.t ?? b.time_sec ?? 0;
    const start = Math.floor(bt * sr);
    for (let i = 0; i < sr * 0.35 && start + i < n; i++) {
      const t = i / sr;
      let v = 0.45 * Math.sin(2 * Math.PI * 2100 * t) * Math.exp(-t * 60) + 0.2 * Math.sin(2 * Math.PI * 520 * t) * Math.exp(-t * 25);
      if (b.bass) v += 0.6 * Math.sin(2 * Math.PI * (95 - 20 * t) * t) * Math.exp(-t * 7);
      data[start + i] += v * (b.strength ?? 0.7);
    }
  }
  const buf = new ArrayBuffer(44 + n * 2);
  const dv = new DataView(buf);
  const w = (o: number, s: string) => [...s].forEach((c, i) => dv.setUint8(o + i, c.charCodeAt(0)));
  w(0, 'RIFF');
  dv.setUint32(4, 36 + n * 2, true);
  w(8, 'WAVE');
  w(12, 'fmt ');
  dv.setUint32(16, 16, true);
  dv.setUint16(20, 1, true);
  dv.setUint16(22, 1, true);
  dv.setUint32(24, sr, true);
  dv.setUint32(28, sr * 2, true);
  dv.setUint16(32, 2, true);
  dv.setUint16(34, 16, true);
  w(36, 'data');
  dv.setUint32(40, n * 2, true);
  for (let i = 0; i < n; i++) dv.setInt16(44 + i * 2, Math.max(-1, Math.min(1, data[i])) * 0x7fff, true);
  wavUrl = URL.createObjectURL(new Blob([buf], { type: 'audio/wav' }));
  return wavUrl;
}

const aev = (start: number, end: number, cue: string, idx?: string) =>
  evidence(`${TABLA_SOURCE}${idx ? `#onset=${idx}` : ''}`, 'audio', 'observed', 0.9, { start_sec: start, end_sec: end, cue_excerpt: cue });

export function tablaCaseView(caseId = 'tabla', extra: Partial<CaseView> = {}): CaseView {
  const cycleEnd = OFFSET + 16 * PERIOD;
  return {
    case_id: caseId,
    title: 'Tabla — 16-beat theka (audio; video optional)',
    modality: 'tabla_audio',
    hero: true,
    runtime_label: 'SYNTHETIC',
    review_status: 'pending',
    derived_from: null,
    warnings: ['MOCK DATA: expert audio is synthesised in the browser; bol names are UNVERIFIED (audio model off).'],
    sources: [
      {
        source_id: TABLA_SOURCE,
        role: 'expert_audio',
        mime_type: 'audio/wav',
        sha256: 'mock-synthesised-in-browser',
        bytes: 0,
        duration_sec: tablaUiView.duration_sec,
        creator: 'Anveshan mock generator',
        license: 'SYNTHETIC (no rights issue)',
        attribution: 'Synthesised click/bass track for offline UI work',
        runtime_label: 'SYNTHETIC',
        used_by_system: true,
      },
    ],
    goal: {
      case_id: caseId,
      version: 1,
      modality: 'tabla_audio',
      source_ids: [TABLA_SOURCE],
      package_id: 'kp.tabla.v1',
      built_with: { onsets: 'spectral_flux', bass_threshold: '2-means', low_band_hz: 250 },
      warnings: ['Bol identity not available: audio model disabled.'],
      ui_view: tablaUiView,
    },
    package: {
      package_id: 'kp.tabla.v1',
      skill_id: 'skill.tabla.theka16',
      title: '16-beat theka — tempo, cycle and bass pattern',
      summary: 'Onsets, tempo, cycle length and bass (bayan) pattern computed from the audio. Bol names are UNVERIFIED.',
      claims: [
        { claim_id: 'CLM-TABLA-001', claim_type: 'condition', statement: 'Tempo is 80 BPM (beat period 0.75 s, IOI histogram peak).', is_observed: true, evidence_refs: [aev(OFFSET, cycleEnd, 'IOI median 750 ms')] },
        { claim_id: 'CLM-TABLA-002', claim_type: 'condition', statement: 'The bass pattern repeats every 16 beats (autocorrelation peak at 16).', is_observed: true, evidence_refs: [aev(OFFSET, OFFSET + 32 * PERIOD, 'two full cycles')] },
        { claim_id: 'CLM-TABLA-003', claim_type: 'step', statement: 'Bass (bayan) is withheld on beats 10–13 of each cycle (the empty section) and played on all other beats.', is_observed: true, evidence_refs: [aev(OFFSET + 9 * PERIOD, OFFSET + 13 * PERIOD, 'low-band ratio drops below threshold', '9-12')] },
        { claim_id: 'CLM-TABLA-004', claim_type: 'cue', statement: 'Beat 1 of each cycle is the strongest stroke (onset strength peak).', is_observed: true, evidence_refs: [aev(OFFSET, OFFSET + 0.2, 'strength 1.0', '0')] },
        { claim_id: 'CLM-TABLA-005', claim_type: 'step', statement: 'Bols may be “Dha Dhin Dhin Dha | Dha Dhin Dhin Dha | Dha Tin Tin Ta | Ta Dhin Dhin Dha” — UNVERIFIED (external reference only; no audio model).', is_observed: false, evidence_refs: [] },
      ],
      consent: { contributor_name: 'SYNTHETIC generator', consent_scope: 'synthetic_no_person', revocable: false },
      expert_review: { reviewer_name: 'unassigned', status: 'pending' },
    },
    rubric: {
      rubric_id: 'rubric.tabla.v1',
      skill_id: 'skill.tabla.theka16',
      title: 'Tabla goal-trajectory rubric',
      criteria: [
        { criterion_id: 'CRIT-TABLA-TEMPO', name: 'Holds the source tempo', description: 'Tempo error.', observable_indicator: '≤ 5%', weight: 2, required: true },
        { criterion_id: 'CRIT-TABLA-TIMING', name: 'Strokes land on the beat grid', description: 'Median deviation after fit.', observable_indicator: 'median ≤ 50 ms', weight: 3, required: true },
        { criterion_id: 'CRIT-TABLA-BAYAN', name: 'Bass used and withheld where the source does', description: 'Bass-pattern accuracy.', observable_indicator: '≥ 0.9', weight: 3, required: true },
        { criterion_id: 'CRIT-TABLA-COMPLETE', name: 'No missing / extra strokes', description: 'Missing + extra.', observable_indicator: '≤ 1', weight: 1, required: false },
        { criterion_id: 'CRIT-TABLA-STEADY', name: 'Steady pulse', description: 'IOI CV.', observable_indicator: 'CV ≤ 0.08', weight: 1, required: false },
      ],
      passing_score: 7,
    },
    task: {
      task_id: 'task.tabla.v1',
      package_id: 'kp.tabla.v1',
      rubric_id: 'rubric.tabla.v1',
      title: 'Play two cycles of the 16-beat theka',
      instructions: 'Record two cycles at about 80 BPM (CLM-TABLA-001). Use the bass on every beat except 10–13 (CLM-TABLA-003). Upload the audio; a video is optional and is shown but not scored.',
      constraints: [
        { constraint_type: 'input', description: 'Audio upload (any container). Optional video is not scored.' },
      ],
      target_criteria_ids: ['CRIT-TABLA-TEMPO', 'CRIT-TABLA-TIMING', 'CRIT-TABLA-BAYAN', 'CRIT-TABLA-COMPLETE', 'CRIT-TABLA-STEADY'],
    },
    criterion_map: {
      rubric_id: 'rubric.tabla.v1',
      package_id: 'kp.tabla.v1',
      criteria: {
        'CRIT-TABLA-TEMPO': { order_index: 0, source_claim_ids: ['CLM-TABLA-001'], reference_evidence_ids: [], why_it_matters: 'The cycle only lines up at the source tempo (CLM-TABLA-001).', drill_hint: 'Count 1-2-3-4 at 80 BPM before starting.' },
        'CRIT-TABLA-TIMING': { order_index: 1, source_claim_ids: ['CLM-TABLA-001'], reference_evidence_ids: [], why_it_matters: 'Strokes off the grid blur the theka (CLM-TABLA-001).', drill_hint: 'Play beats 1–8 slowly against a click, then the full cycle.' },
        'CRIT-TABLA-BAYAN': { order_index: 2, source_claim_ids: ['CLM-TABLA-003'], reference_evidence_ids: [], why_it_matters: 'Withholding the bass on beats 10–13 marks the empty section of the cycle (CLM-TABLA-003).', drill_hint: 'Play beats 9–14 only: lift the left hand off the bayan on 10–13, return on 14.' },
        'CRIT-TABLA-COMPLETE': { order_index: 3, source_claim_ids: ['CLM-TABLA-002'], reference_evidence_ids: [], why_it_matters: 'A missing stroke shifts the 16-beat cycle (CLM-TABLA-002).', drill_hint: 'Say the beat numbers aloud for one cycle.' },
        'CRIT-TABLA-STEADY': { order_index: 4, source_claim_ids: ['CLM-TABLA-001'], reference_evidence_ids: [], why_it_matters: 'A steady pulse keeps the cycle recognisable (CLM-TABLA-001).', drill_hint: 'Keep the right-hand strokes even before adding the bass.' },
      },
    },
    ...extra,
  };
}

export function evaluateTabla(view: CaseView, sessionId: string, learner: string, n: number, hasVideo: boolean): AttemptResult {
  const sourceId = `src.attempt.${view.case_id}.${sessionId}.${n}`;
  const retry = n > 1;
  const rows: TablaAlignmentRow[] = [];
  const events: DivergenceEvent[] = [];
  let correct = 0;
  const curve: number[][] = [[0, 0]];
  beats.forEach((b, i) => {
    let dev = Math.round(Math.sin(i * 1.7) * (retry ? 14 : 28));
    let status: string = 'ok';
    let bassPlayed: boolean | null = b.bass;
    if (!retry) {
      if (i === 5) { dev = 124; status = 'late'; }
      if (i === 9 || i === 10) bassPlayed = true; // bass in the empty section
      if (i === 25 || i === 26) bassPlayed = true;
      if (i === 20) { status = 'missing'; bassPlayed = null; }
    }
    const bt = b.t ?? b.time_sec ?? 0;
    const learnerT = status === 'missing' ? null : Number((bt + dev / 1000).toFixed(3));
    rows.push({
      // Real service field names
      goal: i, goal_t: bt, learner_t: learnerT,
      dev_ms: status === 'missing' ? null : dev,
      bass_goal: b.bass, bass_learner: bassPlayed,
      bass_ok: bassPlayed === b.bass,
      on_time: status === 'ok',
      // Legacy aliases
      goal_index: i, goal_time_sec: bt, learner_time_sec: learnerT,
      deviation_ms: status === 'missing' ? null : dev,
      status, bass_expected: b.bass, bass_played: bassPlayed,
    });
    const ok = status === 'ok' && bassPlayed === b.bass;
    if (ok) correct++;
    curve.push([i + 1, Number((correct / beats.length).toFixed(4))]);
    const ev = (kind: string, detail: string, metric: string) =>
      events.push({ metric, kind, position: learnerT ?? bt, position_kind: 'time', evidence: evidence(`${sourceId}#onset=${i}`, 'audio', 'observed', 0.9, { start_sec: learnerT ?? bt, end_sec: (learnerT ?? bt) + 0.2 }), detail, severity: 'material' });
    if (status === 'late') ev('late_stroke', `Beat ${i + 1} is ${dev} ms late (tolerance 50 ms).`, 'timing');
    if (status === 'missing') ev('missing_stroke', `Beat ${i + 1} has no matching stroke.`, 'complete');
    if (status === 'ok' && bassPlayed !== b.bass) ev('bass_mismatch', `Beat ${(i % 16) + 1} of the cycle: bass played where the source withholds it.`, 'bayan');
  });
  if (!retry) {
    rows.splice(14, 0, {
      goal: null, goal_t: null, learner_t: 11.21, dev_ms: null, on_time: false,
      bass_goal: null, bass_learner: false, bass_ok: null,
      goal_index: null, goal_time_sec: null, learner_time_sec: 11.21, deviation_ms: null,
      status: 'extra', bass_expected: null, bass_played: false,
    });
  }
  const bassAcc = retry ? 1 : 27 / 31;
  const outcomes: Record<string, CriterionOutcome> = retry
    ? {
        'CRIT-TABLA-TEMPO': { status: 'satisfied', finding: 'tempo 81.2 BPM (error 1.5%)' },
        'CRIT-TABLA-TIMING': { status: 'satisfied', finding: 'median deviation 11 ms, worst 14 ms' },
        'CRIT-TABLA-BAYAN': { status: 'satisfied', finding: 'bass pattern 32/32' },
        'CRIT-TABLA-COMPLETE': { status: 'satisfied', finding: '0 missing, 0 extra' },
        'CRIT-TABLA-STEADY': { status: 'satisfied', finding: 'IOI CV 0.03' },
      }
    : {
        'CRIT-TABLA-TEMPO': { status: 'satisfied', finding: 'tempo 77.9 BPM (error 2.6%)' },
        'CRIT-TABLA-TIMING': { status: 'partially_satisfied', finding: 'median deviation 58 ms, worst 124 ms (beat 6)', evidence: events.find((e) => e.kind === 'late_stroke')?.evidence },
        'CRIT-TABLA-BAYAN': { status: 'partially_satisfied', finding: `bass pattern ${Math.round(bassAcc * 31)}/31 matched; bass played on beats 10–11 of both cycles`, evidence: events.find((e) => e.kind === 'bass_mismatch')?.evidence },
        'CRIT-TABLA-COMPLETE': { status: 'partially_satisfied', finding: '1 missing (beat 21), 1 extra stroke' },
        'CRIT-TABLA-STEADY': { status: 'partially_satisfied', finding: 'IOI CV 0.11' },
      };
  const evaluation = buildEvaluation(view.rubric, `att.mock.${sessionId}.${n}`, outcomes, 'deterministic', n);
  events.sort((a, b) => a.position - b.position);
  const fe = events[0];
  const first = fe
    ? buildFirstDivergence(view, evaluation, fe.metric === 'timing' ? 'CRIT-TABLA-TIMING' : fe.metric === 'bayan' ? 'CRIT-TABLA-BAYAN' : 'CRIT-TABLA-COMPLETE', fe.position, 'time', fe.evidence, aev(fe.position, fe.position + 0.3, `source at ${fe.position.toFixed(2)}s`), fe.detail)
    : null;
  return assembleResult({
    view,
    attempt: buildAttempt(view, sessionId, learner, n, 'audio', sourceId),
    evaluation,
    trajectory: { curve, curve_kind: 'beat', events, process_observable: true, artifacts: { alignment: rows }, final_state: { matched: correct, total: beats.length } },
    metrics: {
      tempo_error: { value: retry ? 0.015 : 0.026, finding: outcomes['CRIT-TABLA-TEMPO'].finding },
      median_deviation_ms: { value: retry ? 11 : 58, finding: outcomes['CRIT-TABLA-TIMING'].finding },
      bass_accuracy: { value: bassAcc, finding: outcomes['CRIT-TABLA-BAYAN'].finding },
      bols: { value: null, finding: 'Bol identity not assessed.', uncertain_reason: 'audio model disabled' },
    },
    first,
    expertRefFor: (cid) => (cid === 'CRIT-TABLA-BAYAN' ? aev(OFFSET + 9 * PERIOD, OFFSET + 13 * PERIOD, 'empty section: no bass', '9-12') : aev(OFFSET, OFFSET + 16 * PERIOD, 'one source cycle')),
    runtimeClass: 'DETERMINISTIC',
    warnings: hasVideo ? ['Optional video received: displayed only, not scored.'] : [],
  });
}
