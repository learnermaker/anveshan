/**
 * Step 3a: Refused — source was rejected by safety or teachability gate.
 * Shows the refusal message and intake reasons. No way to continue.
 */

import React from 'react';
import type { DraftView } from '../../api/types';

interface Props {
  draft: DraftView;
  onStartOver: () => void;
}

export function StepRefused({ draft, onStartOver }: Props) {
  const safety = draft.intake.safety as { decision?: string; categories?: string[] };
  const reasons: string[] = [];
  if (draft.intake.teachable_reason) reasons.push(draft.intake.teachable_reason);
  if (safety.categories?.length && !safety.categories.includes('none')) reasons.push(`Safety categories: ${safety.categories.join(', ')}`);

  return (
    <div className="flex flex-col gap-6 max-w-xl mx-auto animate-fade-in">
      <div className="space-y-1">
        <div className="text-[11px] font-mono uppercase tracking-widest text-divergence-crimson font-bold">Composer · Cannot use this file</div>
        <h2 className="text-2xl font-serif text-on-surface">Source refused</h2>
      </div>

      <div className="p-4 rounded-xl border border-divergence-crimson/40 bg-divergence-crimson/10 space-y-3">
        <p className="text-sm text-on-surface font-medium">{draft.refusal_message ?? "We can't use this file."}</p>
        {reasons.length > 0 && (
          <ul className="space-y-1 text-[11px] font-mono text-on-surface-variant">
            {reasons.map((r, i) => <li key={i}>· {r}</li>)}
          </ul>
        )}
      </div>

      <div className="p-3 rounded-lg border border-outline bg-surface-dim text-[11px] font-mono text-on-surface-variant space-y-1">
        <div className="font-bold uppercase text-[11px] tracking-wider">Probe facts</div>
        <div>Type: {draft.probe.mime_type} · {(draft.probe.bytes / 1e6).toFixed(2)} MB</div>
        {draft.probe.duration_sec != null && <div>Duration: {draft.probe.duration_sec.toFixed(1)} s</div>}
        {draft.probe.width != null && <div>Dimensions: {draft.probe.width}×{draft.probe.height}</div>}
      </div>

      <button
        onClick={onStartOver}
        className="self-start inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-mono font-bold text-[11px] uppercase tracking-wider transition-colors"
      >
        Try another file
      </button>
    </div>
  );
}
