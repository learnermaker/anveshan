/**
 * Anveshan frontend view of the frozen common-contract seam.
 *
 * SOURCE OF TRUTH:
 *   tracks/common/schemas/
 *
 * This file is intentionally field/enumeration-compatible with the eight
 * Python contracts. It is not a second product contract. UI-only composites
 * (for example TransmissionBundle) are downstream views, not shared seams.
 *
 * If a field or enum must change here, change the canonical Python contract
 * first and then update this downstream representation/adapter.
 */

export type Modality = 'video' | 'audio' | 'image' | 'text' | 'sensor';
export type VerificationState = 'observed' | 'inferred' | 'unverified';

export interface EvidenceRef {
  evidence_id: string;
  source_id: string;
  modality: Modality;
  start_sec?: number;
  end_sec?: number;
  cue_excerpt?: string;
  verification_state: VerificationState;
  confidence: number;
}

export type ClaimType = 'step' | 'cue' | 'condition' | 'exception' | 'failure_mode';
export type ReviewStatus = 'pending' | 'approved' | 'revised' | 'rejected';

export interface ConsentMetadata {
  contributor_name: string;
  consent_scope: string;
  revocable: boolean;
  granted_at?: string;
  notes?: string;
}

export interface ExpertReview {
  reviewer_name: string;
  status: ReviewStatus;
  reviewed_at?: string;
  notes?: string;
}

export interface KnowledgeClaim {
  claim_id: string;
  claim_type: ClaimType;
  statement: string;
  is_observed: boolean;
  evidence_refs: EvidenceRef[];
}

export interface KnowledgePackage {
  package_id: string;
  skill_id: string;
  title: string;
  summary: string;
  claims: KnowledgeClaim[];
  consent: ConsentMetadata;
  expert_review?: ExpertReview;
}

export interface RubricCriterion {
  criterion_id: string;
  name: string;
  description: string;
  observable_indicator: string;
  weight: number;
  required: boolean;
}

export interface RubricDefinition {
  rubric_id: string;
  skill_id: string;
  title: string;
  description?: string;
  criteria: RubricCriterion[];
  passing_score?: number;
}

export interface TaskConstraint {
  constraint_type: string;
  description: string;
  value?: string;
}

export interface PracticeTask {
  task_id: string;
  package_id: string;
  rubric_id: string;
  title: string;
  instructions: string;
  constraints: TaskConstraint[];
  target_criteria_ids: string[];
}

export type AttemptType = 'baseline' | 'retry';

export interface ParticipantRef {
  participant_id: string;
  name: string;
  role: string;
  notes?: string;
}

export interface LearnerAttempt {
  attempt_id: string;
  task_id: string;
  learner: ParticipantRef;
  attempt_type: AttemptType;
  attempt_number: number;
  submitted_at?: string;
  evidence: EvidenceRef;
}

export type CriterionStatus =
  | 'satisfied'
  | 'partially_satisfied'
  | 'not_satisfied'
  | 'uncertain';

export type EvaluatorType = 'deterministic' | 'model_assisted' | 'human_expert';

export interface CriterionResult {
  criterion_id: string;
  status: CriterionStatus;
  score: number;
  observed_finding: string;
  deviation_analysis?: string;
  evidence_ref?: EvidenceRef;
}

export interface Evaluation {
  evaluation_id: string;
  attempt_id: string;
  rubric_id: string;
  criterion_results: CriterionResult[];
  total_score: number;
  passed: boolean;
  evaluator_type: EvaluatorType;
  uncertainty_flags: string[];
  evaluated_at?: string;
}

export interface FeedbackItem {
  criterion_id: string;
  what_was_observed: string;
  what_differed: string;
  corrective_advice: string;
  expert_evidence_ref?: EvidenceRef;
  learner_evidence_ref?: EvidenceRef;
}

export interface Feedback {
  feedback_id: string;
  evaluation_id: string;
  attempt_id: string;
  summary: string;
  items: FeedbackItem[];
  recommended_retry_focus: string[];
}

export interface LineageMetadata {
  parent_transmission_id?: string | null;
  recorded_at: string;
  provenance_hash?: string | null;
  adaptation_notes?: string | null;
}

export interface TransmissionRecord {
  transmission_id: string;
  skill_id: string;
  package_id: string;
  rubric_id: string;
  expert_id: string;
  learner_id: string;
  baseline_attempt_id: string;
  retry_attempt_id: string;
  baseline_score: number;
  retry_score: number;
  transmission_gain: number;
  criteria_improved: string[];
  lineage: LineageMetadata;
}

/** Downstream UI composite; not one of the eight shared contracts. */
export interface TransmissionBundle {
  case_id: string;
  domain: string;
  skill: string;
  knowledge_package: KnowledgePackage;
  rubric: RubricDefinition;
  practice_task: PracticeTask;
  baseline_attempt: LearnerAttempt;
  baseline_evaluation: Evaluation;
  feedback: Feedback;
  retry_attempt: LearnerAttempt;
  retry_evaluation: Evaluation;
  transmission_record: TransmissionRecord;
}
