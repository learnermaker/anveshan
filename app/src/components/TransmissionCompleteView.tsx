import React from 'react';
import { ArrowRight, Award, CheckCircle2, GitBranch, Layers, RotateCcw, ShieldCheck, Sparkles, TrendingUp } from 'lucide-react';
import type { CapabilityCase } from '../types/workspace';

interface TransmissionCompleteViewProps {
  capCase: CapabilityCase;
  onOpenLineage: () => void;
  onRestartCase: () => void;
  onExploreMore: () => void;
}

export function TransmissionCompleteView({
  capCase,
  onOpenLineage,
  onRestartCase,
  onExploreMore,
}: TransmissionCompleteViewProps) {
  const telemetry = capCase.telemetry;
  const metrics = telemetry.metrics;
  const record = telemetry.record;

  return (
    <div className="flex flex-col gap-8 max-w-4xl w-full mx-auto p-4 lg:p-8 animate-fade-in text-on-surface">
      {/* Hero Completion Card */}
      <div className="p-8 rounded-2xl bg-surface-elevated border border-transmission-emerald/50 shadow-2xl relative overflow-hidden text-center space-y-6">
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-transmission-emerald via-cadmium-amber to-caliper-cyan" />

        <div className="w-16 h-16 rounded-2xl bg-transmission-emerald/20 border border-transmission-emerald/40 flex items-center justify-center text-transmission-emerald mx-auto shadow-xl">
          <Award className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <div className="text-xs font-mono uppercase tracking-widest text-transmission-emerald font-bold">
            STAGE 03 // SYNTHETIC REPLAY TRANSMISSION RECORD
          </div>
          <h1 className="text-3xl sm:text-4xl font-serif font-normal text-on-surface">
            Transmission Event Recorded
          </h1>
          <p className="text-sm text-on-surface-variant max-w-lg mx-auto">
            Replay fixture: rubric-level change recorded between baseline and retry between synthetic expert <strong className="text-on-surface">{capCase.expertName}</strong> and learner <strong className="text-on-surface">{capCase.learnerName}</strong>.
          </p>
        </div>

        {/* Transmission Gain Metric Box */}
        <div className="p-6 bg-surface-dim rounded-xl border border-outline/50 max-w-md mx-auto flex items-center justify-between gap-6">
          <div className="text-left space-y-1">
            <div className="text-[10px] font-mono uppercase text-on-surface-variant">BASELINE ATTEMPT</div>
            <div className="text-xl font-mono font-bold text-on-surface-variant">
              {metrics.baselineScore.toFixed(1)} / {metrics.maxPossibleScore.toFixed(1)}
            </div>
          </div>

          <div className="flex flex-col items-center">
            <span className="text-xs font-mono font-bold text-transmission-emerald flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              GAIN
            </span>
            <div className="text-3xl font-mono font-bold text-transmission-emerald">
              +{metrics.gainPoints.toFixed(1)}
            </div>
            <span className="text-[10px] font-mono text-transmission-emerald">
              (+{metrics.gainPercentage}%)
            </span>
          </div>

          <div className="text-right space-y-1">
            <div className="text-[10px] font-mono uppercase text-on-surface-variant">RETRY (REPLAY)</div>
            <div className="text-xl font-mono font-bold text-transmission-emerald">
              {metrics.retryScore.toFixed(1)} / {metrics.maxPossibleScore.toFixed(1)}
            </div>
          </div>
        </div>

        {/* Improved Criteria Breakdown */}
        <div className="space-y-2 max-w-lg mx-auto text-left">
          <div className="text-xs font-mono font-bold text-on-surface uppercase">
            Criteria Improved in Rubric:
          </div>
          <div className="space-y-1.5">
            {record.criteria_improved?.map((critId) => {
              const comp = telemetry.criteriaComparisons.find((c) => c.criterionId === critId);
              return (
                <div
                  key={critId}
                  className="p-2.5 bg-surface-elevated rounded border border-transmission-emerald/30 flex items-center justify-between text-xs"
                >
                  <span className="font-semibold text-on-surface flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-transmission-emerald" />
                    {comp?.name ?? critId}
                  </span>
                  <span className="font-mono text-transmission-emerald font-bold">
                    {comp?.baselineScore} → {comp?.retryScore} pts
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Cryptographic Lineage Hash */}
        <div className="p-3 bg-surface-dim/80 rounded border border-outline/40 font-mono text-[11px] text-on-surface-variant max-w-lg mx-auto flex items-center justify-between">
          <span>MERKLE ROOT: {record.lineage.provenance_hash}</span>
          <span className="text-transmission-emerald font-bold">IMMUTABLE</span>
        </div>

        {/* Primary Actions */}
        <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
          <button
            onClick={onOpenLineage}
            className="px-5 py-2.5 rounded-lg bg-surface-dim border border-outline hover:border-outline-variant font-mono text-xs font-bold text-on-surface flex items-center gap-2 transition-colors"
          >
            <GitBranch className="w-4 h-4 text-caliper-cyan" />
            <span>INSPECT PROVENANCE DAG</span>
          </button>

          <button
            onClick={onExploreMore}
            className="px-6 py-2.5 rounded-lg bg-transmission-emerald hover:bg-transmission-emerald/90 text-background font-mono font-bold text-xs uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-transmission-emerald/20 transition-all hover:scale-[1.02]"
          >
            <span>EXPLORE NEXT CAPABILITY</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
