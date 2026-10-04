/**
 * Anveshan Shared Contracts — TypeScript Definitions
 * 1:1 Seam mapping from tracks/common/schemas/
 */

export interface EvidenceRef {
  evidence_id: string;
  source_id: string;
  modality: 'video' | 'audio' | 'sensor' | 'document' | 'composite';
  start_sec?: number;
  end_sec?: number;
  uri?: string;
  cue_excerpt?: string;
  verification_state: 'raw' | 'extracted' | 'observed' | 'disputed';
  confidence: number; // 0.0 - 1.0
  metadata?: Record<string, unknown>;
}

export interface Claim {
  claim_id: string;
  claim_type: 'step' | 'cue' | 'condition' | 'pitfall' | 'principle';
  statement: string;
  evidence_refs: EvidenceRef[];
  is_observed: boolean;
}

export interface ConsentRecord {
  contributor_name: string;
  consent_scope: string;
  revocable: boolean;
  granted_at: string;
  notes?: string;
}

export interface ExpertReviewRecord {
  reviewer_name: string;
  status: 'pending' | 'approved' | 'rejected' | 'revisions_requested';
  reviewed_at?: string;
  notes?: string;
}

export interface KnowledgePackage {
  package_id: string;
  skill_id: string;
  title: string;
  summary: string;
  claims: Claim[];
  consent: ConsentRecord;
  expert_review: ExpertReviewRecord;
  version?: string;
  created_at?: string;
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
  description: string;
  criteria: RubricCriterion[];
  passing_score?: number;
  created_at?: string;
}

export interface ExpectedEvidence {
  modality: string;
  description: string;
  min_duration_sec?: number;
}

export interface PracticeTask {
  task_id: string;
  skill_id: string;
  package_id: string;
  title: string;
  instructions: string;
  target_criteria: string[];
  expected_evidence: ExpectedEvidence[];
}

export interface AttemptEvidenceRef {
  evidence_id: string;
  source_id: string;
  modality: string;
  start_sec?: number;
  end_sec?: number;
  uri?: string;
}

export interface LearnerAttempt {
  attempt_id: string;
  task_id: string;
  learner_id: string;
  attempt_type: 'baseline' | 'retry';
  attempt_number: number;
  evidence_refs: AttemptEvidenceRef[];
  notes?: string;
  created_at?: string;
}

export interface CriterionResult {
  criterion_id: string;
  score: number;
  status: 'satisfied' | 'partial' | 'divergent' | 'not_observed';
  divergence_type?: 'omission' | 'incorrect_execution' | 'excessive_motion' | 'timing_fault' | 'safety_hazard';
  evidence_ref?: EvidenceRef;
  observation_notes?: string;
}

export interface Evaluation {
  evaluation_id: string;
  attempt_id: string;
  rubric_id: string;
  evaluator_type: 'gemini' | 'expert_human' | 'consensus';
  criterion_results: CriterionResult[];
  total_score: number;
  max_possible_score: number;
  passed: boolean;
  model_id?: string;
  evaluated_at?: string;
}

export interface FeedbackItem {
  feedback_id: string;
  criterion_id: string;
  divergence_observed: string;
  corrective_instruction: string;
  expert_evidence_ref?: EvidenceRef;
  priority: number; // 1 = highest
}

export interface Feedback {
  feedback_id: string;
  evaluation_id: string;
  attempt_id: string;
  items: FeedbackItem[];
  created_at?: string;
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
  criteria_improved?: string[];
  lineage: LineageMetadata;
}

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
