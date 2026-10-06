/**
 * MOCK DATA builders (SYNTHETIC). Used only when VITE_API_BASE === 'mock'.
 * They mimic the deterministic score policy described in docs/plans/evaluation-core.md:
 * status → score = weight × {satisfied: 1, partially_satisfied: 0.5, otherwise 0}.
 * Nothing here is evidence about any real learner or expert.
 */

import type {
  CriterionResult,
  CriterionStatus,
  Evaluation,
  EvidenceRef,
  Feedback,
  FeedbackItem,
  LearnerAttempt,
  RubricDefinition,
  TransmissionRecord,
} from '../../types/contracts';
import type {
  AttemptKind,
  AttemptResult,
  CaseView,
  DivergenceEvent,
  FirstDivergence,
  MetricView,
  RuntimeClass,
  SessionResult,
  Trajectory,
} from '../types';

export const MOCK_WARNING = 'MOCK DATA: canned SYNTHETIC response generated in the browser; no service or model was called.';

export function scoreFor(status: CriterionStatus, weight: number): number {
  if (status === 'satisfied') return weight;
  if (status === 'partially_satisfied') return weight * 0.5;
  return 0;
}

export interface CriterionOutcome {
  status: CriterionStatus;
  finding: string;
  deviation?: string;
  evidence?: EvidenceRef;
}

export function buildEvaluation(
  rubric: RubricDefinition,
  attemptId: string,
  outcomes: Record<string, CriterionOutcome>,
  evaluatorType: Evaluation['evaluator_type'],
  seq: number,
): Evaluation {
  const results: CriterionResult[] = rubric.criteria.map((c) => {
    const o = outcomes[c.criterion_id] ?? { status: 'uncertain' as const, finding: 'Not evaluated.' };
    const r: CriterionResult = {
      criterion_id: c.criterion_id,
      status: o.status,
      score: Number(scoreFor(o.status, c.weight).toFixed(3)),
      observed_finding: o.finding,
    };
    if (o.deviation) r.deviation_analysis = o.deviation;
    if (o.evidence) r.evidence_ref = o.evidence;
    return r;
  });
  const total = Number(results.reduce((s, r) => s + r.score, 0).toFixed(3));
  const passed = rubric.criteria.every((c) => !c.required || outcomes[c.criterion_id]?.status === 'satisfied');
  return {
    evaluation_id: `eval.mock.${attemptId}.${seq}`,
    attempt_id: attemptId,
    rubric_id: rubric.rubric_id,
    criterion_results: results,
    total_score: total,
    passed,
    evaluator_type: evaluatorType,
    uncertainty_flags: results
      .filter((r) => r.status === 'uncertain')
      .map((r) => `${r.criterion_id}: ${r.deviation_analysis ?? 'evidence insufficient'}`),
    evaluated_at: new Date().toISOString(),
  };
}

export function buildAttempt(
  view: CaseView,
  sessionId: string,
  learnerName: string,
  n: number,
  kind: AttemptKind,
  sourceId: string,
): LearnerAttempt {
  const modality = kind === 'trace' || kind === 'image' ? 'image' : kind === 'audio' ? 'audio' : 'video';
  return {
    attempt_id: `att.mock.${sessionId}.${n}`,
    task_id: view.task.task_id,
    learner: { participant_id: `learner.mock.${sessionId}`, name: learnerName, role: 'learner', notes: 'SYNTHETIC mock session' },
    attempt_type: n === 1 ? 'baseline' : 'retry',
    attempt_number: n,
    submitted_at: new Date().toISOString(),
    evidence: {
      evidence_id: `ev.${sourceId}`,
      source_id: sourceId,
      modality,
      verification_state: 'observed',
      confidence: 1,
    },
  };
}

