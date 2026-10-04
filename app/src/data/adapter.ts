import rawBundle from './fixtures/case_001/bundle.json';
import type {
  TransmissionBundle,
  KnowledgePackage,
  RubricDefinition,
  PracticeTask,
  LearnerAttempt,
  Evaluation,
  Feedback,
  TransmissionRecord,
  ClaimType,
  ReviewStatus,
  Modality,
  VerificationState,
  CriterionStatus,
  EvaluatorType,
  EvidenceRef,
  CriterionResult,
  FeedbackItem,
  ClaimType,
  ReviewStatus,
  Modality,
  VerificationState,
  CriterionStatus,
  EvaluatorType,
  EvidenceRef,
} from '../types/contracts';

// Type assertion for bundle
/**
 * Normalize legacy UI fixture payloads into the canonical eight-contract shape.
 *
 * Existing seven-case replay data predates the frozen Python seam. Keep that
 * fixture vocabulary at the edge only; everything consumed by the workbench
 * below is canonical. New case data must be authored in canonical shape.
 */
type LegacyEvidence = {
  evidence_id: string;
  source_id: string;
  modality?: string;
  start_sec?: number;
  end_sec?: number;
  cue_excerpt?: string;
  verification_state?: string;
  confidence?: number;
};

type LegacyBundle = any;

function normalizeModality(value: unknown): Modality {
  switch (value) {
    case 'audio': return 'audio';
    case 'image': return 'image';
    case 'text': return 'text';
    case 'sensor': return 'sensor';
    case 'video': return 'video';
    default: return 'video';
  }
}

function normalizeEvidence(input: LegacyEvidence): EvidenceRef {
  return {
    evidence_id: input.evidence_id,
    source_id: input.source_id,
    modality: normalizeModality(input.modality),
    start_sec: input.start_sec,
    end_sec: input.end_sec,
    cue_excerpt: input.cue_excerpt,
    verification_state:
      input.verification_state === 'inferred'
        ? 'inferred'
        : input.verification_state === 'unverified'
          ? 'unverified'
          : 'observed',
    confidence: typeof input.confidence === 'number' ? input.confidence : 1,
  };
}

function normalizeClaimType(value: unknown): ClaimType {
  if (value === 'cue' || value === 'condition' || value === 'exception' || value === 'failure_mode') {
    return value;
  }
  return 'step';
}

function normalizeReviewStatus(value: unknown): ReviewStatus {
  if (value === 'approved' || value === 'revised' || value === 'rejected') return value;
  return 'pending';
}

function normalizeCriterionStatus(value: unknown): CriterionStatus {
  switch (value) {
    case 'satisfied': return 'satisfied';
    case 'partial':
    case 'partially_satisfied': return 'partially_satisfied';
    case 'divergent':
    case 'not_satisfied': return 'not_satisfied';
    default: return 'uncertain';
  }
}

function normalizeEvaluatorType(value: unknown): EvaluatorType {
  if (value === 'deterministic') return 'deterministic';
  if (value === 'human_expert' || value === 'expert_human') return 'human_expert';
  return 'model_assisted';
}

