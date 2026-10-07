/**
 * Step 3b: Needs input — AI couldn't determine the skill type alone.
 * Title and description are required to refine the draft.
 */

import React, { useState } from 'react';
import type { DraftView } from '../../api/types';
import { ErrorNote, Spinner } from '../../hero/ui';

interface Props {
  draft: DraftView;
  onRefine: (draft: DraftView, title: string, description: string) => void;
  onStartOver: () => void;
  error: unknown;
}

export function StepNeedsInput({ draft, onRefine, onStartOver, error }: Props) {
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [busy, setBusy] = useState(false);

  const canRefine = title.trim().length > 0 && desc.trim().length > 0;

  const handleRefine = async () => {
    if (!canRefine) return;
    setBusy(true);
    try {
      await onRefine(draft, title.trim(), desc.trim());
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-xl mx-auto animate-fade-in">
      <div className="space-y-1">
        <div className="text-[11px] font-mono uppercase tracking-widest text-cadmium-amber font-bold">Composer · Step 3b — More context needed</div>
        <h2 className="text-2xl font-serif text-on-surface">Tell us about this skill</h2>
      </div>

      {draft.warnings.map((w, i) => (
        <p key={i} className="text-[11px] font-mono text-cadmium-amber">⚠ {w}</p>
      ))}

      {draft.intake.skill_kind && (
        <p className="text-sm text-on-surface-variant">
          The AI thinks this is <span className="font-mono text-on-surface">{draft.intake.skill_kind}</span> (INFERRED) — but needs more context to propose a teachable structure.
        </p>
      )}

      {draft.intake.teachable_reason && (
        <p className="text-sm text-on-surface-variant">Reason: {draft.intake.teachable_reason}</p>
      )}

      <div className="space-y-3">
        <div>
          <label htmlFor="refine-title" className="block text-[11px] font-mono uppercase text-on-surface-variant mb-1">
            Skill title (required)
          </label>
          <input
            id="refine-title"
            value={title}
            maxLength={60}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Watercolour wet-on-wet blending"
            className="w-full bg-surface-dim border border-outline rounded-lg px-3 py-2 text-sm outline-none focus:border-caliper-cyan"
            aria-required="true"
          />
        </div>
        <div>
          <label htmlFor="refine-desc" className="block text-[11px] font-mono uppercase text-on-surface-variant mb-1">
            What should a learner achieve? (required)
          </label>
          <textarea
            id="refine-desc"
            value={desc}
            maxLength={300}
            rows={3}
            onChange={(e) => setDesc(e.target.value)}
            placeholder="Describe the specific skill a learner should be able to reproduce"
            className="w-full bg-surface-dim border border-outline rounded-lg px-3 py-2 text-sm outline-none focus:border-caliper-cyan resize-none"
            aria-required="true"
          />
        </div>
      </div>

      <ErrorNote error={error} />

      <div className="flex items-center gap-3">
        {busy ? (
          <Spinner label="Analysing with your input…" />
        ) : (
          <>
            <button
              onClick={() => void handleRefine()}
              disabled={!canRefine}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-mono font-bold text-[11px] uppercase tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Continue
            </button>
            <button onClick={onStartOver} className="text-[11px] font-mono text-on-surface-variant hover:text-on-surface">
              Start over
            </button>
          </>
        )}
      </div>
    </div>
  );
}
