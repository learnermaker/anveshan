/** Universal-case result extras: MEASURED vs AI-JUDGED criterion badges and a video step strip (DEBUG only). */
import React from 'react';
import type { AttemptResult, CaseView, UniversalUiView } from '../../api/types';
import { Badge } from '../ui';
import { DEBUG } from '../../api/debug';

const MEASURED_MARKERS = ['u.step_', 'u.off_path', 'u.final_similarity', 'rhythm:', 'line_art'];
const JUDGED_MARKERS = ['u.final_property.', 'u.final_state_match', 'u.step_quality.'];

export type MetricOrigin = 'measured' | 'judged' | null;

/** AI-judged markers win over measured ones (u.step_quality.* also contains "u.step_"). */
export function metricOrigin(metricId: string | undefined): MetricOrigin {
  if (!metricId) return null;
  if (JUDGED_MARKERS.some((m) => metricId.includes(m))) return 'judged';
  if (MEASURED_MARKERS.some((m) => metricId.includes(m))) return 'measured';
  return null;
}

export function isUniversalView(view: CaseView): boolean {
  const ui = view.goal.ui_view as Partial<UniversalUiView> & { kind?: string };
  return ui.kind === 'universal' || (view.profile != null && Array.isArray(ui.checks));
}

/** criterion_id -> metric_id, for criteria named CRIT-U-<check_id>. */
export function criterionMetricIds(view: CaseView): Record<string, string> {
  const ui = view.goal.ui_view as UniversalUiView;
  const out: Record<string, string> = {};
  for (const c of ui.checks ?? []) if (c.metric_id) out[`CRIT-U-${c.check_id}`] = c.metric_id;
  return out;
}

export function OriginBadge({ metricId }: { metricId: string | undefined }) {
  if (!DEBUG) return null;
  const o = metricOrigin(metricId);
  if (o === 'measured') return <Badge tone="emerald" title={`Computed deterministically (${metricId})`}>MEASURED</Badge>;
  if (o === 'judged') return <Badge tone="amber" title={`Judged by a model (${metricId})`}>AI-JUDGED</Badge>;
  return null;
}

/** Step strip for video attempts: steps reported missing and off-path moments. */
export function StepStrip({ view, result }: { view: CaseView; result: AttemptResult }) {
  const ui = view.goal.ui_view as UniversalUiView;
  const steps = ui.steps ?? [];
  const events = result.trajectory.events;
  const missing = new Set<number>();
  for (const e of events) {
    if (e.kind !== 'missing_state') continue;
    const m = /step\s+(\d+)/i.exec(e.detail);
    if (m) missing.add(Number(m[1]));
  }
  const offPath = events.filter((e) => e.kind === 'off_path_state');
  if (steps.length === 0 && offPath.length === 0) return null;

  return (
    <div className="space-y-2" aria-label="Step strip">
      <div className="text-[9px] font-mono uppercase text-on-surface-variant">Steps in your attempt</div>
      <div className="flex gap-1.5 overflow-x-auto pb-1">
        {steps.map((s, i) => {
          const miss = missing.has(i);
          return (
            <div key={s.step_id} className={`shrink-0 w-24 p-1.5 rounded border text-[9px] font-mono leading-tight ${miss ? 'border-divergence-crimson/50 bg-divergence-crimson/10 text-divergence-crimson' : 'border-transmission-emerald/40 bg-transmission-emerald/10 text-on-surface'}`}>
              <div className="font-bold">{i + 1}. {miss ? 'MISSING' : 'seen'}</div>
              <div className="truncate" title={s.name}>{s.name}</div>
            </div>
          );
        })}
      </div>
      {offPath.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {offPath.map((e, i) => (
            <li key={i}><Badge tone="amber" title={e.detail}>off-path from {e.position.toFixed(0)} s</Badge></li>
          ))}
        </ul>
      )}
    </div>
  );
}
