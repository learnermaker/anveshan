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
  CriterionResult,
  FeedbackItem,
} from '../types/contracts';

// Type assertion for bundle
export const canonicalBundle = rawBundle as unknown as TransmissionBundle;

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
  baselineStatus: 'satisfied' | 'partial' | 'divergent' | 'not_observed';
  baselineNotes?: string;
  retryScore: number;
  retryStatus: 'satisfied' | 'partial' | 'divergent' | 'not_observed';
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
    masteryAchieved: boolean;
  };
}

export function getTransmissionTelemetry(bundle: TransmissionBundle = canonicalBundle): TransmissionTelemetry {
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

    // CRIT-RATCHET is our primary first divergence in case_001
    const isFirstDivergence = c.criterion_id === 'CRIT-RATCHET';

    return {
      criterionId: c.criterion_id,
      name: c.name,
      weight: c.weight,
      required: c.required,
      observableIndicator: c.observable_indicator,
      baselineScore: bScore,
      baselineStatus: base?.status ?? 'divergent',
      baselineNotes: base?.observation_notes,
      retryScore: rScore,
      retryStatus: retry?.status ?? 'satisfied',
      retryNotes: retry?.observation_notes,
      feedback: fb,
      expertEvidenceSec: fb?.expert_evidence_ref?.start_sec ?? 18.0,
      isFirstDivergence,
    };
  });

  const sensoryCues: SensoryCueAnnotation[] = [
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
      label: 'ACOUSTIC: RATCHET CLICK #3 (CALIBRATED)',
      category: 'acoustic',
      description: 'Third and terminal ratchet click at 19.2s. 5.0 Newton standard force verified.',
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
    firstDivergenceSec: 19.2,
    firstDivergenceCriterionId: 'CRIT-RATCHET',
    sensoryCues,
    metrics: {
      baselineScore: record.baseline_score,
      retryScore: record.retry_score,
      maxPossibleScore: maxPossible,
      gainPoints,
      gainPercentage: Math.round(gainPercentage * 10) / 10,
      criteriaImprovedCount,
      totalCriteriaCount: rubric.criteria.length,
      masteryAchieved: retryEval.passed,
    },
  };
}
