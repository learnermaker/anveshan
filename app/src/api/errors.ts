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
