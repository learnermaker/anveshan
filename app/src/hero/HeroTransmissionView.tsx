/** Step 3 RESULTS for a live case: what to do next, baseline vs retry curves, gains, transitions, record. */

import React from 'react';
import { ArrowLeft, ArrowRight, Compass, GitBranch, Layers, RotateCcw, Target } from 'lucide-react';
import type { CaseView } from '../api/types';
import type { HeroSession } from './session';
import { ProgressCurve } from './results/ProgressCurve';
import { Badge, btn, Panel, StatusBadge } from './ui';
import { TrustLine } from './TrustLine';
import { DEBUG } from '../api/debug';
import { attemptLabel } from '../copy/plain';

interface Props {
  view: CaseView;
  session: HeroSession | null;
  onBackToPractice: () => void;
  /** discard the session and start a fresh baseline */
  onPractiseAgain?: () => void;
  onStudySource?: () => void;
  onExploreMore: () => void;
}

const TRANSITION_TONE: Record<string, 'emerald' | 'crimson' | 'cyan' | 'muted' | 'amber'> = {
  improved: 'emerald',
  regressed: 'crimson',
  observability_gain: 'cyan', // real service name
  observability_gained: 'cyan', // legacy mock name (kept for backward compat)
  observability_loss: 'amber', // real service name
  observability_lost: 'amber', // legacy mock name (kept for backward compat)
  unchanged: 'muted',
};

