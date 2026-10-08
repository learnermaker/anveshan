/** Shared badges and small primitives for the live hero-case screens. */

import React, { useEffect, useState } from 'react';
import { AlertTriangle, KeyRound, Loader2 } from 'lucide-react';
import type { CriterionStatus, VerificationState } from '../types/contracts';
import type { RuntimeClass } from '../api/types';
import { friendlyError } from '../api/errors';
import { getUserKey, requestKeyDialog, subscribeUserKey } from '../api/userKey';
import { IS_MOCK } from '../api/runtime';
import { DEBUG } from '../api/debug';
import { SOURCE_LABEL, REVIEW_LABEL, OWN_REVIEW_LABEL, STATUS_PLAIN } from '../copy/plain';

export { STATUS_PLAIN };

const base = 'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-mono font-bold uppercase tracking-wider border whitespace-nowrap';

export function Badge({ tone, children, title }: { tone: 'amber' | 'emerald' | 'cyan' | 'crimson' | 'muted'; children: React.ReactNode; title?: string }) {
  const cls = {
    amber: 'bg-cadmium-amber/10 text-cadmium-amber border-cadmium-amber/30',
    emerald: 'bg-transmission-emerald/10 text-transmission-emerald border-transmission-emerald/30',
    cyan: 'bg-caliper-cyan/10 text-caliper-cyan border-caliper-cyan/30',
    crimson: 'bg-divergence-crimson/10 text-divergence-crimson border-divergence-crimson/30',
    muted: 'bg-surface-dim text-on-surface-variant border-outline',
  }[tone];
  return (
    <span className={`${base} ${cls}`} title={title}>
      {children}
    </span>
  );
}

/** Mock mode is shown once, in the header and footer; per-panel badges were noise (warning fatigue). */
export function MockBadge(): React.ReactElement | null {
  return null;
}

export function SourceLabelBadge({ label }: { label: string }) {
  if (!DEBUG) {
    const text = SOURCE_LABEL[label] ?? label;
    const tone: 'amber' | 'emerald' | 'cyan' | 'crimson' | 'muted' =
      label === 'SYNTHETIC' ? 'crimson' : label === 'INTERNET_REFERENCE' ? 'cyan' : 'muted';
    return <Badge tone={tone}>{text}</Badge>;
  }
  const map: Record<string, { tone: 'amber' | 'emerald' | 'cyan' | 'crimson' | 'muted'; text: string }> = {
    INTERNET_REFERENCE: { tone: 'cyan', text: 'INTERNET REFERENCE' },
    UPLOAD: { tone: 'amber', text: 'UPLOAD' },
    SYNTHETIC: { tone: 'crimson', text: 'SYNTHETIC' },
    OWNED_CONSENTED: { tone: 'emerald', text: 'OWNED · CONSENTED' },
  };
  const m = map[label] ?? { tone: 'muted' as const, text: label };
  return <Badge tone={m.tone}>{m.text}</Badge>;
}

export function ReviewBadge({ status, own }: { status: string; own?: boolean }) {
  if (!DEBUG) {
    const labelMap = own ? OWN_REVIEW_LABEL : REVIEW_LABEL;
    const text = labelMap[status] ?? status;
    const tone: 'emerald' | 'amber' | 'crimson' =
      status === 'approved' || status === 'revised' ? 'emerald' : status === 'rejected' ? 'crimson' : 'amber';
    return <Badge tone={tone}>{text}</Badge>;
  }
  const tone = status === 'approved' ? 'emerald' : status === 'rejected' ? 'crimson' : status === 'revised' ? 'cyan' : 'amber';
  return <Badge tone={tone}>REVIEW: {status}</Badge>;
}

export function VerificationBadge({ state }: { state: VerificationState }) {
  if (!DEBUG) {
    if (state === 'observed') return null;
    if (state === 'inferred') return <Badge tone="amber">AI's reading</Badge>;
    return <Badge tone="muted">Not checked</Badge>;
  }
  const tone = state === 'observed' ? 'emerald' : state === 'inferred' ? 'amber' : 'muted';
  return <Badge tone={tone}>{state}</Badge>;
}

export const STATUS_LABEL: Record<CriterionStatus, string> = {
  satisfied: 'SATISFIED',
  partially_satisfied: 'PARTIAL',
  not_satisfied: 'NOT SATISFIED',
  uncertain: 'UNCERTAIN',
};

export function StatusBadge({ status }: { status: CriterionStatus | string }) {
  const tone = status === 'satisfied' ? 'emerald' : status === 'partially_satisfied' ? 'amber' : status === 'not_satisfied' ? 'crimson' : 'muted';
  if (!DEBUG) {
    return <Badge tone={tone}>{STATUS_PLAIN[status] ?? status}</Badge>;
  }
  return <Badge tone={tone}>{STATUS_LABEL[status as CriterionStatus] ?? status}</Badge>;
}

