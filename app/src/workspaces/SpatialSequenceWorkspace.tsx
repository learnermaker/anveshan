import React, { useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  Layers,
  Sparkles,
  Scissors,
  ShieldCheck,
  Video,
  ExternalLink,
  Info,
  Clock,
  Shield,
} from 'lucide-react';
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
  const [activeStep, setActiveStep] = useState<number>(4); // Step 4 is first divergence locus

  const sourceMeta = capCase.sourceProvenance ?? {
    sourceId: 'src-origami-tavin-2010',
    title: 'OrigamiCrane.ogv',
    creator: 'Tavin (Wikimedia Commons)',
    sourceUrl: 'https://commons.wikimedia.org/wiki/File:OrigamiCrane.ogv',
    license: 'CC BY 3.0',
    runtimeSeconds: 335,
    dimensions: '400 × 226',
    localPosterPath: '/assets/origami-tavin-poster.jpg',
  };

  const steps = [
    {
      num: 1,
      title: 'Diagonal Valley Fold',
      status: 'PASS',
      error: '0.4mm (PASS)',
      certainty: 'OBSERVED',
      note: 'Initial corner alignment within 1mm tolerance.',
    },
    {
      num: 2,
      title: 'Preliminary Square Collapse',
      status: 'PASS',
      error: '0.6mm (PASS)',
      certainty: 'OBSERVED',
      note: 'Four-flap diamond collapse with open corner facing learner.',
    },
    {
      num: 3,
      title: 'Lateral Wing Pre-Creases',
      status: 'PASS',
      error: '0.8mm (PASS)',
      certainty: 'OBSERVED',
      note: 'Bilateral guideline creases burnished to 180° flat profile.',
    },
    {
      num: 4,
      title: 'Petal Fold Crease Inversion',
      status: 'DIVERGENT',
      error: 'UNREVERSED RIDGE',
      certainty: 'OBSERVED',
      note: 'FIRST DIVERGENCE: Mountain fold unreversed; spine buckles under tension.',
    },
    {
      num: 5,
      title: 'Diamond Bird Base Flaps',
      status: 'BLOCKED',
      error: 'CRUMPLED APEX',
      certainty: 'INFERRED',
      note: 'Mechanically blocked due to Step 4 unreversed fold geometry.',
    },
  ];

  const currentStepData = steps.find((s) => s.num === activeStep) ?? steps[3];

  return (
    <div className="flex flex-col gap-6 w-full animate-fade-in text-on-surface">
      {/* Top Banner: Spatial Sequence Context & Epistemic Separation */}
      <div className="bg-surface-elevated/90 border border-outline rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-lg backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-cadmium-amber/15 border border-cadmium-amber/30 flex items-center justify-center text-cadmium-amber">
            <Scissors className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] font-mono uppercase tracking-widest text-cadmium-amber font-bold">
                SPATIAL SEQUENCE WORKSPACE
              </span>
              <span className="text-outline text-xs">//</span>
              <span className="text-[10px] font-mono text-transmission-emerald bg-transmission-emerald/10 px-2 py-0.5 rounded border border-transmission-emerald/30 font-semibold">
                ORDERED FOLD TIMELINE
              </span>
            </div>
            <h2 className="text-base font-semibold text-on-surface">
              Origami Crane Bird Base: Mountain/Valley Crease Inversion
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap text-[11px] font-mono">
          <span className="px-2.5 py-1 rounded bg-surface-dim border border-outline text-on-surface-variant flex items-center gap-1.5">
            <Video className="w-3.5 h-3.5 text-caliper-cyan" />
            <span>EXTERNAL SOURCE: WIKIMEDIA COMMONS</span>
          </span>
          <span className="px-2.5 py-1 rounded bg-divergence-crimson/15 border border-divergence-crimson/30 text-divergence-crimson font-bold">
            FIRST DIVERGENCE: STEP 04
          </span>
        </div>
      </div>

      {/* Main Grid: Left Column Workspace (8 cols) + Right Column Rubric HUD (4 cols) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left Column: Spatial Sequence Instrument */}
        <div className="xl:col-span-8 flex flex-col gap-6">
          {/* Section 1: Source Demonstration & Case State Overview */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
            {/* Source Demonstration Panel (7 cols) */}
            <div className="lg:col-span-7 bg-surface-elevated border border-outline rounded-xl p-4 flex flex-col justify-between gap-3 shadow-md">
              <div className="flex items-center justify-between border-b border-outline/50 pb-2.5">
                <div className="flex items-center gap-2 text-xs font-mono font-bold text-on-surface">
                  <Video className="w-4 h-4 text-caliper-cyan" />
                  <span>SOURCE DEMONSTRATION // File:OrigamiCrane.ogv</span>
                </div>
                <span className="text-[9px] font-mono text-caliper-cyan bg-caliper-cyan/10 px-2 py-0.5 rounded border border-caliper-cyan/25 font-bold">
                  EXTERNAL EVIDENCE
                </span>
              </div>

              {/* Source Demonstration Poster / Media Display */}
              <div className="relative rounded-lg overflow-hidden border border-outline/50 bg-zinc-950 aspect-[16/9] flex items-center justify-center group">
                <img
                  src="/assets/origami-tavin-poster.jpg"
                  alt="Wikimedia Commons OrigamiCrane.ogv poster"
                  className="w-full h-full object-cover opacity-85 group-hover:opacity-100 transition-opacity"
                  onError={(e) => {
                    // Graceful fallback to schematic if image load fails
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent pointer-events-none" />

                {/* Video Info Overlay */}
                <div className="absolute top-2.5 left-2.5 z-10 flex items-center gap-1.5 font-mono text-[10px]">
                  <span className="bg-black/75 text-zinc-300 px-2 py-0.5 rounded border border-zinc-700 flex items-center gap-1">
                    <Clock className="w-3 h-3 text-cadmium-amber" />
                    <span>5m 35s</span>
                  </span>
                  <span className="bg-black/75 text-zinc-300 px-2 py-0.5 rounded border border-zinc-700">
                    400 × 226
                  </span>
                </div>

                {/* External Source Link */}
                <a
                  href="https://commons.wikimedia.org/wiki/File:OrigamiCrane.ogv"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="absolute bottom-2.5 right-2.5 z-10 px-3 py-1 rounded bg-black/80 hover:bg-black text-caliper-cyan border border-caliper-cyan/40 text-[10px] font-mono flex items-center gap-1.5 transition-colors shadow-lg"
                  title="Open source video on Wikimedia Commons"
                >
                  <span>COMMONS SOURCE PAGE</span>
                  <ExternalLink className="w-3 h-3" />
                </a>

                <div className="absolute bottom-2.5 left-2.5 z-10 text-[10px] font-mono text-zinc-300">
                  CREATOR: Tavin • CC BY 3.0
                </div>
              </div>

              {/* Epistemic Mapping Notice */}
              <div className="p-2.5 bg-surface-dim rounded-lg border border-outline/40 space-y-1 text-[11px] font-mono">
                <div className="flex items-center justify-between text-on-surface font-semibold">
                  <span className="flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5 text-cadmium-amber" />
                    <span>SOURCE-TO-STEP MAPPING:</span>
                  </span>
                  <span className="text-cadmium-amber font-bold">UNVERIFIED TIMESTAMPS</span>
                </div>
                <p className="text-[10px] text-on-surface-variant leading-relaxed">
                  The external demonstration records the complete origami sequence. Step-level alignment to millisecond video timestamps remains unverified until frame-by-frame temporal inspection. Replay executes on deterministic step order.
                </p>
                <div className="text-[9px] text-zinc-400 pt-0.5">
                  MEDIA PLAYBACK NOT REQUIRED FOR DETERMINISTIC REPLAY
                </div>
              </div>
            </div>

            {/* Case State & Progression Panel (5 cols) */}
            <div className="lg:col-span-5 bg-surface-elevated border border-outline rounded-xl p-4 flex flex-col justify-between gap-3 shadow-md">
              <div className="flex items-center justify-between border-b border-outline/50 pb-2.5">
                <div className="text-xs font-mono font-bold text-on-surface flex items-center gap-1.5">
                  <Layers className="w-4 h-4 text-cadmium-amber" />
                  <span>CASE PROGRESSION</span>
                </div>
                <span className="text-[9px] font-mono text-on-surface-variant bg-surface-dim px-2 py-0.5 rounded border border-outline">
                  5 ORDERED STEPS
                </span>
              </div>

              {/* Sequential Transformation Chain */}
              <div className="space-y-2 font-mono text-xs">
                <div className="text-[10px] text-on-surface-variant uppercase tracking-wider font-bold">
                  Ordered Fold-State Sequence:
                </div>
                <div className="p-2.5 bg-surface-dim rounded-lg border border-outline/40 space-y-2 text-[11px]">
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-300">01. Diagonal Valley</span>
                    <span className="text-transmission-emerald font-bold">PASS (0.4mm)</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-300">02. Square Collapse</span>
                    <span className="text-transmission-emerald font-bold">PASS (0.6mm)</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-300">03. Wing Pre-Creases</span>
                    <span className="text-transmission-emerald font-bold">PASS (0.8mm)</span>
                  </div>
                  <div className="flex items-center justify-between bg-divergence-crimson/15 p-1 rounded border border-divergence-crimson/30">
                    <span className="text-divergence-crimson font-bold">04. Petal Inversion</span>
                    <span className="text-divergence-crimson font-bold">DIVERGENT</span>
                  </div>
                  <div className="flex items-center justify-between text-zinc-500">
                    <span>05. Diamond Base</span>
                    <span className="text-zinc-500">BLOCKED</span>
                  </div>
                </div>
              </div>

              {/* Rationale Note */}
              <div className="p-2.5 bg-cadmium-amber/10 border border-cadmium-amber/25 rounded-lg text-[10px] font-mono text-cadmium-amber leading-relaxed">
                <strong>MECHANICAL CAUSALITY:</strong> Step 4 crease failure forces paper against fiber grain, buckling the spine and mechanically blocking Step 5 completion.
              </div>
            </div>
          </div>

          {/* Section 2: Interactive Ordered Fold Timeline */}
          <div className="bg-surface-elevated border border-outline rounded-xl p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-outline pb-3">
              <div className="flex items-center gap-2 text-xs font-mono font-bold text-on-surface">
                <Layers className="w-4 h-4 text-caliper-cyan" />
                <span>ORDERED FOLD TIMELINE // SELECT STEP TO INSPECT REASONING</span>
              </div>
              <div className="text-[10px] font-mono text-cadmium-amber">
                ACTIVE STEP: 0{activeStep}
              </div>
            </div>

            {/* Step Navigator Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
              {steps.map((s) => (
                <button
                  key={s.num}
                  onClick={() => setActiveStep(s.num)}
                  className={`p-3 rounded-lg border text-left font-mono transition-all flex flex-col justify-between ${
                    activeStep === s.num
                      ? s.status === 'DIVERGENT'
                        ? 'border-divergence-crimson bg-divergence-crimson/20 shadow-lg shadow-divergence-crimson/15 ring-1 ring-divergence-crimson'
                        : 'border-transmission-emerald bg-transmission-emerald/15 shadow-lg shadow-transmission-emerald/15 ring-1 ring-transmission-emerald'
                      : 'border-outline bg-surface-dim hover:border-outline-variant hover:bg-surface-dim/80'
                  }`}
                >
                  <div className="flex items-center justify-between text-[9px] text-on-surface-variant">
                    <span>STEP 0{s.num}</span>
                    <span
                      className={`px-1 py-0.2 rounded text-[8px] font-bold ${
                        s.certainty === 'OBSERVED'
                          ? 'bg-caliper-cyan/20 text-caliper-cyan'
                          : 'bg-cadmium-amber/20 text-cadmium-amber'
                      }`}
                    >
                      {s.certainty}
                    </span>
                  </div>
                  <div className="text-[11px] font-bold text-on-surface truncate mt-1">
                    {s.title}
                  </div>
                  <div
                    className={`text-[9px] font-semibold mt-1.5 ${
                      s.status === 'DIVERGENT'
                        ? 'text-divergence-crimson font-bold'
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

            {/* Active Step Details Sub-bar */}
            <div className="px-3.5 py-2 bg-surface-dim rounded-lg border border-outline/40 flex items-center justify-between text-xs font-mono">
              <span className="text-zinc-300">
                <strong>STEP 0{currentStepData.num}:</strong> {currentStepData.title}
              </span>
              <span className="text-on-surface-variant text-[11px]">
                {currentStepData.note}
              </span>
            </div>

            {/* Section 3: Forensic Crease Polarity Comparison (Reference vs Learner) */}
            <div className="p-4 bg-surface-dim rounded-xl border border-outline/50 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono font-bold">
                <span className="text-on-surface flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-caliper-cyan" />
                  <span>STEP 04 FORENSIC CREASE POLARITY ANALYSIS</span>
                </span>
                <span className="text-divergence-crimson text-[11px]">
                  OBSERVED: FOLD CONVEXITY POLARITY CONFLICT
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Reference State Card */}
                <div className="p-4 bg-surface-elevated rounded-lg border border-transmission-emerald/40 space-y-3">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-transmission-emerald font-bold flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>REFERENCE FOLD STATE</span>
                    </span>
                    <span className="text-[10px] text-transmission-emerald bg-transmission-emerald/10 px-1.5 py-0.5 rounded border border-transmission-emerald/30 font-bold">
                      -180° CONCAVE
                    </span>
                  </div>

                  {/* Visual Diagram: Valley Trough */}
                  <div className="h-32 bg-zinc-950 rounded-lg flex flex-col items-center justify-center border border-zinc-800 relative overflow-hidden p-2">
                    <svg
                      viewBox="0 0 100 60"
                      className="w-36 h-20 stroke-transmission-emerald fill-none stroke-[2.5]"
                    >
                      <path d="M 10,12 L 50,48 L 90,12" strokeLinecap="round" strokeLinejoin="round" />
                      {/* Symmetry center dashed guide */}
                      <line x1="50" y1="5" x2="50" y2="55" stroke="#10b981" strokeWidth="1" strokeDasharray="2,2" opacity="0.6" />
                      {/* Inward pop vector arrow */}
                      <path d="M 50,15 L 50,35" stroke="#06b6d4" strokeWidth="1.5" strokeDasharray="none" markerEnd="url(#arrow)" />
                    </svg>
                    <span className="absolute bottom-1.5 text-[10px] font-mono text-transmission-emerald font-semibold">
                      INWARD VALLEY TROUGH (CONCAVE)
                    </span>
                  </div>

                  <p className="text-[11px] font-mono text-on-surface-variant leading-relaxed">
                    Paper popped inside-out cleanly along central symmetry axis. Valley trough vector allows lateral wings to collapse without tearing fiber grain.
                  </p>
                  <div className="text-[9px] font-mono text-transmission-emerald flex items-center justify-between border-t border-outline/30 pt-1.5">
                    <span>STATE: DERIVED SPECIFICATION</span>
                    <span>CERTAINTY: SOURCE_DERIVED_FACT</span>
                  </div>
                </div>

                {/* Learner Replay State Card */}
                <div className="p-4 bg-surface-elevated rounded-lg border border-divergence-crimson/40 space-y-3">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-divergence-crimson font-bold flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>LEARNER REPLAY ATTEMPT</span>
                    </span>
                    <span className="text-[10px] text-divergence-crimson bg-divergence-crimson/10 px-1.5 py-0.5 rounded border border-divergence-crimson/30 font-bold">
                      +180° MOUNTAIN (UNREVERSED)
                    </span>
                  </div>

                  {/* Visual Diagram: Mountain Ridge */}
                  <div className="h-32 bg-zinc-950 rounded-lg flex flex-col items-center justify-center border border-zinc-800 relative overflow-hidden p-2">
                    <svg
                      viewBox="0 0 100 60"
                      className="w-36 h-20 stroke-divergence-crimson fill-none stroke-[2.5]"
                    >
                      <path d="M 10,48 L 50,12 L 90,48" strokeLinecap="round" strokeLinejoin="round" />
                      {/* Conflict arrows */}
                      <line x1="50" y1="5" x2="50" y2="55" stroke="#ef4444" strokeWidth="1" strokeDasharray="2,2" opacity="0.6" />
                      <circle cx="50" cy="12" r="3" fill="#ef4444" />
                    </svg>
                    <span className="absolute bottom-1.5 text-[10px] font-mono text-divergence-crimson font-semibold">
                      OUTWARD MOUNTAIN RIDGE (SPINE BUNCHING)
                    </span>
                  </div>

                  <p className="text-[11px] font-mono text-on-surface-variant leading-relaxed">
                    Top flap pulled upward without pushing lateral creases inward. Paper fought the fiber grain (+180° convex ridge), crushing central apex.
                  </p>
                  <div className="text-[9px] font-mono text-divergence-crimson flex items-center justify-between border-t border-outline/30 pt-1.5">
                    <span>STATE: REPLAY FIXTURE ATTEMPT</span>
                    <span>CERTAINTY: OBSERVED DIVERGENCE</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Section 4: First Divergence Intervention & Targeted Action */}
            <div className="p-4 bg-surface-dim/70 rounded-xl border border-cadmium-amber/30 space-y-3">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-bold text-cadmium-amber flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4" />
                  <span>TARGETED INTERVENTION // CRIT-VALLEY-FOLD</span>
                </span>
                <span className="text-[10px] font-mono text-on-surface-variant">
                  EVALUATOR: DETERMINISTIC RUBRIC
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px] font-mono">
                <div className="p-2.5 bg-surface-elevated rounded border border-outline/40">
                  <div className="text-caliper-cyan font-bold text-[10px]">OBSERVED FINDING</div>
                  <div className="text-on-surface mt-1">Left wing crease maintained as mountain fold (+180° convex).</div>
                </div>
                <div className="p-2.5 bg-surface-elevated rounded border border-outline/40">
                  <div className="text-cadmium-amber font-bold text-[10px]">MECHANICAL INFERENCE</div>
                  <div className="text-on-surface mt-1">Fiber grain stressed against fold line; apex crinkled 18° off-plane.</div>
                </div>
                <div className="p-2.5 bg-surface-elevated rounded border border-outline/40">
                  <div className="text-zinc-400 font-bold text-[10px]">CORRECTIVE INSTRUCTION</div>
                  <div className="text-on-surface mt-1">Pinch edges inward while pressing finger behind flap to pop crease inward.</div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-outline/40">
                <button
                  onClick={onJumpFirstDivergence}
                  className="px-4 py-2.5 rounded-lg bg-divergence-crimson/20 border border-divergence-crimson/40 text-divergence-crimson hover:bg-divergence-crimson/30 text-xs font-mono font-bold flex items-center gap-2 transition-colors"
                >
                  <AlertTriangle className="w-4 h-4" />
                  <span>INSPECT STEP 04 CREASE REVERSAL</span>
                </button>

                <button
                  onClick={onLaunchRetry}
                  className="px-5 py-2.5 rounded-lg bg-transmission-emerald hover:bg-transmission-emerald/90 text-background text-xs font-mono font-bold flex items-center gap-2 shadow-lg shadow-transmission-emerald/20 transition-all hover:scale-[1.02]"
                >
                  <span>RETRY VALLEY INVERSION</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
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