export function buildFeedback(
  view: CaseView,
  evaluation: Evaluation,
  attemptId: string,
  first: FirstDivergence | null,
  expertRefFor: (criterionId: string) => EvidenceRef | undefined,
): Feedback | null {
  const nonSat = evaluation.criterion_results.filter((r) => r.status !== 'satisfied');
  if (!nonSat.length) return null;
  const ordered = first ? [...nonSat].sort((a, b) => (a.criterion_id === first.criterion_id ? -1 : b.criterion_id === first.criterion_id ? 1 : 0)) : nonSat;
  const items: FeedbackItem[] = ordered.map((r) => {
    const map = view.criterion_map?.criteria[r.criterion_id];
    const crit = view.rubric.criteria.find((c) => c.criterion_id === r.criterion_id);
    const item: FeedbackItem = {
      criterion_id: r.criterion_id,
      what_was_observed: r.observed_finding,
      what_differed:
        r.status === 'uncertain'
          ? `Not assessable from this evidence: ${r.deviation_analysis ?? 'insufficient evidence'}.`
          : `${crit?.name ?? r.criterion_id}: ${r.deviation_analysis ?? 'below the source band'}. ${map?.why_it_matters ?? ''}`.trim(),
      corrective_advice: map?.drill_hint ?? 'Repeat the full task, watching the referenced source evidence.',
    };
    const ex = expertRefFor(r.criterion_id);
    if (ex) item.expert_evidence_ref = ex;
    if (r.evidence_ref) item.learner_evidence_ref = r.evidence_ref;
    return item;
  });
  return {
    feedback_id: `fb.mock.${attemptId}`,
    evaluation_id: evaluation.evaluation_id,
    attempt_id: attemptId,
    summary: first
      ? `Start with ${first.criterion_name}: ${first.observed_finding}`
      : `${items.length} criteria below the source bands.`,
    items,
    recommended_retry_focus: items.slice(0, 2).map((i) => i.criterion_id),
  };
}

export function buildFirstDivergence(
  view: CaseView,
  evaluation: Evaluation,
  criterionId: string,
  position: number | null,
  positionKind: string,
  learnerEvidence: EvidenceRef | null,
  expertEvidence: EvidenceRef | null,
  finding: string,
): FirstDivergence {
  const crit = view.rubric.criteria.find((c) => c.criterion_id === criterionId);
  const map = view.criterion_map?.criteria[criterionId];
  const status = evaluation.criterion_results.find((r) => r.criterion_id === criterionId)?.status ?? 'not_satisfied';
  return {
    criterion_id: criterionId,
    criterion_name: crit?.name ?? criterionId,
    status,
    position,
    position_kind: positionKind,
    learner_evidence: learnerEvidence,
    expert_evidence: expertEvidence,
    observed_finding: finding,
    why_it_matters: map?.why_it_matters ?? '',
    source_claim_ids: map?.source_claim_ids ?? [],
    drill_hint: map?.drill_hint ?? '',
  };
}

export function assembleResult(args: {
  view: CaseView;
  attempt: LearnerAttempt;
  evaluation: Evaluation;
  trajectory: Trajectory;
  metrics: Record<string, MetricView>;
  first: FirstDivergence | null;
  expertRefFor: (criterionId: string) => EvidenceRef | undefined;
  runtimeClass: RuntimeClass;
  warnings?: string[];
}): AttemptResult {
  const { view, attempt, evaluation, first } = args;
  const feedback = buildFeedback(view, evaluation, attempt.attempt_id, first, args.expertRefFor);
  const drillCrit = first?.criterion_id ?? feedback?.items[0]?.criterion_id;
  const map = drillCrit ? view.criterion_map?.criteria[drillCrit] : undefined;
  return {
    attempt,
    evaluation,
    trajectory: args.trajectory,
    metrics: args.metrics,
    first_divergence: first,
    feedback,
    drill: drillCrit
      ? {
          criterion_id: drillCrit,
          title: `Drill: ${view.rubric.criteria.find((c) => c.criterion_id === drillCrit)?.name ?? drillCrit}`,
          instructions: map?.drill_hint ?? 'Practise the referenced segment on its own, then repeat the full task.',
          drill_hint: map?.drill_hint,
          source_claim_ids: map?.source_claim_ids ?? [],
          reference_evidence: args.expertRefFor(drillCrit) ?? null,
        }
      : null,
    runtime_class: args.runtimeClass,
    warnings: [MOCK_WARNING, ...(args.warnings ?? [])],
    run_keys: [],
  };
}

const RANK: Record<CriterionStatus, number> = { not_satisfied: 0, partially_satisfied: 1, satisfied: 2, uncertain: -1 };

function transitionKind(a: CriterionStatus | undefined, b: CriterionStatus | undefined): string {
  if (!a || !b) return 'unchanged';
  if (a === 'uncertain' && b !== 'uncertain') return 'observability_gain';   // real service name
  if (a !== 'uncertain' && b === 'uncertain') return 'observability_loss';   // real service name
  if (RANK[b] > RANK[a]) return 'improved';
  if (RANK[b] < RANK[a]) return 'regressed';
  return 'unchanged';
}

