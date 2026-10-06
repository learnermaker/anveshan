/** 03 TRANSMISSION for a live hero case: baseline vs retry curves, gains, transitions, lineage. */

import React from 'react';
import { ArrowLeft, ArrowRight, GitBranch, Target } from 'lucide-react';
import type { CaseView } from '../api/types';
import type { HeroSession } from './session';
import { ProgressCurve } from './results/ProgressCurve';
import { Badge, btn, MockBadge, Panel, RuntimeClassBadge, SourceLabelBadge, StatusBadge } from './ui';

interface Props {
  view: CaseView;
  session: HeroSession | null;
  onBackToPractice: () => void;
  onExploreMore: () => void;
}

const TRANSITION_TONE: Record<string, 'emerald' | 'crimson' | 'cyan' | 'muted' | 'amber'> = {
  improved: 'emerald',
  regressed: 'crimson',
  observability_gained: 'cyan',
  observability_lost: 'amber',
  unchanged: 'muted',
};

const signed = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}`;

export function HeroTransmissionView({ view, session, onBackToPractice, onExploreMore }: Props) {
  const res = session?.result;
  if (!session || !res) {
    return (
      <div className="max-w-xl mx-auto w-full p-6 text-center space-y-3 animate-fade-in">
        <div className="text-[10px] font-mono uppercase tracking-widest text-cadmium-amber font-bold">03 // TRANSMISSION</div>
        <h1 className="font-serif text-2xl">No completed session yet</h1>
        <p className="text-xs text-on-surface-variant">Submit a baseline and a full retry in PRACTICE, then complete the session. The transmission record is computed only from those two evaluated attempts.</p>
        <button onClick={onBackToPractice} className={btn.primary}>
          Go to practice <ArrowRight className="w-3.5 h-3.5" />
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

  return (
    <div className="flex flex-col gap-5 w-full animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          <button onClick={onBackToPractice} className={btn.ghost}>
            <ArrowLeft className="w-3.5 h-3.5" /> PRACTICE
          </button>
          <div className="text-[10px] font-mono uppercase tracking-widest text-transmission-emerald font-bold">03 // TRANSMISSION RECORDED</div>
          <h1 className="font-serif text-2xl sm:text-3xl">{view.title}</h1>
          <div className="flex flex-wrap gap-1.5 items-center">
            <SourceLabelBadge label={view.runtime_label} />
            {baseline && <span className="text-[9px] font-mono text-on-surface-variant">baseline</span>}
            {baseline && <RuntimeClassBadge value={baseline.runtime_class} />}
            {retry && <span className="text-[9px] font-mono text-on-surface-variant">retry</span>}
            {retry && <RuntimeClassBadge value={retry.runtime_class} />}
            <MockBadge />
          </div>
        </div>
        <button onClick={onExploreMore} className={btn.secondary}>
          Portfolio <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 rounded-xl border border-transmission-emerald/40 bg-surface-container-low">
          <div className="text-[9px] font-mono uppercase text-on-surface-variant">Contract gain (TransmissionRecord)</div>
          <div className={`text-4xl font-mono font-bold ${rec.transmission_gain >= 0 ? 'text-transmission-emerald' : 'text-divergence-crimson'}`}>{signed(rec.transmission_gain)}</div>
          <div className="text-[11px] font-mono text-on-surface-variant">
            {rec.baseline_score.toFixed(1)} → {rec.retry_score.toFixed(1)} of {maxScore.toFixed(1)}
          </div>
        </div>
        <div className="p-5 rounded-xl border border-outline bg-surface-container-low">
          <div className="text-[9px] font-mono uppercase text-on-surface-variant flex items-center gap-1"><Target className="w-3 h-3" /> Targeted change (baseline first divergence)</div>
          {tc.criterion_id ? (
            <>
              <div className="text-sm text-on-surface mt-1">{targetName}</div>
              <div className="flex items-center gap-2 mt-2">
                {tc.baseline_status && <StatusBadge status={tc.baseline_status} />}
                <ArrowRight className="w-3 h-3 text-on-surface-variant" />
                {tc.retry_status && <StatusBadge status={tc.retry_status} />}
              </div>
              <div className="text-[10px] font-mono text-on-surface-variant mt-1">{tc.changed ? `changed (${tc.kind ?? 'changed'})` : 'did not change'}</div>
            </>
          ) : (
            <div className="text-xs text-on-surface-variant mt-1">No baseline divergence was established, so no targeted change is claimed.</div>
          )}
        </div>
        <div className="p-5 rounded-xl border border-outline bg-surface-container-low">
          <div className="text-[9px] font-mono uppercase text-on-surface-variant">Skill gain excluding observability</div>
          <div className="text-4xl font-mono font-bold text-caliper-cyan">{signed(cmp.skill_gain_excluding_observability)}</div>
          <div className="text-[10px] text-on-surface-variant">Only criteria assessable in both attempts; UNCERTAIN → known changes are excluded.</div>
        </div>
      </div>

      <Panel kicker="Baseline vs retry" title="Progress toward the goal">
        <ProgressCurve
          kind={kind}
          height={260}
          series={[
            { id: 'b', label: 'Baseline', points: cmp.curves.baseline, color: '#e67e22', dashed: true, events: baseline?.trajectory.events },
            { id: 'r', label: 'Retry', points: cmp.curves.retry, color: '#10b981', events: retry?.trajectory.events },
          ]}
          firstDivergence={baseline?.first_divergence?.position ?? null}
        />
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Panel kicker="Criteria transitions" title="What changed, criterion by criterion">
          <table className="w-full text-xs">
            <tbody>
              {view.rubric.criteria.map((c) => {
                const b = baseline?.evaluation.criterion_results.find((x) => x.criterion_id === c.criterion_id);
                const r = retry?.evaluation.criterion_results.find((x) => x.criterion_id === c.criterion_id);
                const k = cmp.transitions[c.criterion_id] ?? 'unchanged';
                return (
                  <tr key={c.criterion_id} className="border-b border-outline/40">
                    <td className="py-2 pr-2">
                      <div>{c.name}</div>
                      <div className="text-[9px] font-mono text-on-surface-variant">{c.criterion_id}</div>
                    </td>
                    <td className="py-2 pr-2 whitespace-nowrap">{b && <StatusBadge status={b.status} />}</td>
                    <td className="py-2 pr-2 text-on-surface-variant">→</td>
                    <td className="py-2 pr-2 whitespace-nowrap">{r && <StatusBadge status={r.status} />}</td>
                    <td className="py-2 text-right"><Badge tone={TRANSITION_TONE[k] ?? 'muted'}>{k.replace(/_/g, ' ')}</Badge></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-2 text-[10px] text-on-surface-variant">criteria_improved (contract): {rec.criteria_improved.length ? rec.criteria_improved.join(', ') : 'none'}</p>
        </Panel>

        <Panel kicker="Lineage" title={<span className="flex items-center gap-2"><GitBranch className="w-4 h-4 text-caliper-cyan" />TransmissionRecord</span>}>
          <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-[11px] font-mono">
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
          {rec.lineage.adaptation_notes && <p className="mt-2 text-[10px] text-cadmium-amber">{rec.lineage.adaptation_notes}</p>}
          <p className="mt-2 text-[10px] text-on-surface-variant">
            The hash identifies this record’s inputs. It records that a baseline and retry were evaluated against this package; it is not a certification of skill.
          </p>
        </Panel>
      </div>
    </div>
  );
}
