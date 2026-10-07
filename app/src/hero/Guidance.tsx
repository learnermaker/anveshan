/** Learner guidance shared by the practice views: readable task steps and "what to do next". */

import React from 'react';
import { ArrowRight, Check, RotateCcw } from 'lucide-react';
import type { KnowledgeClaim as Claim } from '../types/contracts';
import { btn } from './ui';
import { trustLine } from '../copy/plain';
import { DEBUG } from '../api/debug';

const CLAIM_REF = /\[((?:CLM-[A-Za-z0-9-]+)(?:\s*,\s*CLM-[A-Za-z0-9-]+)*)\]/g;

/** Split "1. foo 2. bar" into items; text without numbering stays one item. */
export function splitNumbered(text: string): string[] {
  const parts = text
    .split(/(?:^|\s)(?=\d{1,2}\.\s)/)
    .map((p) => p.replace(/^\d{1,2}\.\s+/, '').trim())
    .filter(Boolean);
  return parts.length ? parts : [text];
}

/** In learner mode: strip [CLM-..] references from text (no double spaces remain).
 *  In DEBUG mode: render as small chips with hover tooltip. */
export function WithClaimRefs({ text, claims }: { text: string; claims: Claim[] }) {
  if (!DEBUG) {
    // Strip [CLM-...] references and clean up extra whitespace
    const stripped = text.replace(CLAIM_REF, '').replace(/\s{2,}/g, ' ').trim();
    return <>{stripped}</>;
  }
  const out: React.ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(CLAIM_REF)) {
    const at = m.index ?? 0;
    if (at > last) out.push(text.slice(last, at));
    for (const id of m[1].split(/\s*,\s*/)) {
      const claim = claims.find((c) => c.claim_id === id);
      out.push(
        <span
          key={`${at}-${id}`}
          title={claim ? `${id}: ${claim.statement}` : id}
          className="inline-block mx-0.5 px-1 rounded border border-caliper-cyan/40 text-caliper-cyan font-mono text-[11px] align-baseline cursor-help"
        >
          {id}
        </span>,
      );
    }
    last = at + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return <>{out}</>;
}

export function TaskInstructions({ text, claims }: { text: string; claims: Claim[] }) {
  const items = splitNumbered(text);
  return (
    <div className="space-y-1.5">
      <ol className="list-decimal pl-5 space-y-1 text-sm text-on-surface leading-relaxed marker:text-on-surface-variant">
        {items.map((it, i) => (
          <li key={i}>
            <span data-plain-exempt>
              <WithClaimRefs text={it} claims={claims} />
            </span>
          </li>
        ))}
      </ol>
      {DEBUG && (
        <p className="text-xs text-on-surface-variant">Blue tags such as CLM-01 point to the source claim behind a step. Hover or tap to read it.</p>
      )}
    </div>
  );
}

interface ProgressProps {
  attempts: number;
  /** a session exists */
  started: boolean;
  completing?: boolean;
  onRetry?: () => void;
  onComplete?: () => void;
  /** the retry form is already open */
  retryOpen?: boolean;
}

/** Three-step tracker (first try, second try, results) with the one next action spelled out. */
export function AttemptProgress({ attempts, started, completing, onRetry, onComplete, retryOpen }: ProgressProps) {
  const steps = ['First try', 'Second try', 'See what changed'];
  const doneCount = Math.min(attempts, 2);
  let next: React.ReactNode;
  if (!started) next = 'Start below. Your name is optional.';
  else if (attempts === 0) next = 'Do the task once, as well as you can, and submit it.';
  else if (attempts === 1)
    next = retryOpen ? (
      'Do the whole task again below, using the feedback from your first try.'
    ) : (
      <span className="flex flex-wrap items-center gap-2">
        Read the feedback and the drill below, then retry the whole task once.
        {onRetry && (
          <button onClick={onRetry} className={btn.primary}>
            <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" /> Retry now
          </button>
        )}
      </span>
    );
  else
    next = (
      <span className="flex flex-wrap items-center gap-2">
        Both tries are done.
        {onComplete && (
          <button onClick={onComplete} disabled={completing} className={btn.primary}>
            {completing ? 'Saving the record…' : 'See what changed'} <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
        )}
      </span>
    );
  return (
    <div className="rounded-xl border border-cadmium-amber/40 bg-cadmium-amber/5 p-3 space-y-2" aria-live="polite">
      <ol className="flex flex-wrap items-center gap-2 text-sm">
        {steps.map((s, i) => {
          const done = i < doneCount;
          const current = i === doneCount && started;
          return (
            <li key={s} className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border ${
                  done
                    ? 'border-transmission-emerald/50 text-transmission-emerald'
                    : current
                      ? 'border-cadmium-amber text-cadmium-amber font-semibold'
                      : 'border-outline text-on-surface-variant'
                }`}
              >
                {done ? <Check className="w-3.5 h-3.5" aria-label="done" /> : <span className="font-mono">{i + 1}</span>}
                {s}
              </span>
              {i < steps.length - 1 && <span className="text-outline" aria-hidden="true">→</span>}
            </li>
          );
        })}
      </ol>
      <div className="text-sm text-on-surface">
        <span className="font-semibold text-cadmium-amber">Next: </span>
        {next}
      </div>
    </div>
  );
}

/** The honest status line for packages no expert has reviewed. */
export function ReviewNote({ status, runtimeLabel = 'INTERNET_REFERENCE' }: { status: string; runtimeLabel?: string }) {
  if (status === 'approved' || status === 'revised') return null;
  const line = trustLine({ runtime_label: runtimeLabel, review_status: status });
  return (
    <p className="text-sm text-on-surface-variant">
      <span className="text-cadmium-amber font-semibold">Not yet checked by an expert.</span>{' '}
      You can practise normally. {line} Treat results as practice feedback, not a certificate.
    </p>
  );
}
