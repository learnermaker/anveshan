import type { ErrorCategory } from './types';

/** Normalised service error from {"error": {category, message, details}} (service-api §5). */
export class ApiError extends Error {
  readonly category: ErrorCategory | string;
  readonly status: number;
  readonly details: unknown;

  constructor(category: ErrorCategory | string, message: string, status = 0, details: unknown = null) {
    super(message);
    this.name = 'ApiError';
    this.category = category;
    this.status = status;
    this.details = details;
  }
}

export interface FriendlyError {
  /** Short plain-language headline. */
  title: string;
  /** What happened and what to do next, for a first-time user. */
  message: string;
  /** Category, HTTP status and the raw service message, shown only under "Technical details". */
  technical: string;
  /** offer the "use your own API key" dialog (no key yet, replay-only request or used-up quota) */
  suggestKey?: boolean;
}

/** Map a service error to plain language. The raw message stays available as technical detail. */
export function friendlyError(error: unknown): FriendlyError {
  const raw = error instanceof Error ? error.message : String(error);
  if (!(error instanceof ApiError)) {
    return { title: 'Something went wrong', message: raw, technical: raw };
  }
  const technical = `${error.category}${error.status ? ` · HTTP ${error.status}` : ''} · ${raw}`;
  const details = (error.details ?? {}) as Record<string, unknown>;
  switch (error.category) {
    case 'REPLAY_MISMATCH':
      return {
        title: 'This needs live AI',
        message: 'This server is replaying recorded results, and this exact request was never recorded. Try one of the sample attempts, or use your own Gemini API key to run it live.',
        technical,
        suggestKey: true,
      };
    case 'RATE_LIMITED': {
      const wait = Number(details.retry_after_s ?? 0);
      const mins = wait > 0 ? Math.max(1, Math.round(wait / 60)) : 0;
      return { title: 'Please wait a little', message: `${raw}${mins ? ` You can try again in about ${mins} minute${mins > 1 ? 's' : ''}.` : ''}`, technical, suggestKey: false };
    }
    case 'REVIEW_DISABLED':
      return { title: 'Review is by invitation', message: raw, technical };
    case 'NETWORK':
      return { title: 'Cannot reach the service', message: 'The Anveshan service did not answer. Check your connection and try again in a moment.', technical };
    case 'MODEL_FAILURE':
    case 'MODEL_TIMEOUT':
      if (details.reason === 'key_required') {
        return { title: 'Add your Gemini API key', message: 'Checking something new uses Gemini AI with your own API key. Add it once (free from Google AI Studio); it stays in this browser.', technical, suggestKey: true };
      }
      if (details.reason === 'daily_budget') return { title: "Today's live AI budget is used up", message: raw, technical, suggestKey: true };
      return {
        title: 'The AI model did not answer',
        message: 'The model call failed or timed out. Nothing was scored. Please try again; if it keeps failing, try a sample attempt.',
        technical,
      };
    case 'STEWARD_REQUIRED':
      return { title: 'Steward access needed', message: 'Enter the steward access code to continue.', technical };
    case 'STEWARD_DISABLED':
      return { title: 'Steward console not enabled', message: 'This server does not have a steward console.', technical };
    case 'NOT_OWNER':
      return { title: 'Only the creator can do this', message: raw, technical };
    case 'INVALID_INPUT': {
      const blockers = details.blockers;
      if (Array.isArray(blockers) && blockers.length > 0) {
        return { title: 'Not ready to publish yet', message: (blockers as string[]).join(' '), technical };
      }
      if (raw.startsWith('Google rejected this key') || raw.startsWith('No API key was sent')) {
        return { title: 'That key did not work', message: raw, technical, suggestKey: false };
      }
      return { title: 'This file or input cannot be used', message: raw, technical };
    }
    case 'MISSING_EVIDENCE':
      return { title: 'Not found', message: "This wasn't found. The link may be wrong, or a shared upload may have expired (uploads are kept for a few hours).", technical };
    case 'HUMAN_REVIEW_REQUIRED':
    case 'AMBIGUOUS_EVIDENCE':
    case 'UNSUPPORTED_CLAIM':
      return { title: 'Not enough evidence to decide', message: raw, technical };
    case 'INTERNAL_ERROR':
      return { title: 'Something went wrong on the server', message: 'The request failed unexpectedly. Please try again.', technical };
    default:
      return { title: 'Something went wrong', message: raw, technical };
  }
}