async function sha256Hex(text: string): Promise<string> {
  try {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  } catch {
    let h = 0;
    for (let i = 0; i < text.length; i++) h = (Math.imul(31, h) + text.charCodeAt(i)) | 0;
    return `fallback-${(h >>> 0).toString(16)}`;
  }
}

export async function buildSessionResult(view: CaseView, sessionId: string, baseline: AttemptResult, retry: AttemptResult): Promise<SessionResult> {
  const b = baseline.evaluation;
  const r = retry.evaluation;
  const transitions: Record<string, string> = {};
  let skillGain = 0;
  const improved: string[] = [];
  for (const c of view.rubric.criteria) {
    const bs = b.criterion_results.find((x) => x.criterion_id === c.criterion_id);
    const rs = r.criterion_results.find((x) => x.criterion_id === c.criterion_id);
    const kind = transitionKind(bs?.status, rs?.status);
    transitions[c.criterion_id] = kind;
    if (kind === 'improved') improved.push(c.criterion_id);
    if (bs && rs && bs.status !== 'uncertain' && rs.status !== 'uncertain') skillGain += rs.score - bs.score;
  }
  const targetId = baseline.first_divergence?.criterion_id ?? null;
  const tb = targetId ? b.criterion_results.find((x) => x.criterion_id === targetId)?.status ?? null : null;
  const tr = targetId ? r.criterion_results.find((x) => x.criterion_id === targetId)?.status ?? null : null;
  const recordedAt = new Date().toISOString();
  const core = {
    package_id: view.package.package_id,
    rubric_id: view.rubric.rubric_id,
    baseline: baseline.attempt.attempt_id,
    retry: retry.attempt.attempt_id,
    baseline_score: b.total_score,
    retry_score: r.total_score,
  };
  const record: TransmissionRecord = {
    transmission_id: `tx.mock.${sessionId}`,
    skill_id: view.package.skill_id,
    package_id: view.package.package_id,
    rubric_id: view.rubric.rubric_id,
    expert_id: view.package.consent.contributor_name,
    learner_id: baseline.attempt.learner.participant_id,
    baseline_attempt_id: baseline.attempt.attempt_id,
    retry_attempt_id: retry.attempt.attempt_id,
    baseline_score: b.total_score,
    retry_score: r.total_score,
    transmission_gain: Number((r.total_score - b.total_score).toFixed(3)),
    criteria_improved: improved,
    lineage: {
      parent_transmission_id: null,
      recorded_at: recordedAt,
      provenance_hash: `sha256:${await sha256Hex(JSON.stringify(core))}`,
      adaptation_notes: 'MOCK DATA (SYNTHETIC): computed in the browser mock; not a real transmission event.',
    },
  };
  return {
    bundle: {
      case_id: view.case_id,
      knowledge_package: view.package,
      rubric: view.rubric,
      practice_task: view.task,
      baseline_attempt: baseline.attempt,
      baseline_evaluation: b,
      feedback: baseline.feedback,
      retry_attempt: retry.attempt,
      retry_evaluation: r,
      transmission_record: record,
    },
    transmission_record: record,
    comparison: {
      transitions,
      targeted_change: {
        criterion_id: targetId,
        // Real service field names
        before: tb,
        after: tr,
        improved: targetId ? (RANK[tr!] > RANK[tb!]) : false,
        changed: tb !== tr,
        // Legacy aliases (kept for any existing code paths)
        baseline_status: tb,
        retry_status: tr,
        kind: targetId ? transitionKind(tb ?? undefined, tr ?? undefined) : 'none',
      },
      skill_gain_excluding_observability: Number(skillGain.toFixed(3)),
      curves: { baseline: baseline.trajectory.curve, retry: retry.trajectory.curve },
    },
  };
}

export function evidence(sourceId: string, modality: EvidenceRef['modality'], state: EvidenceRef['verification_state'], confidence: number, extra: Partial<EvidenceRef> = {}): EvidenceRef {
  return {
    evidence_id: `ev.${sourceId.replace(/[^A-Za-z0-9.]+/g, '_')}`,
    source_id: sourceId,
    modality,
    verification_state: state,
    confidence,
    ...extra,
  };
}

export function event(e: DivergenceEvent): DivergenceEvent {
  return e;
}
