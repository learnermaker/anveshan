/**
 * Step 2: Perceiving — progress screen.
 * Shows stage text and elapsed time; the expected duration depends on the media kind.
 */

import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

const STAGES = [
  { until: 1.5, label: 'Measuring the file…' },
  { until: 12, label: 'Looking and listening (AI)…' },
  { until: 999, label: 'Structuring the skill…' },
];

interface Props {
  since: number;
  mime?: string;
}

/** Typical live durations (docs/validation/experiments.md E6): video compose ~20–60 s for up to 10 min of footage. */
function expected(mime?: string): { text: string; sec: number } {
  if (mime?.startsWith('video/')) return { text: 'videos usually take 20–90 s', sec: 90 };
  if (mime?.startsWith('audio/')) return { text: 'audio usually takes 10–30 s', sec: 30 };
  return { text: 'usually 10–30 s', sec: 30 };
}

export function StepPerceiving({ since, mime }: Props) {
  const [, tick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tick((x) => x + 1), 500);
    return () => clearInterval(id);
  }, []);

  const elapsed = (Date.now() - since) / 1000;
  const stage = STAGES.find((s) => elapsed < s.until) ?? STAGES[STAGES.length - 1];
  const exp = expected(mime);

  return (
    <div className="flex flex-col items-center gap-6 py-16 animate-fade-in">
      <Loader2 className="w-8 h-8 text-cadmium-amber animate-spin" />
      <div className="space-y-2 text-center">
        <div className="text-[11px] font-mono uppercase tracking-widest text-cadmium-amber font-bold">Composer · Analysing</div>
        <p className="text-lg font-serif text-on-surface">{stage.label}</p>
        <p className="text-sm text-on-surface-variant">{elapsed.toFixed(0)} s elapsed · {exp.text}</p>
      </div>
      <div className="w-full max-w-sm h-1.5 rounded bg-surface-dim border border-outline overflow-hidden">
        <div
          className="h-full bg-cadmium-amber transition-all duration-500"
          style={{ width: `${Math.min(95, (elapsed / exp.sec) * 100)}%` }}
        />
      </div>
      <p className="text-[11px] font-mono text-on-surface-variant max-w-sm text-center">
        AI-perceived elements will be labelled INFERRED and require your review before use.
      </p>
    </div>
  );
}