export function RuntimeClassBadge({ value }: { value: RuntimeClass | string }) {
  if (!DEBUG) return null;
  const map: Record<string, { tone: 'cyan' | 'amber' | 'emerald'; text: string; title: string }> = {
    LIVE: { tone: 'cyan', text: 'LIVE', title: 'Model calls made during this request' },
    RECORDED_LIVE: { tone: 'amber', text: 'RECORDED LIVE', title: 'Replayed from a recorded live model run' },
    DETERMINISTIC: { tone: 'emerald', text: 'DETERMINISTIC', title: 'No model involved in scoring' },
  };
  const m = map[value] ?? { tone: 'amber' as const, text: value, title: '' };
  return (
    <Badge tone={m.tone} title={m.title}>
      {m.text}
    </Badge>
  );
}

export function Panel({ title, kicker, right, children, className = '' }: { title?: React.ReactNode; kicker?: string; right?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-outline bg-surface-container-low/80 ${className}`}>
      {(title || kicker || right) && (
        <header className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 border-b border-outline/60">
          <div>
            {kicker && <div className="text-[11px] font-mono uppercase tracking-widest text-cadmium-amber font-bold">{kicker}</div>}
            {title && <h3 className="text-sm font-semibold text-on-surface">{title}</h3>}
          </div>
          {right && <div className="flex items-center gap-2 flex-wrap">{right}</div>}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  const f = friendlyError(error);
  return (
    <div role="alert" className="flex items-start gap-2 p-3 rounded-lg border border-divergence-crimson/40 bg-divergence-crimson/10 text-sm text-on-surface">
      <AlertTriangle className="w-4 h-4 text-divergence-crimson shrink-0 mt-0.5" aria-hidden="true" />
      <div className="space-y-1">
        <div className="font-semibold text-divergence-crimson">{f.title}</div>
        <div>{f.message}</div>
        {f.suggestKey && (
          <button type="button" onClick={requestKeyDialog} className="text-sm text-caliper-cyan underline">
            Add your Gemini API key
          </button>
        )}
        <details className="text-xs text-on-surface-variant">
          <summary className="cursor-pointer select-none">Technical details</summary>
          <code className="font-mono break-all">{f.technical}</code>
        </details>
      </div>
    </div>
  );
}

/**
 * Shown next to every live upload: checking a new photo, video or recording uses Gemini. The visitor can
 * add their own key (kept in this browser, sent only to this app's service).
 */
export function KeyHint() {
  const [key, setKey] = useState<string | null>(() => getUserKey());
  useEffect(() => subscribeUserKey(setKey), []);
  if (IS_MOCK) return null;
  return (
    <p className="text-xs text-on-surface-variant leading-relaxed">
      <KeyRound className="inline w-3.5 h-3.5 mr-1 -mt-0.5 text-cadmium-amber" aria-hidden="true" />
      {key ? (
        <>
          Checking your upload uses your own Gemini API key.{' '}
          <button type="button" onClick={requestKeyDialog} className="text-caliper-cyan underline">Change key</button>
        </>
      ) : (
        <>
          Checking a new upload needs your own Gemini API key.{' '}
          <button type="button" onClick={requestKeyDialog} className="text-caliper-cyan underline">Add your Gemini API key</button>{' '}
          (free from Google AI Studio; it stays in this browser). Sample attempts need no key.
        </>
      )}
    </p>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-xs font-mono text-on-surface-variant">
      <Loader2 className="w-4 h-4 animate-spin text-cadmium-amber" />
      {label}
    </div>
  );
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  return (
    <div className="space-y-1">
      {label && (
        <div className="flex justify-between text-[11px] font-mono text-on-surface-variant">
          <span>{label}</span>
          <span>{Math.round(value * 100)}%</span>
        </div>
      )}
      <div className="h-1.5 rounded bg-surface-dim border border-outline overflow-hidden">
        <div className="h-full bg-cadmium-amber transition-all" style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
      </div>
    </div>
  );
}

export const btn = {
  primary:
    'inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-mono font-bold text-[11px] uppercase tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed',
  secondary:
    'inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg border border-outline bg-surface-dim hover:border-cadmium-amber text-on-surface font-mono text-[11px] uppercase tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed',
  ghost: 'inline-flex items-center gap-1 text-[11px] font-mono text-on-surface-variant hover:text-on-surface transition-colors disabled:opacity-40',
};
