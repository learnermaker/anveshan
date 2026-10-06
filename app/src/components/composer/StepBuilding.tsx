/**
 * Step 4: Building — creating the skill from the confirmed draft.
 */

import React from 'react';
import { Loader2 } from 'lucide-react';

interface Props {
  progress: number;
}

export function StepBuilding({ progress }: Props) {
  return (
    <div className="flex flex-col items-center gap-6 py-16 animate-fade-in">
      <Loader2 className="w-8 h-8 text-cadmium-amber animate-spin" />
      <div className="space-y-2 text-center">
        <div className="text-[10px] font-mono uppercase tracking-widest text-cadmium-amber font-bold">Composer · Building</div>
        <p className="text-lg font-serif text-on-surface">Creating your skill…</p>
        <p className="text-sm text-on-surface-variant">Generating rubric, knowledge package and goal model.</p>
      </div>
      <div className="w-full max-w-sm h-1.5 rounded bg-surface-dim border border-outline overflow-hidden">
        <div
          className="h-full bg-cadmium-amber transition-all duration-500"
          style={{ width: `${Math.max(5, Math.min(95, progress * 100))}%` }}
        />
      </div>
    </div>
  );
}
