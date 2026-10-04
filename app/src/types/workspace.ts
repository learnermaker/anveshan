/**
 * Declarative Workspace Compiler and Interaction Types
 * Defines the adaptive GenUI interface primitives and certainty taxonomy
 */

import type { TransmissionBundle } from './contracts';
import type { TransmissionTelemetry } from '../data/adapter';

export type CertaintyState =
  | 'SOURCE_DERIVED_FACT'
  | 'OBSERVED'
  | 'INFERRED'
  | 'UNVERIFIED'
  | 'UNKNOWN';

export type WorkspaceType =
  | 'forensic_instrument'
  | 'spatial_canvas'
  | 'diagnostic_workspace'
  | 'state_transition'
  | 'rhythm_instrument'
  | 'spatial_sequence'
  | 'first_divergence';

export type AppView =
  | 'discovery'
  | 'source'
  | 'practice'
  | 'transmission';

export interface WorkspaceSpecification {
  workspaceType: WorkspaceType;
  title: string;
  tagline: string;
  reasoningArchetype: string;
  primaryModalities: Array<'video' | 'audio' | 'spatial' | 'numeric' | 'sensor' | 'state' | 'diagnostic'>;
  compilerRationale: string;
  evidenceProfile: {
    temporalResolution: string;
    primarySensoryCues: string[];
    uncertaintyBoundary: string;
  };
  features: {
    dualDeck: boolean;
    spatialCanvas: boolean;
    diagnosticTree: boolean;
    stateMatrix: boolean;
    rhythmEnvelope: boolean;
    foldSequence: boolean;
    knotCrossing: boolean;
    sensoryRibbon: boolean;
    rubricHud: boolean;
    firstDivergenceInteraction: boolean;
    microPracticeRetry: boolean;
  };
}

export interface FirstDivergenceDetail {
  criterionId: string;
  criterionName: string;
  timeSec?: number;
  stepIndex?: number;
  divergenceTitle: string;
  observation: string;
  observationCertainty: CertaintyState;
  evidenceLocation: string;
  interpretation: string;
  interpretationCertainty: CertaintyState;
  consequence: string;
  unknownFactors: string[];
  targetedIntervention: string;
  suggestedAction: string;
}

export interface MicroPracticeChallenge {
  challengeId: string;
  targetCriterionId: string;
  title: string;
  instructions: string;
  interactionType:
    | 'slider_torque'
    | 'canvas_loop'
    | 'diagnosis_tree'
    | 'shuttle_pass'
    | 'rhythm_tap'
    | 'fold_angle'
    | 'knot_cross';
  targetLabel: string;
  correctiveCue: string;
  baselineDeficitExplanation: string;
  successThresholdLabel: string;
}

export interface CapabilityCase {
  id: string;
  title: string;
  domain: string;
  archetype: string;
  shortDescription: string;
  expertName: string;
  expertRole: string;
  learnerName: string;
  learnerBackground: string;
  primaryModalities: Array<'video' | 'audio' | 'spatial' | 'numeric' | 'sensor' | 'state' | 'diagnostic'>;
  workspaceSpec: WorkspaceSpecification;
  bundle: TransmissionBundle;
  telemetry: TransmissionTelemetry;
  firstDivergence: FirstDivergenceDetail;
  microPractice: MicroPracticeChallenge;
  uncertainties: Array<{
    aspect: string;
    state: CertaintyState;
    rationale: string;
  }>;
}
