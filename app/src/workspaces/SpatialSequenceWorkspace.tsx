import React, { useState } from 'react';
import { AlertTriangle, ArrowRight, CheckCircle2, ChevronRight, Layers, Sparkles, Scissors, ShieldCheck } from 'lucide-react';
import type { CapabilityCase } from '../types/workspace';
import { RubricHUD } from '../components/RubricHUD';
import { TransmissionGainHero } from '../components/TransmissionGainHero';

interface SpatialSequenceWorkspaceProps {
  capCase: CapabilityCase;
  onOpenLineage: () => void;
  onJumpFirstDivergence: () => void;
  onLaunchRetry: () => void;
}

export function SpatialSequenceWorkspace({
  capCase,
  onOpenLineage,
  onJumpFirstDivergence,
  onLaunchRetry,
}: SpatialSequenceWorkspaceProps) {
  const telemetry = capCase.telemetry;
  const [selectedCriterionId, setSelectedCriterionId] = useState<string | null>('CRIT-VALLEY-FOLD');
  const [activeStep, setActiveStep] = useState<number>(4); // Step 4 is first divergence

  const steps = [
    { num: 1, title: 'Diagonal Valley Fold', status: 'PASS', error: '0.4mm' },
    { num: 2, title: 'Preliminary Square Collapse', status: 'PASS', error: '0.6mm' },
    { num: 3, title: 'Lateral Wing Pre-Creases', status: 'PASS', error: '0.8mm' },
    { num: 4, title: 'Petal Fold Crease Inversion', status: 'DIVERGENT', error: 'UNREVERSED RIDGE' },
    { num: 5, title: 'Diamond Bird Base Flaps', status: 'BLOCKED', error: 'CRUMPLED' },
  ];

  return (
    <div className="flex flex-col gap-6 w-full animate-fade-in">
      {/* Main Grid: Step Sequence on Left (8 cols) + Rubric HUD on Right (4 cols) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left Column: Spatial Sequence Workspace */}
        <div className="xl:col-span-8 flex flex-col gap-4">
          <div className="bg-surface-elevated border border-outline rounded-xl p-5 shadow-xl relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-outline pb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-cadmium-amber/15 border border-cadmium-amber/30 flex items-center justify-center text-cadmium-amber">
                  <Scissors className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-cadmium-amber font-bold">
                    SPATIAL SEQUENCE WORKSPACE // ORDERED FOLD TIMELINE
                  </div>
                  <h3 className="text-base font-semibold text-on-surface">
                    Origami Crane Bird Base: Mountain/Valley Crease Inversion
                  </h3>
                </div>
              </div>

              <div className="px-3 py-1 bg-divergence-crimson/15 border border-divergence-crimson/30 rounded font-mono text-xs text-divergence-crimson font-bold">
                DIVERGENCE: STEP 04
              </div>
            </div>

            {/* Step Navigator */}
            <div className="grid grid-cols-5 gap-2 my-4">
              {steps.map((s) => (
                <button
                  key={s.num}
                  onClick={() => setActiveStep(s.num)}
                  className={`p-2.5 rounded-lg border text-left font-mono transition-all ${
                    activeStep === s.num
                      ? s.status === 'DIVERGENT'
                        ? 'border-divergence-crimson bg-divergence-crimson/20 shadow-lg shadow-divergence-crimson/10'
                        : 'border-transmission-emerald bg-transmission-emerald/15'
                      : 'border-outline bg-surface-dim hover:border-outline-variant'
                  }`}
                >
                  <div className="text-[9px] text-on-surface-variant">STEP 0{s.num}</div>
                  <div className="text-[11px] font-bold text-on-surface truncate mt-0.5">{s.title}</div>
                  <div
                    className={`text-[9px] font-semibold mt-1 ${
                      s.status === 'DIVERGENT'
                        ? 'text-divergence-crimson'
                        : s.status === 'PASS'
                        ? 'text-transmission-emerald'
                        : 'text-on-surface-variant'
                    }`}
                  >
                    {s.error}
                  </div>
                </button>
              ))}
            </div>

            {/* Fold Crease Inversion Diagram */}
            <div className="p-4 bg-surface-dim rounded-lg border border-outline/40 space-y-4">
              <div className="flex items-center justify-between text-xs font-mono font-bold">
                <span className="text-on-surface flex items-center gap-1.5">
                  <Layers className="w-4 h-4 text-caliper-cyan" />
                  STEP 04 FORENSIC CREASE POLARITY ANALYSIS
                </span>
                <span className="text-divergence-crimson">
                  OBSERVED: FOLD CONVEXITY CONFLICT
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* Reference Crease */}
                <div className="p-3.5 bg-surface-elevated rounded border border-transmission-emerald/40 space-y-2">
                  <div className="flex items-center justify-between text-[11px] font-mono text-transmission-emerald font-bold">
                    <span>EXPERT VALLEY INVERSION</span>
                    <span>-180° CONCAVE</span>
                  </div>
                  <div className="h-28 bg-zinc-950 rounded flex items-center justify-center border border-zinc-800 relative">
                    {/* Visual Valley Crease (inward V) */}
                    <svg viewBox="0 0 100 60" className="w-32 h-20 stroke-transmission-emerald fill-none stroke-[2.5]">
                      <path d="M 10,10 L 50,50 L 90,10" />
                    </svg>
                    <span className="absolute bottom-2 text-[10px] font-mono text-transmission-emerald">
                      INWARD VALLEY TROUGH
                    </span>
                  </div>
                  <p className="text-[11px] font-mono text-on-surface-variant">
                    Paper popped inside-out cleanly. Center apex flat with zero crinkles.
                  </p>
                </div>

                {/* Learner Unreversed Crease */}
                <div className="p-3.5 bg-surface-elevated rounded border border-divergence-crimson/40 space-y-2">
                  <div className="flex items-center justify-between text-[11px] font-mono text-divergence-crimson font-bold">
                    <span>LEARNER BASELINE ERROR</span>
                    <span>+180° MOUNTAIN (UNREVERSED)</span>
                  </div>
                  <div className="h-28 bg-zinc-950 rounded flex items-center justify-center border border-zinc-800 relative">
                    {/* Visual Mountain Crease (outward peak) */}
                    <svg viewBox="0 0 100 60" className="w-32 h-20 stroke-divergence-crimson fill-none stroke-[2.5]">
                      <path d="M 10,50 L 50,10 L 90,50" />
                    </svg>
                    <span className="absolute bottom-2 text-[10px] font-mono text-divergence-crimson">
                      OUTWARD MOUNTAIN RIDGE
                    </span>
                  </div>
                  <p className="text-[11px] font-mono text-on-surface-variant">
                    Paper forced down against fiber grain, buckling central spine.
                  </p>
                </div>
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-outline/50 mt-4">
              <button
                onClick={onJumpFirstDivergence}
                className="px-4 py-2 rounded-lg bg-divergence-crimson/20 border border-divergence-crimson/40 text-divergence-crimson hover:bg-divergence-crimson/30 text-xs font-mono font-bold flex items-center gap-2 transition-colors"
              >
                <AlertTriangle className="w-4 h-4" />
                <span>INSPECT STEP 04 CREASE REVERSAL</span>
              </button>

              <button
                onClick={onLaunchRetry}
                className="px-5 py-2 rounded-lg bg-transmission-emerald hover:bg-transmission-emerald/90 text-background text-xs font-mono font-bold flex items-center gap-2 shadow-lg shadow-transmission-emerald/20 transition-all hover:scale-[1.02]"
              >
                <span>RETRY VALLEY INVERSION</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Rubric HUD (4 cols) */}
        <div className="xl:col-span-4 h-full">
          <RubricHUD
            telemetry={telemetry}
            currentTime={22.0}
            onTimeChange={() => {}}
            selectedCriterionId={selectedCriterionId}
            onSelectCriterion={setSelectedCriterionId}
          />
        </div>
      </div>

      {/* Bottom Transmission Gain Card */}
      <TransmissionGainHero
        telemetry={telemetry}
        onOpenLineage={onOpenLineage}
      />
    </div>
  );
}
