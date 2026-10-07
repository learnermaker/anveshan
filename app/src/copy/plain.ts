/**
 * Plain-language copy for the learner and creator surfaces (K9-00 §5).
 *
 * One place for every user-facing label that replaces a technical term. Views import from here
 * instead of writing their own wording, so the product speaks with one voice. Honesty labels
 * (synthetic, internet source, AI's reading, not yet checked) are translated, never dropped.
 */

import type { LibraryStatus, LicenceId } from '../api/types-product';

/** runtime_label -> where the skill comes from */
export const SOURCE_LABEL: Record<string, string> = {
  INTERNET_REFERENCE: 'From an openly licensed internet source',
  UPLOAD: 'Shared by its creator',
  SYNTHETIC: 'Synthetic example (made up for the demo)',
  OWNED_CONSENTED: 'Shared with consent by its creator',
};

/** review_status -> has a person checked the steps (library and learner view) */
export const REVIEW_LABEL: Record<string, string> = {
  approved: 'Checked by an expert',
  revised: 'Checked and corrected by an expert',
  pending: 'Not yet checked by an expert',
  rejected: 'Withdrawn after expert review',
};

/** review_status as the creator sees it on their own skill */
export const OWN_REVIEW_LABEL: Record<string, string> = {
  approved: 'You checked the steps',
  revised: 'You corrected the steps',
  pending: 'Steps not checked yet',
  rejected: 'Withdrawn',
};

/** criterion status -> result of one check */
export const STATUS_PLAIN: Record<string, string> = {
  satisfied: 'Met',
  partially_satisfied: 'Partly met',
  not_satisfied: 'Not met',
  uncertain: "Couldn't tell",
};

/** claim certainty -> how we know */
export const CERTAINTY_PLAIN: Record<string, string> = {
  observed: 'Seen in the source',
  inferred: "AI's reading",
  unverified: 'Not checked',
};

/** library lifecycle status as the creator and steward see it */
export const LIBRARY_STATUS_LABEL: Record<LibraryStatus, string> = {
  private: 'Private',
  submitted: 'Waiting for review',
  published: 'Published',
  returned: 'Sent back',
  rejected: 'Not accepted',
  unlisted: 'Hidden by a steward',
};

export const LIBRARY_STATUS_HELP: Record<LibraryStatus, string> = {
  private: 'Only you can see and practise this skill.',
  submitted: 'A steward will check it before it appears in the library. You can withdraw it at any time.',
  published: 'Anyone can find it in the library and practise it.',
  returned: 'A steward sent it back with a note. Fix what they asked, then send it again.',
  rejected: 'A steward decided not to publish it. It stays private to you.',
  unlisted: 'A steward hid it from the library. People who already started can still finish.',
};

export interface LicenceOption {
  id: LicenceId;
  label: string;
  help: string;
}

export const LICENCE_OPTIONS: LicenceOption[] = [
  { id: 'CC-BY-4.0', label: 'Credit me (CC BY 4.0)', help: 'Anyone may practise and share it, as long as they credit you. Recommended.' },
  { id: 'CC-BY-SA-4.0', label: 'Credit me, share alike (CC BY-SA 4.0)', help: 'As above, and changed versions must be shared under the same terms.' },
  { id: 'CC0-1.0', label: 'No conditions (CC0)', help: 'You give up all conditions, including credit.' },
  { id: 'PRACTICE-ONLY', label: 'Practice here only', help: 'Learners may practise it in Anveshan; no reuse anywhere else.' },
];

export function licenceLabel(id: string | null | undefined): string {
  if (!id) return 'Licence not stated';
  return LICENCE_OPTIONS.find((o) => o.id === id)?.label ?? id;
}

/** 1 -> "First try", 2 -> "Second try", n -> "Try n" */
export function attemptLabel(n: number): string {
  return n === 1 ? 'First try' : n === 2 ? 'Second try' : `Try ${n}`;
}

export interface TrustInput {
  runtime_label: string;
  review_status: string;
  credit_name?: string | null;
  collection?: string | null;
}

/**
 * One sentence telling a learner where a skill comes from and whether a person checked it.
 * Example: "From an openly licensed internet source, not a verified expert. Steps found with AI; not yet checked by an expert."
 */
export function trustLine(v: TrustInput): string {
  const checked = v.review_status === 'approved' || v.review_status === 'revised';
  let from: string;
  if (v.runtime_label === 'SYNTHETIC') from = 'Synthetic example made up for the demo.';
  else if (v.runtime_label === 'INTERNET_REFERENCE') from = 'From an openly licensed internet source, not a verified expert.';
  else if (v.credit_name) from = `Shared by ${v.credit_name}.`;
  else from = 'Shared by its creator.';
  const steps = checked ? 'Steps found with AI and checked by a person.' : 'Steps found with AI; not yet checked by an expert.';
  return `${from} ${steps}`;
}

/** short practice-mode phrase for a modality */
export const MODALITY_PHRASE: Record<string, string> = {
  kolam_image: 'Draw it on screen or upload a photo',
  origami_video: 'Record a short video of your folding',
  tabla_audio: 'Record yourself playing',
  universal: 'Practise and upload your attempt',
};

/**
 * Terms that must not appear in the learner or creator surfaces, checked by
 * app/scripts/check_plain_language.mjs.
 * - A term written in lower case matches case-insensitively, as a whole word.
 * - A term containing an upper-case letter matches case-sensitively (e.g. 'SATISFIED' does not match "satisfied").
 * Exempt: the steward console, ?debug=1, and any element (with its children) marked
 * `data-plain-exempt`. That marker is for text authored by people or by the source, such as skill
 * titles, step statements or answers quoting the source.
 */
export const BANNED_LEARNER_TERMS: string[] = [
  'CLM-',
  'claim',
  'claims',
  'knowledge package',
  'provenance',
  'lineage',
  'runtime',
  'RECORDED_LIVE',
  'RECORDED LIVE',
  'DETERMINISTIC',
  'INFERRED',
  'OBSERVED',
  'conf ',
  'confidence',
  'criterion',
  'criteria',
  'rubric',
  'trajectory',
  'divergence',
  'modality',
  'goal model',
  'baseline',
  'session',
  'REVIEW:',
  'SATISFIED',
  'UNCERTAIN',
  'MOCK DATA',
  'replay fixture',
  'provenance_hash',
  'Approve package',
];