export function normalizeTransmissionBundle(input: LegacyBundle): TransmissionBundle {
  const normalizeAttempt = (attempt: any): LearnerAttempt => {
    const legacyEvidence = attempt.evidence_refs?.[0] ?? attempt.evidence;
    const evidence = normalizeEvidence({
      evidence_id: legacyEvidence.evidence_id,
      source_id: legacyEvidence.source_id,
      modality: legacyEvidence.modality,
      start_sec: legacyEvidence.start_sec,
      end_sec: legacyEvidence.end_sec,
      cue_excerpt: legacyEvidence.cue_excerpt,
      verification_state: legacyEvidence.verification_state,
      confidence: legacyEvidence.confidence,
    });
    const learnerId = attempt.learner_id ?? attempt.learner?.participant_id;
    return {
      attempt_id: attempt.attempt_id,
      task_id: attempt.task_id,
      learner: attempt.learner ?? {
        participant_id: learnerId,
        name: learnerId,
        role: 'learner',
      },
      attempt_type: attempt.attempt_type,
      attempt_number: attempt.attempt_number,
      submitted_at: attempt.submitted_at ?? attempt.created_at,
      evidence,
    };
  };

  const normalizeEvaluation = (evaluation: any): Evaluation => ({
    evaluation_id: evaluation.evaluation_id,
    attempt_id: evaluation.attempt_id,
    rubric_id: evaluation.rubric_id,
    evaluator_type: normalizeEvaluatorType(evaluation.evaluator_type),
    criterion_results: evaluation.criterion_results.map((result: any) => ({
      criterion_id: result.criterion_id,
      score: result.score,
      status: normalizeCriterionStatus(result.status),
      observed_finding: result.observed_finding ?? result.observation_notes ?? '',
      deviation_analysis: result.deviation_analysis ?? result.divergence_type,
      evidence_ref: result.evidence_ref ? normalizeEvidence(result.evidence_ref) : undefined,
    })),
    total_score: evaluation.total_score,
    passed: evaluation.passed,
    uncertainty_flags: evaluation.uncertainty_flags ?? [],
    evaluated_at: evaluation.evaluated_at,
  });

  const normalizeFeedback = (feedbackInput: any): Feedback => ({
    feedback_id: feedbackInput.feedback_id,
    evaluation_id: feedbackInput.evaluation_id,
    attempt_id: feedbackInput.attempt_id,
    summary: feedbackInput.summary ?? 'Targeted corrective feedback for the next attempt.',
    items: feedbackInput.items.map((item: any) => ({
      criterion_id: item.criterion_id,
      what_was_observed: item.what_was_observed ?? item.divergence_observed ?? '',
      what_differed: item.what_differed ?? item.divergence_observed ?? '',
      corrective_advice: item.corrective_advice ?? item.corrective_instruction ?? '',
      expert_evidence_ref: item.expert_evidence_ref
        ? normalizeEvidence(item.expert_evidence_ref)
        : undefined,
      learner_evidence_ref: item.learner_evidence_ref
        ? normalizeEvidence(item.learner_evidence_ref)
        : undefined,
    })),
    recommended_retry_focus: feedbackInput.recommended_retry_focus ??
      feedbackInput.items.map((item: any) => item.criterion_id),
  });

  const kp = input.knowledge_package;
  return {
    case_id: input.case_id,
    domain: input.domain,
    skill: input.skill,
    knowledge_package: {
      package_id: kp.package_id,
      skill_id: kp.skill_id,
      title: kp.title,
      summary: kp.summary,
      claims: kp.claims.map((claim: any) => ({
        claim_id: claim.claim_id,
        claim_type: normalizeClaimType(claim.claim_type),
        statement: claim.statement,
        is_observed: claim.is_observed,
        evidence_refs: claim.evidence_refs.map((ref: LegacyEvidence) => normalizeEvidence(ref)),
      })),
      consent: kp.consent,
      expert_review: kp.expert_review
        ? {
            reviewer_name: kp.expert_review.reviewer_name,
            status: normalizeReviewStatus(kp.expert_review.status),
            reviewed_at: kp.expert_review.reviewed_at,
            notes: kp.expert_review.notes,
          }
        : undefined,
    },
    rubric: input.rubric,
    practice_task: {
      ...input.practice_task,
      constraints: input.practice_task.constraints ?? [],
      target_criteria_ids: input.practice_task.target_criteria_ids ?? [],
    },
    baseline_attempt: normalizeAttempt(input.baseline_attempt),
    baseline_evaluation: normalizeEvaluation(input.baseline_evaluation),
    feedback: normalizeFeedback(input.feedback),
    retry_attempt: normalizeAttempt(input.retry_attempt),
    retry_evaluation: normalizeEvaluation(input.retry_evaluation),
    transmission_record: input.transmission_record,
  };
}

export const canonicalBundle = normalizeTransmissionBundle(rawBundle);

export interface SensoryCueAnnotation {
  id: string;
  timeSec: number;
  label: string;
  category: 'tactile' | 'acoustic' | 'visual';
  description: string;
  waveformRegion?: { start: number; end: number };
}

export interface CriterionComparison {
  criterionId: string;
  name: string;
  weight: number;
  required: boolean;
  observableIndicator: string;
  baselineScore: number;
  baselineStatus: CriterionStatus;
  baselineNotes?: string;
  retryScore: number;
  retryStatus: CriterionStatus;
  retryNotes?: string;
  feedback?: FeedbackItem;
  expertEvidenceSec?: number;
  isFirstDivergence: boolean;
}

export interface TransmissionTelemetry {
  bundle: TransmissionBundle;
  knowledgePackage: KnowledgePackage;
  rubric: RubricDefinition;
  task: PracticeTask;
  baselineAttempt: LearnerAttempt;
  baselineEval: Evaluation;
  feedback: Feedback;
  retryAttempt: LearnerAttempt;
  retryEval: Evaluation;
  record: TransmissionRecord;
  criteriaComparisons: CriterionComparison[];
  firstDivergenceSec: number;
  firstDivergenceCriterionId: string;
  sensoryCues: SensoryCueAnnotation[];
  metrics: {
    baselineScore: number;
    retryScore: number;
    maxPossibleScore: number;
    gainPoints: number;
    gainPercentage: number;
    criteriaImprovedCount: number;
    totalCriteriaCount: number;
    rubricPassed: boolean;
  };
}