const signed = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`;
const scoreTone = (v: number) => (v > 0 ? 'text-transmission-emerald' : v < 0 ? 'text-divergence-crimson' : 'text-on-surface');

export function HeroTransmissionView({ view, session, onBackToPractice, onPractiseAgain, onStudySource, onExploreMore }: Props) {
  const res = session?.result;
  if (!session || !res) {
    const n = session?.attempts.length ?? 0;
    const status =
      n === 0
        ? 'You have not submitted an attempt yet.'
        : n === 1
          ? 'You have done your first try. Read its feedback, then do the whole task once more.'
          : 'Both tries are done. Press "See what changed" in Practise to save the record.';
    return (
      <div className="max-w-xl mx-auto w-full p-6 text-center space-y-3 animate-fade-in">
        <div className="text-xs font-mono uppercase tracking-widest text-cadmium-amber font-bold">Step 3 of 3 · Results</div>
        <h1 className="font-serif text-2xl">Results appear after two tries</h1>
        <p className="text-sm text-on-surface-variant">Results compare your first try with one full retry, check by check. {status}</p>
        <div className="flex justify-center gap-1 text-sm" aria-label={`${Math.min(n, 2)} of 2 tries done`}>
          {[0, 1].map((i) => (
            <span
              key={i}
              className={`px-2 py-0.5 rounded-full border ${i < n ? 'border-transmission-emerald/50 text-transmission-emerald' : 'border-outline text-on-surface-variant'}`}
            >
              {attemptLabel(i + 1)} {i < n ? '✓' : ''}
            </span>
          ))}
        </div>
        <button onClick={onBackToPractice} className={btn.primary}>
          {n === 1 ? 'Go to Practise and retry' : 'Go to Practise'} <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  const rec = res.transmission_record;
  const cmp = res.comparison;
  const tc = cmp.targeted_change;
  const baseline = session.attempts[0]?.result;
  const retry = session.attempts[session.attempts.length - 1]?.result;
  const maxScore = view.rubric.criteria.reduce((s, c) => s + c.weight, 0);
  const kind = baseline?.trajectory.curve_kind ?? 'time';
  const targetName = view.rubric.criteria.find((c) => c.criterion_id === tc.criterion_id)?.name ?? tc.criterion_id;
  // Support both real-service (before/after/improved) and legacy mock (baseline_status/retry_status/kind) fields
  const tcBefore = tc.before ?? tc.baseline_status;
  const tcAfter = tc.after ?? tc.retry_status;
  const tcKind = tc.improved !== undefined ? (tc.improved ? 'improved' : 'unchanged') : tc.kind ?? 'changed';

  return (
    <div className="flex flex-col gap-5 w-full animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          <button onClick={onBackToPractice} className={btn.ghost}>
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Practise
          </button>
          <div className="text-xs font-mono uppercase tracking-widest text-transmission-emerald font-bold">Step 3 of 3 · Results recorded</div>
          <h1 className="font-serif text-2xl sm:text-3xl" data-plain-exempt>{view.title}</h1>
          {!DEBUG ? (
            <TrustLine view={view} />
          ) : (
            <div className="flex flex-wrap gap-1.5 items-center">
              {baseline && <span className="text-xs font-mono text-on-surface-variant">attempt 1</span>}
              {baseline && <Badge tone="muted">{baseline.runtime_class}</Badge>}
              {retry && <span className="text-xs font-mono text-on-surface-variant">attempt 2</span>}
              {retry && <Badge tone="muted">{retry.runtime_class}</Badge>}
            </div>
          )}
        </div>
        <button onClick={onExploreMore} className={btn.secondary}>
          All skills <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      <WhatNext
        gain={rec.transmission_gain}
        passed={Boolean(retry?.evaluation.passed)}
        targetChanged={Boolean(tc.criterion_id) && Boolean(tc.changed)}
        targetName={tc.criterion_id ? targetName ?? null : null}
        onPractiseAgain={onPractiseAgain}
        onStudySource={onStudySource}
        onExploreMore={onExploreMore}
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 rounded-xl border border-outline bg-surface-container-low">
          <div className="text-xs font-mono uppercase text-on-surface-variant">Score change</div>
          <div className={`text-4xl font-mono font-bold ${scoreTone(rec.transmission_gain)}`}>{signed(rec.transmission_gain)}</div>
          <div className="text-xs font-mono text-on-surface-variant">
            {rec.baseline_score.toFixed(1)} → {rec.retry_score.toFixed(1)} of {maxScore.toFixed(1)}
          </div>
        </div>
        <div className="p-5 rounded-xl border border-outline bg-surface-container-low">
          <div className="text-xs font-mono uppercase text-on-surface-variant flex items-center gap-1">
            <Target className="w-3 h-3" aria-hidden="true" /> Where you first went off track
          </div>
          {tc.criterion_id ? (
            <>
              <div className="text-sm text-on-surface mt-1">{targetName}</div>
              <div className="flex items-center gap-2 mt-2">
                {tcBefore && <StatusBadge status={tcBefore} />}
                <ArrowRight className="w-3 h-3 text-on-surface-variant" aria-hidden="true" />
                {tcAfter && <StatusBadge status={tcAfter} />}
              </div>
              <div className="text-xs text-on-surface-variant mt-1">{tc.changed ? `Changed on the retry (${tcKind}).` : 'Not fixed on the retry yet.'}</div>
            </>
          ) : (
            <div className="text-sm text-on-surface-variant mt-1">Your first try never clearly went off track, so there was no single thing to fix.</div>
          )}
        </div>
        <div className="p-5 rounded-xl border border-outline bg-surface-container-low">
          <div className="text-xs font-mono uppercase text-on-surface-variant">Change on checks we could judge both times</div>
          <div className={`text-4xl font-mono font-bold ${scoreTone(cmp.skill_gain_excluding_observability)}`}>{signed(cmp.skill_gain_excluding_observability)}</div>
          <div className="text-xs text-on-surface-variant">Leaves out checks we couldn't judge in one of the tries, so clearer recordings alone don't count as improvement.</div>
        </div>
      </div>

      <Panel kicker="First try vs second try" title="Progress toward the goal">
        <ProgressCurve
          kind={kind}
          height={260}
          series={[
            { id: 'b', label: attemptLabel(1), points: cmp.curves.baseline, color: '#e67e22', dashed: true, events: baseline?.trajectory.events },
            { id: 'r', label: attemptLabel(2), points: cmp.curves.retry, color: '#10b981', events: retry?.trajectory.events },
          ]}
          firstDivergence={baseline?.first_divergence?.position ?? null}
        />
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Panel kicker="Check by check" title="What changed between your first and second try">
          <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[11px] font-mono uppercase text-on-surface-variant text-left border-b border-outline">
                <th className="py-1.5 pr-2">Check</th>
                <th className="py-1.5 pr-2">First try</th>
                <th className="py-1.5 pr-2" aria-hidden="true"></th>
                <th className="py-1.5 pr-2">Second try</th>
                <th className="py-1.5"></th>
              </tr>
            </thead>
            <tbody>
              {view.rubric.criteria.map((c) => {
                const b = baseline?.evaluation.criterion_results.find((x) => x.criterion_id === c.criterion_id);
                const r = retry?.evaluation.criterion_results.find((x) => x.criterion_id === c.criterion_id);
                const k = cmp.transitions[c.criterion_id] ?? 'unchanged';
                return (
                  <tr key={c.criterion_id} className="border-b border-outline/40">
                    <td className="py-2 pr-2">
                      <div>{c.name}</div>
                      {DEBUG && <div className="text-[11px] font-mono text-on-surface-variant">{c.criterion_id}</div>}
                    </td>
                    <td className="py-2 pr-2 whitespace-nowrap">{b && <StatusBadge status={b.status} />}</td>
                    <td className="py-2 pr-2 text-on-surface-variant" aria-hidden="true">→</td>
                    <td className="py-2 pr-2 whitespace-nowrap">{r && <StatusBadge status={r.status} />}</td>
                    <td className="py-2 text-right">
                      <Badge tone={TRANSITION_TONE[k] ?? 'muted'}>{k.replace(/_/g, ' ')}</Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
          <p className="mt-2 text-xs text-on-surface-variant">Checks improved: {rec.criteria_improved.length ? rec.criteria_improved.map(id => view.rubric.criteria.find(c => c.criterion_id === id)?.name ?? id).join(', ') : 'none yet'}</p>
        </Panel>

        {DEBUG && (
          <Panel
            kicker="Record (for audit)"
            title={
              <span className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-caliper-cyan" aria-hidden="true" />
                Transmission record
              </span>
            }
          >
            <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-xs font-mono">
              {(
                [
                  ['transmission_id', rec.transmission_id],
                  ['skill_id', rec.skill_id],
                  ['package_id', rec.package_id],
                  ['rubric_id', rec.rubric_id],
                  ['expert_id', rec.expert_id],
                  ['learner_id', rec.learner_id],
                  ['baseline_attempt', rec.baseline_attempt_id],
                  ['retry_attempt', rec.retry_attempt_id],
                  ['recorded_at', rec.lineage.recorded_at],
                  ['parent', rec.lineage.parent_transmission_id ?? '—'],
                  ['provenance_hash', rec.lineage.provenance_hash ?? '—'],
                ] as [string, string][]
              ).map(([k, v]) => (
                <React.Fragment key={k}>
                  <dt className="text-on-surface-variant">{k}</dt>
                  <dd className="text-on-surface break-all">{v}</dd>
                </React.Fragment>
              ))}
            </dl>
            {rec.lineage.adaptation_notes && <p className="mt-2 text-xs text-cadmium-amber">{rec.lineage.adaptation_notes}</p>}
            <p className="mt-2 text-xs text-on-surface-variant">
              The hash identifies this record's inputs. It records that a baseline and a retry were evaluated against this skill; it is not a certification of skill.
            </p>
          </Panel>
        )}
      </div>
    </div>
  );
}

function WhatNext({
  gain,
  passed,
  targetChanged,
  targetName,
  onPractiseAgain,
  onStudySource,
  onExploreMore,
}: {
  gain: number;
  passed: boolean;
  targetChanged: boolean;
  targetName: string | null;
  onPractiseAgain?: () => void;
  onStudySource?: () => void;
  onExploreMore: () => void;
}) {
  let headline: string;
  let body: string;
  if (passed) {
    headline = 'Your retry met every required check.';
    body = 'The skill transferred for this task. Try another skill, or practise again to make it consistent.';
  } else if (gain > 0 || targetChanged) {
    headline = 'Your retry improved.';
    body =
      targetChanged && targetName
        ? `You changed "${targetName}", where you first went off track. Some required checks are still open: practise again to close them.`
        : 'Some checks improved, but not every required check is met yet. Practise again to close the rest.';
  } else {
    headline = 'No change yet. That is normal on a first try.';
    body = targetName
      ? `Focus on "${targetName}", where you first went off track. Study that step in the source, then practise again with a fresh first and second try.`
      : 'Study the steps in the source, then practise again with a fresh first and second try.';
  }
  return (
    <section className="rounded-xl border border-cadmium-amber/40 bg-cadmium-amber/5 p-4 space-y-3" aria-live="polite">
      <div>
        <div className="text-base font-semibold text-on-surface">{headline}</div>
        <p className="text-sm text-on-surface-variant mt-1">{body}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {onPractiseAgain && (
          <button onClick={onPractiseAgain} className={btn.primary}>
            <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" /> Practise again
          </button>
        )}
        {onStudySource && (
          <button onClick={onStudySource} className={btn.secondary}>
            <Compass className="w-3.5 h-3.5" aria-hidden="true" /> Study the source steps
          </button>
        )}
        <button onClick={onExploreMore} className={btn.secondary}>
          <Layers className="w-3.5 h-3.5" aria-hidden="true" /> Try another skill
        </button>
      </div>
    </section>
  );
}
