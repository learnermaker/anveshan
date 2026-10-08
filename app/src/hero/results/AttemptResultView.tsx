/** Attempt results: progress curve (hero), first divergence, criteria, feedback, unscored drill. */

import React, { useState } from 'react';
import { Dumbbell, MessageSquareText, RotateCcw } from 'lucide-react';
import type { AttemptResult, CaseView } from '../../api/types';
import type { LocalAttemptMedia } from '../session';
import { ProgressCurve } from './ProgressCurve';
import { FirstDivergenceCard } from './FirstDivergenceCard';
import { Badge, Panel, RuntimeClassBadge, StatusBadge } from '../ui';
import { fmtPosition } from '../locators';
import { OriginBadge, StepStrip, criterionMetricIds, isUniversalView } from '../universal/ResultExtras';
import { DEBUG } from '../../api/debug';
import { attemptLabel, STATUS_PLAIN } from '../../copy/plain';
import { WhyThisFeedback } from '../WhyThisFeedback';
import { HowChecked } from './HowChecked';

interface Props {
  view: CaseView;
  result: AttemptResult;
  media: LocalAttemptMedia;
}

const EVENTS_SHOWN = 6;

export function AttemptResultView({ view, result, media }: Props) {
  const t = result.trajectory;
  const ev = result.evaluation;
  const maxScore = view.rubric.criteria.reduce((s, c) => s + c.weight, 0);
  const universal = isUniversalView(view);
  const metricIds = universal ? criterionMetricIds(view) : {};
  const label = attemptLabel(result.attempt.attempt_number ?? (result.attempt.attempt_type === 'baseline' ? 1 : 2));
  const [showTemplate, setShowTemplate] = useState(false);
  const aiWorded = result.coaching?.status === 'ai_worded';
  const [allEvents, setAllEvents] = useState(false);
  const shownEvents = allEvents ? t.events : t.events.slice(0, EVENTS_SHOWN);

  return (
    <div className="space-y-5">
      <Panel
        kicker={`${label} · result`}
        title={t.process_observable ? 'How your attempt progressed toward the goal' : 'Finished result only (we could not see how you got there)'}
        right={
          <>
            {DEBUG && <RuntimeClassBadge value={result.runtime_class} />}
            <Badge tone={ev.passed ? 'emerald' : 'amber'}>{ev.passed ? 'all required checks met' : 'some required checks not met yet'}</Badge>
            <span className="text-[11px] font-mono text-on-surface">
              {ev.total_score.toFixed(1)} / {maxScore.toFixed(1)}
            </span>
          </>
        }
      >
        <ProgressCurve
          kind={t.curve_kind}
          series={[{ id: 'a', label: `${label} progress`, points: t.curve, color: (result.attempt.attempt_type === 'baseline') ? '#e67e22' : '#10b981', events: t.events }]}
          firstDivergence={result.first_divergence?.position ?? null}
        />
        {t.events.length > 0 && (
          <ul className="mt-3 space-y-1 text-[11px]">
            {shownEvents.map((e, i) => (
              <li key={i} className="flex flex-wrap gap-2 items-baseline">
                <span className={`font-mono ${e.severity === 'material' ? 'text-divergence-crimson' : 'text-[#f39c12]'}`}>▼ {fmtPosition(e.position, e.position_kind)}</span>
                {DEBUG && <code className="font-mono text-on-surface-variant">{e.kind}</code>}
                <span className="text-on-surface" data-plain-exempt>{e.detail}</span>
              </li>
            ))}
            {t.events.length > EVENTS_SHOWN && (
              <li>
                <button type="button" className="text-[11px] font-mono uppercase tracking-wider text-caliper-cyan hover:underline" onClick={() => setAllEvents((v) => !v)}>
                  {allEvents ? 'Show fewer events' : `Show all ${t.events.length} events`}
                </button>
              </li>
            )}
          </ul>
        )}
        {DEBUG && result.warnings.length > 0 && (
          <ul className="mt-3 text-[11px] font-mono text-cadmium-amber space-y-0.5">
            {result.warnings.map((w, i) => <li key={i}>⚠ {w}</li>)}
          </ul>
        )}
      </Panel>

      {universal && media.kind === 'video' && (
        <Panel kicker="Video attempt" title="Step strip"><StepStrip view={view} result={result} /></Panel>
      )}

      <FirstDivergenceCard view={view} result={result} media={media} />

      <Panel kicker="Checked by fixed rules" title="Check · Result · Score · What we found">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[11px] font-mono uppercase text-on-surface-variant text-left border-b border-outline">
                <th className="py-1.5 pr-3">Check</th>
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
                      <div className="font-semibold text-on-surface">{c.name}</div>
                      {DEBUG ? (
                        <div className="text-[11px] font-mono text-on-surface-variant">
                          {c.criterion_id}{c.required ? ' · required' : ''}
                        </div>
                      ) : (
                        c.required && <div className="text-[11px] text-on-surface-variant">Required</div>
                      )}
                      {universal && DEBUG && <div className="mt-1"><OriginBadge metricId={metricIds[c.criterion_id]} /></div>}
                    </td>
                    <td className="py-2 pr-3">{r ? <StatusBadge status={r.status} /> : <span className="text-on-surface-variant">—</span>}</td>
                    <td className="py-2 pr-3 text-right font-mono whitespace-nowrap">{r ? `${r.score.toFixed(1)} / ${c.weight}` : '—'}</td>
                    <td className="py-2 text-on-surface-variant">
                      <span data-plain-exempt>{r?.observed_finding}</span>
                      {r?.status === 'uncertain' && (
                        <div className="text-[11px] font-mono text-cadmium-amber mt-0.5">{STATUS_PLAIN['uncertain']}: {r.deviation_analysis ?? 'evidence insufficient'}</div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {DEBUG ? (
          <p className="mt-2 text-xs text-on-surface-variant">Scores come from measured metrics through fixed bands. No model authors a score; UNCERTAIN scores zero and is reported, not hidden.</p>
        ) : (
          <p className="mt-2 text-xs text-on-surface-variant">Each check is scored by fixed rules from what was measured. The AI never sets a score; when we couldn't tell, the check scores zero and says so.</p>
        )}
      </Panel>

      {result.feedback && (
        <Panel
          kicker="What to change next time"
          title={<span className="flex items-center gap-2"><MessageSquareText className="w-4 h-4 text-cadmium-amber" aria-hidden="true" />{result.feedback.summary}</span>}
          right={
            aiWorded ? (
              <span className="flex items-center gap-2">
                <Badge tone="cyan" title="Worded by AI from the measured findings; scores are not affected.">
                  Advice worded by AI
                </Badge>
                <button type="button" className="text-xs text-caliper-cyan hover:underline" onClick={() => setShowTemplate((v) => !v)}>
                  {showTemplate ? 'Show AI wording' : 'Show plain version'}
                </button>
              </span>
            ) : undefined
          }
        >
          <ul className="space-y-3">
            {result.feedback.items.map((it, i) => {
              const map = view.criterion_map?.criteria[it.criterion_id];
              const criterionName = view.rubric.criteria.find((c) => c.criterion_id === it.criterion_id)?.name;
              return (
                <li key={i} className="p-3 rounded-lg bg-surface-dim border border-outline/60 text-xs space-y-1.5">
                  {criterionName && <div className="font-semibold text-on-surface text-sm">{criterionName}</div>}
                  {DEBUG && (
                    <div className="flex flex-wrap items-center gap-2">
                      <code className="text-[11px] font-mono text-caliper-cyan">{it.criterion_id}</code>
                      {map?.source_claim_ids.map((id) => (
                        <span key={id} title={view.package.claims.find((c) => c.claim_id === id)?.statement} className="text-[11px] font-mono text-on-surface-variant">
                          cites {id}
                        </span>
                      ))}
                    </div>
                  )}
                  <p><span className="text-[11px] font-mono uppercase text-on-surface-variant mr-1">What we saw</span><span data-plain-exempt>{it.what_was_observed}</span></p>
                  <p><span className="text-[11px] font-mono uppercase text-on-surface-variant mr-1">Gap</span><span data-plain-exempt>{it.what_differed}</span></p>
                  <p className="text-cadmium-amber"><span className="text-[11px] font-mono uppercase text-on-surface-variant mr-1">Try</span><span data-plain-exempt>{showTemplate ? result.coaching?.template_advice?.[it.criterion_id] ?? it.corrective_advice : it.corrective_advice}</span></p>
                  <WhyThisFeedback
                    view={view}
                    claimIds={map?.source_claim_ids ?? []}
                    measured={it.what_was_observed}
                    aiWorded={aiWorded}
                  />
                </li>
              );
            })}
          </ul>
        </Panel>
      )}

      {result.drill && <DrillCard view={view} drill={result.drill} />}

      <HowChecked view={view} result={result} media={media} />
    </div>
  );
}

function DrillCard({ view, drill }: { view: CaseView; drill: NonNullable<AttemptResult['drill']> }) {
  return (
    <Panel
      kicker="Practice exercise"
      title={<span className="flex items-center gap-2"><Dumbbell className="w-4 h-4 text-caliper-cyan" />{drill.title ?? 'Focused drill'}</span>}
      right={<Badge tone="muted">Not scored</Badge>}
    >
      <div className="space-y-2 text-sm">
        <p className="text-on-surface leading-relaxed" data-plain-exempt>{drill.instruction ?? drill.instructions ?? drill.drill_hint ?? 'Repeat the step where you first went off track, slowly, before the retry.'}</p>
        {drill.success_hint && (
          <p className="text-on-surface-variant">
            <span className="text-[11px] font-mono uppercase mr-1">You have it when</span>
            <span data-plain-exempt>{drill.success_hint}</span>
          </p>
        )}
        {DEBUG && drill.source_claim_ids && drill.source_claim_ids.length > 0 && (
          <p className="text-[11px] font-mono text-on-surface-variant">
            Grounded in {drill.source_claim_ids.map((id) => (
              <span key={id} className="text-caliper-cyan mr-1" title={view.package.claims.find((c) => c.claim_id === id)?.statement}>{id}</span>
            ))}
          </p>
        )}
        {!DEBUG && drill.source_claim_ids && drill.source_claim_ids.length > 0 && (
          <WhyThisFeedback view={view} claimIds={drill.source_claim_ids ?? []} />
        )}
        <p className="text-xs text-on-surface-variant flex items-center gap-1">
          <RotateCcw className="w-3 h-3" /> This exercise is not scored. Only your second try of the whole task is checked.
        </p>
      </div>
    </Panel>
  );
}
