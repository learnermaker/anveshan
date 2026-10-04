/**
 * Gemini Multimodal Model Gateway Types
 */

import type { CertaintyState, WorkspaceType } from './workspace';

export type AnalysisMode = 'REPLAY' | 'LIVE';

export interface GeminiConfig {
  apiKey?: string;
  modelName: 'gemini-2.5-flash' | 'gemini-2.5-pro';
  temperature: number;
  mode: AnalysisMode;
}

export interface MultimodalObservation {
  id: string;
  timestampOrStep: string;
  modality: string;
  observation: string;
  certainty: CertaintyState;
  divergenceRisk?: 'low' | 'medium' | 'high';
}

export interface StateTransitionObservation {
  step: number;
  fromState: string;
  toState: string;
  actionObserved: string;
  timeWindow?: string;
}

export interface GeminiAnalysisResult {
  caseId: string;
  timestamp: string;
  isLiveModel: boolean;
  modelName: string;
  latencyMs: number;
  summary: string;
  observations: MultimodalObservation[];
  stateTransitions: StateTransitionObservation[];
  firstDivergence: {
    criterionId: string;
    timestampOrStep: string;
    description: string;
    certainty: CertaintyState;
    rubricAlignment: string;
  };
  intervention: {
    title: string;
    instruction: string;
    correctiveCue: string;
  };
  workspaceComposition: {
    recommendedWorkspace: WorkspaceType;
    justification: string;
    prioritizedModalities: string[];
  };
}
