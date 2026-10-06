/** Client-side session state for a live hero case (lifted into App so 03 TRANSMISSION can read it). */

import type { AttemptKind, AttemptResult, SessionResult } from '../api/types';
import type { Stroke } from './kolam/KolamCanvas';

/** What the learner submitted, kept locally so results can show learner evidence next to expert evidence. */
export interface LocalAttemptMedia {
  kind: AttemptKind;
  fileName?: string;
  strokes?: Stroke[];
  /** object URL of the uploaded image / video / audio */
  url?: string;
  /** tabla: optional video (shown, not scored) */
  extraVideoUrl?: string;
}

export interface HeroSession {
  caseId: string;
  sessionId: string;
  learnerName: string;
  attempts: { result: AttemptResult; media: LocalAttemptMedia }[];
  result: SessionResult | null;
}
