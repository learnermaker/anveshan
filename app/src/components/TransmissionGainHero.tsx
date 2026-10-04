import React from 'react';
import {
  TrendingUp,
  Sparkles,
  ShieldCheck,
  Award,
  ArrowRight,
  Fingerprint,
  FileCheck,
} from 'lucide-react';
import type { TransmissionTelemetry } from '../data/adapter';

interface TransmissionGainHeroProps {
  telemetry: TransmissionTelemetry;
  onOpenLineage: () => void;
}

export const TransmissionGainHero: React.FC<TransmissionGainHeroProps> = ({
  telemetry,
  onOpenLineage,
}) => {
  const metrics = telemetry.metrics;

  return (
    <div className="bg-surface-container-low border border-outline rounded-lg p-5 relative overflow-hidden shadow-2xl">
      {/* Background Accent Gradients */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-transmission-emerald/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-cadmium-amber/5 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col lg:flex-row items-stretch justify-between gap-6">
        {/* Left Column: Quantitative Transmission Hero Callout */}
        <div className="flex-1 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2 h-2 rounded-full bg-transmission-emerald animate-ping" />
              <span className="font-mono text-xs font-bold uppercase tracking-widest text-transmission-emerald">
                TRANSMISSION VERIFICATION COMPLETE
              </span>
              <span className="text-outline text-xs">//</span>
              <span className="font-mono text-[10px] text-on-surface-variant">
                DETERMINISTIC RUBRIC SEAM
              </span>
            </div>

            <h2 className="font-serif text-2xl lg:text-3xl font-bold text-on-surface mb-2">
              Measurable Human Expertise Transfer
            </h2>

            <p className="font-sans text-xs text-on-surface-variant leading-relaxed max-w-xl">
              Through evidence-grounded feedback and deliberate retry, the apprentice eliminated all 3 critical technique divergences, converting baseline acoustic and parallax failures into certified optical calibration proficiency.
            </p>
          </div>

          {/* Expert Attestation Quote */}
          <div className="mt-4 pt-4 border-t border-outline/70 flex items-start gap-3 bg-surface-container/60 p-3 rounded border border-outline/50">
            <ShieldCheck className="w-5 h-5 text-transmission-emerald shrink-0 mt-0.5" />
            <div className="text-xs font-sans">
              <div className="font-mono text-[10px] text-transmission-emerald font-bold mb-0.5">
                EXPERT & MULTIMODAL EVALUATOR CONSENSUS:
              </div>
              <p className="text-on-surface-variant italic">
                &ldquo;Apprentice Marcus Vance corrected spindle over-compression; uniform 3-click clutch cadence now matches standard Elena Rostova reference at 19.2s.&rdquo;
              </p>
              <div className="font-mono text-[10px] text-on-surface-variant mt-1">
                — Gemini 2.5 Flash Evaluator &bull; Lineage Node TX-REC-001
              </div>
            </div>
          </div>
        </div>

        {/* Center / Right Column: Quantitative Gain Badges & Progress Bars */}
        <div className="lg:w-96 flex flex-col justify-between bg-surface-container-lowest p-4 rounded-lg border border-outline shadow-inner">
          {/* Main Gain Metric Card */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-on-surface-variant">DETERMINISTIC TRANSMISSION GAIN:</span>
              <span className="text-caliper-cyan">Δ = RETRY - BASELINE</span>
            </div>

            {/* Glowing Emerald Gain Badge */}
            <div className="flex items-baseline justify-between bg-transmission-emerald/10 border border-transmission-emerald/40 p-3 rounded shadow-[0_0_20px_rgba(16,185,129,0.15)]">
              <div>
                <div className="font-mono text-3xl font-extrabold text-transmission-emerald tracking-tight">
                  +{metrics.gainPoints.toFixed(1)} PTS
                </div>
                <div className="font-mono text-xs text-transmission-emerald/90 font-medium">
                  +{metrics.gainPercentage.toFixed(1)}% OVERALL ATTAINMENT
                </div>
              </div>
              <div className="text-right">
                <span className="px-2 py-1 rounded bg-transmission-emerald text-surface-container-lowest font-mono font-bold text-xs uppercase tracking-wider">
                  +3 CRITERIA MASTERED
                </span>
              </div>
            </div>

            {/* Baseline vs Retry Score Comparison Strip */}
            <div className="grid grid-cols-2 gap-2 mt-1">
              <div className="p-2 rounded bg-surface-container border border-outline">
                <div className="text-[10px] font-mono text-on-surface-variant uppercase">
                  BASELINE (ATT-BASE-001)
                </div>
                <div className="font-mono text-lg font-bold text-divergence-crimson">
                  {metrics.baselineScore.toFixed(1)} <span className="text-xs text-on-surface-variant font-normal">/ {metrics.maxPossibleScore.toFixed(1)}</span>
                </div>
                <div className="text-[9px] font-mono text-divergence-crimson">
                  FAILED (21.4%)
                </div>
              </div>

              <div className="p-2 rounded bg-surface-container border border-outline">
                <div className="text-[10px] font-mono text-on-surface-variant uppercase">
                  RETRY (ATT-RETRY-001)
                </div>
                <div className="font-mono text-lg font-bold text-transmission-emerald">
                  {metrics.retryScore.toFixed(1)} <span className="text-xs text-on-surface-variant font-normal">/ {metrics.maxPossibleScore.toFixed(1)}</span>
                </div>
                <div className="text-[9px] font-mono text-transmission-emerald">
                  PASSED (100.0%)
                </div>
              </div>
            </div>

            {/* Criterion Gains Breakdown */}
            <div className="mt-2 space-y-1.5 pt-2 border-t border-outline/50">
              <div className="flex items-center justify-between text-[10px] font-mono text-on-surface-variant">
                <span>CRITERION GAINS:</span>
                <span>DELTA</span>
              </div>

              {telemetry.criteriaComparisons.map((c) => {
                const diff = c.retryScore - c.baselineScore;
                return (
                  <div key={c.criterionId} className="flex items-center justify-between font-mono text-[11px]">
                    <span className="text-on-surface-variant flex items-center gap-1">
                      <span className="text-caliper-cyan">{c.criterionId}:</span>
                      <span className="truncate max-w-[130px]">{c.name}</span>
                    </span>
                    <span className="text-transmission-emerald font-bold">
                      +{diff.toFixed(1)} pts
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Inspect Provenance Drawer Trigger */}
          <button
            onClick={onOpenLineage}
            className="mt-4 w-full flex items-center justify-center gap-2 py-2 rounded bg-surface-container hover:bg-surface-container-high border border-outline hover:border-caliper-cyan text-on-surface font-mono text-xs transition-colors group"
          >
            <Fingerprint className="w-3.5 h-3.5 text-caliper-cyan group-hover:scale-110 transition-transform" />
            <span>INSPECT CRYPTOGRAPHIC LINEAGE DAG</span>
            <ArrowRight className="w-3.5 h-3.5 text-on-surface-variant group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </div>
    </div>
  );
};
