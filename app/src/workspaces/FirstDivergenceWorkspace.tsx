import React, { useState } from 'react';
import { AlertTriangle, ArrowRight, CheckCircle2, ShieldAlert, ShieldCheck, Sparkles, Sliders } from 'lucide-react';
import type { CapabilityCase } from '../types/workspace';
import { RubricHUD } from '../components/RubricHUD';
import { TransmissionGainHero } from '../components/TransmissionGainHero';

interface FirstDivergenceWorkspaceProps {
  capCase: CapabilityCase;
  onOpenLineage: () => void;
  onJumpFirstDivergence: () => void;
  onLaunchRetry: () => void;
}

export function FirstDivergenceWorkspace({
  capCase,
  onOpenLineage,
  onJumpFirstDivergence,
  onLaunchRetry,
}: FirstDivergenceWorkspaceProps) {
  const telemetry = capCase.telemetry;
  const [selectedCriterionId, setSelectedCriterionId] = useState<string | null>('CRIT-CROSS-DIR');
  const [tensileLoad, setTensileLoad] = useState<number>(15);

  const isCapsize = tensileLoad >= 12;

  return (
    <div className="flex flex-col gap-6 w-full animate-fade-in">
      {/* Main Grid: Knot Topology on Left (8 cols) + Rubric HUD on Right (4 cols) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left Column: First-Divergence Workspace */}
        <div className="xl:col-span-8 flex flex-col gap-4">
          <div className="bg-surface-elevated border border-outline rounded-xl p-5 shadow-xl relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-outline pb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-divergence-crimson/15 border border-divergence-crimson/30 flex items-center justify-center text-divergence-crimson">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-divergence-crimson font-bold">
                    FIRST-DIVERGENCE WORKSPACE // TOPOLOGICAL CHIRALITY
                  </div>
                  <h3 className="text-base font-semibold text-on-surface">
                    Square (Reef) Knot vs Granny Knot: Second Throw Reversal
                  </h3>
                </div>
              </div>

              <div className="px-3 py-1 bg-divergence-crimson/15 border border-divergence-crimson/30 rounded font-mono text-xs text-divergence-crimson font-bold">
                TOPOLOGICAL FAULT: THROW #2
              </div>
            </div>

            {/* Visual Knot Comparison */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
              {/* Expert Square Knot */}
              <div className="p-4 bg-surface-dim rounded-lg border border-transmission-emerald/40 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-transmission-emerald flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" />
                    TRUE SQUARE KNOT (REEF)
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-transmission-emerald/15 text-transmission-emerald">
                    R-OVER-L → L-OVER-R
                  </span>
                </div>

                <div className="h-32 bg-zinc-950 rounded border border-zinc-800 flex items-center justify-center relative">
                  <svg viewBox="0 0 160 80" className="w-40 h-20 fill-none stroke-[4]">
                    {/* Blue cord loop */}
                    <path d="M 20,30 Q 70,10 90,40 Q 110,70 140,50" stroke="#38bdf8" />
                    {/* Gold cord loop interlocking parallel */}
                    <path d="M 20,50 Q 50,70 70,40 Q 90,10 140,30" stroke="#fbbf24" />
                  </svg>
                  <span className="absolute bottom-2 font-mono text-[10px] text-transmission-emerald">
                    PARALLEL BIGHTS // LOCKS SOLID
                  </span>
                </div>

                <p className="text-[11px] font-mono text-on-surface-variant leading-relaxed">
                  Working ends exit parallel to standing lines. Tightens cleanly under load.
                </p>
              </div>

              {/* Learner Granny Knot */}
              <div className="p-4 bg-surface-dim rounded-lg border border-divergence-crimson/40 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-divergence-crimson flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4" />
                    GRANNY KNOT (LEARNER ERROR)
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-divergence-crimson/15 text-divergence-crimson">
                    R-OVER-L → R-OVER-L
                  </span>
                </div>

                <div className="h-32 bg-zinc-950 rounded border border-zinc-800 flex items-center justify-center relative">
                  <svg viewBox="0 0 160 80" className="w-40 h-20 fill-none stroke-[4]">
                    {/* Crossed asymmetric granny knot cords */}
                    <path d="M 20,25 Q 80,60 140,25" stroke="#38bdf8" />
                    <path d="M 20,55 Q 80,20 140,55" stroke="#fbbf24" />
                    <line x1="80" y1="10" x2="80" y2="70" stroke="#ef4444" strokeWidth="2" strokeDasharray="3 3" />
                  </svg>
                  <span className="absolute bottom-2 font-mono text-[10px] text-divergence-crimson">
                    PERPENDICULAR TAILS // CAPSIZES
                  </span>
                </div>

                <p className="text-[11px] font-mono text-on-surface-variant leading-relaxed">
                  Repeated right-over-left throw forces cords out perpendicular, creating a slip knot.
                </p>
              </div>
            </div>

            {/* Interactive Tensile Load Tester */}
            <div className="p-4 bg-surface-dim rounded-lg border border-outline/40 space-y-3">
              <div className="flex items-center justify-between text-xs font-mono font-bold">
                <span className="text-on-surface flex items-center gap-1.5">
                  <Sliders className="w-4 h-4 text-caliper-cyan" />
                  TENSILE LOAD SLIP TEST SIMULATION (0–25 NEWTONS)
                </span>
                <span className={isCapsize ? 'text-divergence-crimson font-bold' : 'text-transmission-emerald font-bold'}>
                  LOAD: {tensileLoad} N // {isCapsize ? 'CAPSIZED & SLIPPED' : 'LOCKED'}
                </span>
              </div>

              <input
                type="range"
                min="0"
                max="25"
                value={tensileLoad}
                onChange={(e) => setTensileLoad(Number(e.target.value))}
                className="w-full accent-cadmium-amber cursor-pointer"
              />

              <div className="flex items-center justify-between text-[11px] font-mono text-on-surface-variant">
                <span>0 N (SLACK)</span>
                <span className="text-divergence-crimson font-bold">12 N (GRANNY FAILS)</span>
                <span className="text-transmission-emerald font-bold">25 N (SQUARE HOLDS)</span>
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-outline/50 mt-4">
              <button
                onClick={onJumpFirstDivergence}
                className="px-4 py-2 rounded-lg bg-divergence-crimson/20 border border-divergence-crimson/40 text-divergence-crimson hover:bg-divergence-crimson/30 text-xs font-mono font-bold flex items-center gap-2 transition-colors"
              >
                <AlertTriangle className="w-4 h-4" />
                <span>INSPECT FIRST DIVERGENCE (THROW #2)</span>
              </button>

              <button
                onClick={onLaunchRetry}
                className="px-5 py-2 rounded-lg bg-transmission-emerald hover:bg-transmission-emerald/90 text-background text-xs font-mono font-bold flex items-center gap-2 shadow-lg shadow-transmission-emerald/20 transition-all hover:scale-[1.02]"
              >
                <span>RETRY SECOND THROW</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Rubric HUD (4 cols) */}
        <div className="xl:col-span-4 h-full">
          <RubricHUD
            telemetry={telemetry}
            currentTime={7.5}
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
