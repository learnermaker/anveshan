/** Attempt results: progress curve (hero), first divergence, criteria, feedback, unscored drill. */

import React from 'react';
import { Dumbbell, MessageSquareText, RotateCcw } from 'lucide-react';
import type { AttemptResult, CaseView } from '../../api/types';
import type { LocalAttemptMedia } from '../session';
import { ProgressCurve } from './ProgressCurve';
import { FirstDivergenceCard } from './FirstDivergenceCard';
import { Badge, MockBadge, Panel, RuntimeClassBadge, StatusBadge } from '../ui';
import { fmtPosition } from '../locators';
import { OriginBadge, StepStrip, criterionMetricIds, isUniversalView } from '../universal/ResultExtras';

interface Props {
  view: CaseView;
  result: AttemptResult;
  media: LocalAttemptMedia;
}

export function AttemptResultView({ view, result, media }: Props) {
  const t = result.trajectory;
  const ev = result.evaluation;
  const maxScore = view.rubric.criteria.reduce((s, c) => s + c.weight, 0);
  const universal = isUniversalView(view);
  const metricIds = universal ? criterionMetricIds(view) : {};
  const label = result.attempt.attempt_type === 'baseline' ? 'Baseline' : `Retry #${result.attempt.attempt_number - 1}`;

  return (
    <div className="space-y-5">
      <Panel
        kicker={`${label} · progress toward the goal`}
        title={t.process_observable ? 'Trajectory against the goal model' : 'Final state only — process not observable'}
        right={
          <>
            <RuntimeClassBadge value={result.runtime_class} />
            <Badge tone={ev.passed ? 'emerald' : 'amber'}>{ev.passed ? 'required criteria met' : 'required criteria not all met'}</Badge>
            <span className="text-[11px] font-mono text-on-surface">
              {ev.total_score.toFixed(1)} / {maxScore.toFixed(1)}
            </span>
            <MockBadge />
          </>
        }
      >
        <ProgressCurve
          kind={t.curve_kind}
          series={[{ id: 'a', label: `${label} progress`, points: t.curve, color: result.attempt.attempt_type === 'baseline' ? '#e67e22' : '#10b981', events: t.events }]}
          firstDivergence={result.first_divergence?.position ?? null}
        />
        {t.events.length > 0 && (
          <ul className="mt-3 space-y-1 text-[11px]">
            {t.events.map((e, i) => (
              <li key={i} className="flex flex-wrap gap-2 items-baseline">
                <span className={`font-mono ${e.severity === 'material' ? 'text-divergence-crimson' : 'text-[#f39c12]'}`}>▼ {fmtPosition(e.position, e.position_kind)}</span>
                <code className="font-mono text-on-surface-variant">{e.kind}</code>
                <span className="text-on-surface">{e.detail}</span>
              </li>
            ))}
          </ul>
        )}
        {result.warnings.length > 0 && (
          <ul className="mt-3 text-[10px] font-mono text-cadmium-amber space-y-0.5">
            {result.warnings.map((w, i) => <li key={i}>⚠ {w}</li>)}
          </ul>
        )}
      </Panel>

      {universal && media.kind === 'video' && (
        <Panel kicker="Video attempt" title="Step strip"><StepStrip view={view} result={result} /></Panel>
      )}

      <FirstDivergenceCard view={view} result={result} media={media} />

      <Panel kicker="Deterministic score policy" title="Criteria">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[9px] font-mono uppercase text-on-surface-variant text-left border-b border-outline">
                <th className="py-1.5 pr-3">Criterion</th>
                <th className="py-1.5 pr-3">Status</th>
                <th className="py-1.5 pr-3 text-right">Score</th>
                <th className="py-1.5">Finding</th>
              </tr>
            </thead>
            <tbody>
              {view.rubric.criteria.map((c) => {
                const r = ev.criterion_results.find((x) => x.criterion_id === c.criterion_id);
                return (
                  <tr key={c.criterion_id} className="border-b border-outline/40 align-top">
                    <td className="py-2 pr-3">
                      <div className="text-on-surface">{c.name}</div>
                      <div className="text-[9px] font-mono text-on-surface-variant">
                        {c.criterion_id}{c.required ? ' · required' : ''}
                      </div>
                      {universal && <div className="mt-1"><OriginBadge metricId={metricIds[c.criterion_id]} /></div>}
                    </td>
                    <td className="py-2 pr-3">{r ? <StatusBadge status={r.status} /> : <span className="text-on-surface-variant">—</span>}</td>
                    <td className="py-2 pr-3 text-right font-mono whitespace-nowrap">{r ? `${r.score.toFixed(1)} / ${c.weight}` : '—'}</td>
                    <td className="py-2 text-on-surface-variant">
                      {r?.observed_finding}
                      {r?.status === 'uncertain' && (
                        <div className="text-[10px] font-mono text-cadmium-amber mt-0.5">UNCERTAIN: {r.deviation_analysis ?? 'evidence insufficient'}</div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[10px] text-on-surface-variant">Scores come from measured metrics through fixed bands. No model authors a score; UNCERTAIN scores zero and is reported, not hidden.</p>
      </Panel>

      {result.feedback && (
        <Panel kicker="Feedback" title={<span className="flex items-center gap-2"><MessageSquareText className="w-4 h-4 text-cadmium-amber" />{result.feedback.summary}</span>}>
          <ul className="space-y-3">
            {result.feedback.items.map((it, i) => {
              const map = view.criterion_map?.criteria[it.criterion_id];
              return (
                <li key={i} className="p-3 rounded-lg bg-surface-dim border border-outline/60 text-xs space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <code className="text-[10px] font-mono text-caliper-cyan">{it.criterion_id}</code>
                    {map?.source_claim_ids.map((id) => (
                      <span key={id} title={view.package.claims.find((c) => c.claim_id === id)?.statement} className="text-[10px] font-mono text-on-surface-variant">
                        cites {id}
                      </span>
                    ))}
                  </div>
                  <p><span className="text-[9px] font-mono uppercase text-on-surface-variant mr-1">Observed</span>{it.what_was_observed}</p>
                  <p><span className="text-[9px] font-mono uppercase text-on-surface-variant mr-1">Differed</span>{it.what_differed}</p>
                  <p className="text-cadmium-amber"><span className="text-[9px] font-mono uppercase text-on-surface-variant mr-1">Try</span>{it.corrective_advice}</p>
                </li>
              );
            })}
          </ul>
        </Panel>
      )}

      {result.drill && <DrillCard view={view} drill={result.drill} />}
    </div>
  );
}

function DrillCard({ view, drill }: { view: CaseView; drill: NonNullable<AttemptResult['drill']> }) {
  return (
    <Panel
      kicker="Micro-drill"
      title={<span className="flex items-center gap-2"><Dumbbell className="w-4 h-4 text-caliper-cyan" />{drill.title ?? 'Focused drill'}</span>}
      right={<Badge tone="muted">UNSCORED · guidance only</Badge>}
    >
      <div className="space-y-2 text-xs">
        <p className="text-on-surface leading-relaxed">{drill.instructions ?? drill.drill_hint}</p>
        {drill.source_claim_ids && drill.source_claim_ids.length > 0 && (
          <p className="text-[10px] font-mono text-on-surface-variant">
            Grounded in {drill.source_claim_ids.map((id) => (
              <span key={id} className="text-caliper-cyan mr-1" title={view.package.claims.find((c) => c.claim_id === id)?.statement}>{id}</span>
            ))}
          </p>
        )}
        <p className="text-[10px] text-on-surface-variant flex items-center gap-1">
          <RotateCcw className="w-3 h-3" /> The drill awards nothing. Only the full retry below is evaluated.
        </p>
      </div>
    </Panel>
  );
}