export function getTransmissionTelemetry(
  bundle: TransmissionBundle = canonicalBundle,
  customSensoryCues?: SensoryCueAnnotation[],
  targetFirstDivergenceCriterionId: string = 'CRIT-RATCHET',
  firstDivergenceSec: number = 19.2
): TransmissionTelemetry {
  const kp = bundle.knowledge_package;
  const rubric = bundle.rubric;
  const baselineEval = bundle.baseline_evaluation;
  const retryEval = bundle.retry_evaluation;
  const feedback = bundle.feedback;
  const record = bundle.transmission_record;

  const baselineMap = new Map<string, CriterionResult>(
    baselineEval.criterion_results.map((r) => [r.criterion_id, r])
  );
  const retryMap = new Map<string, CriterionResult>(
    retryEval.criterion_results.map((r) => [r.criterion_id, r])
  );
  const feedbackMap = new Map<string, FeedbackItem>(
    feedback.items.map((item) => [item.criterion_id, item])
  );

  let criteriaImprovedCount = 0;
  const criteriaComparisons: CriterionComparison[] = rubric.criteria.map((c) => {
    const base = baselineMap.get(c.criterion_id);
    const retry = retryMap.get(c.criterion_id);
    const fb = feedbackMap.get(c.criterion_id);

    const bScore = base?.score ?? 0;
    const rScore = retry?.score ?? 0;
    if (rScore > bScore) {
      criteriaImprovedCount++;
    }

    const isFirstDivergence = c.criterion_id === targetFirstDivergenceCriterionId;

    return {
      criterionId: c.criterion_id,
      name: c.name,
      weight: c.weight,
      required: c.required,
      observableIndicator: c.observable_indicator,
      baselineScore: bScore,
      baselineStatus: base?.status ?? 'uncertain',
      baselineNotes: base?.observed_finding,
      retryScore: rScore,
      retryStatus: retry?.status ?? 'uncertain',
      retryNotes: retry?.observed_finding,
      feedback: fb,
      expertEvidenceSec: fb?.expert_evidence_ref?.start_sec ?? 18.0,
      isFirstDivergence,
    };
  });

  const sensoryCues: SensoryCueAnnotation[] = customSensoryCues ?? [
    {
      id: 'cue-wipe',
      timeSec: 6.5,
      label: 'TACTILE: UNIDIRECTIONAL DRAG',
      category: 'tactile',
      description: 'Single continuous pull across carbide anvil faces (4.5s – 12.0s). Zero finger skin contact.',
      waveformRegion: { start: 4.5, end: 12.0 },
    },
    {
      id: 'cue-ratchet-1',
      timeSec: 18.4,
      label: 'ACOUSTIC: RATCHET CLICK #1',
      category: 'acoustic',
      description: 'Initial torque clutch engagement at 18.4s. First audible ratchet release sound.',
      waveformRegion: { start: 18.0, end: 18.6 },
    },
    {
      id: 'cue-ratchet-2',
      timeSec: 18.8,
      label: 'ACOUSTIC: RATCHET CLICK #2',
      category: 'acoustic',
      description: 'Second steady ratchet click at 18.8s (0.4s interval).',
      waveformRegion: { start: 18.6, end: 19.0 },
    },
    {
      id: 'cue-ratchet-3',
      timeSec: 19.2,
      label: 'ACOUSTIC: RATCHET CLICK #3',
      category: 'acoustic',
      description: 'Third and terminal audible ratchet click at 19.2s in the replay fixture; physical force is not directly measured.',
      waveformRegion: { start: 19.0, end: 19.5 },
    },
    {
      id: 'cue-lock',
      timeSec: 27.5,
      label: 'VISUAL: NEEDLE STABILIZATION',
      category: 'visual',
      description: 'Indicator needle settles within +/- 0.5 division before spindle lock lever engaged.',
      waveformRegion: { start: 26.0, end: 31.0 },
    },
  ];

  const maxPossible = rubric.criteria.reduce((sum, c) => sum + c.weight, 0);
  const gainPoints = record.transmission_gain;
  const gainPercentage = ((gainPoints / maxPossible) * 100);

  return {
    bundle,
    knowledgePackage: kp,
    rubric,
    task: bundle.practice_task,
    baselineAttempt: bundle.baseline_attempt,
    baselineEval,
    feedback,
    retryAttempt: bundle.retry_attempt,
    retryEval,
    record,
    criteriaComparisons,
    firstDivergenceSec,
    firstDivergenceCriterionId: targetFirstDivergenceCriterionId,
    sensoryCues,
    metrics: {
      baselineScore: record.baseline_score,
      retryScore: record.retry_score,
      maxPossibleScore: maxPossible,
      gainPoints,
      gainPercentage: Math.round(gainPercentage * 10) / 10,
      criteriaImprovedCount,
      totalCriteriaCount: rubric.criteria.length,
      rubricPassed: retryEval.passed,
    },
  };
}
