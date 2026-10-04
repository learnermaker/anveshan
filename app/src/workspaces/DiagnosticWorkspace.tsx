import React, { useState } from 'react';
import { AlertTriangle, ArrowRight, CheckCircle2, ChevronRight, Droplets, Eye, HelpCircle, Sparkles, Wrench, ShieldCheck } from 'lucide-react';
import type { CapabilityCase } from '../types/workspace';
import { RubricHUD } from '../components/RubricHUD';
import { TransmissionGainHero } from '../components/TransmissionGainHero';

interface DiagnosticWorkspaceProps {
  capCase: CapabilityCase;
  onOpenLineage: () => void;
  onJumpFirstDivergence: () => void;
  onLaunchRetry: () => void;
}

export function DiagnosticWorkspace({
  capCase,
  onOpenLineage,
  onJumpFirstDivergence,
  onLaunchRetry,
}: DiagnosticWorkspaceProps) {
  const telemetry = capCase.telemetry;
  const [activeStep, setActiveStep] = useState<number>(2); // Step 2 is first divergence
  const [selectedCriterionId, setSelectedCriterionId] = useState<string | null>('CRIT-TUBE-SAND');

  const diagnosticSteps = [
    {
      step: 1,
      title: 'Pneumatic Immersion Inspection',
      status: 'SATISFIED',
      finding: 'Continuous bubble stream observed 140mm clockwise from Schrader valve.',
      modality: 'Visual / Pneumatic',
      divergence: false,
    },
    {
      step: 2,
      title: 'Abrasive Surface Buffing',
      status: 'DIVERGENT',
      finding: 'Learner applied fluid directly onto factory mold-release glaze (Omitted sanding).',
      modality: 'Surface Mechanical',
      divergence: true,
    },
    {
      step: 3,
      title: 'Solvent Flash-Off Drying Window',
      status: 'PARTIAL',
      finding: 'Patch applied at 15s before solvent evaporated into tacky matte film.',
      modality: 'Chemical Kinetic',
      divergence: false,
    },
    {
      step: 4,
      title: 'Pressure Lock Seal & Curing',
      status: 'FAILED',
      finding: 'Trapped solvent and mold wax caused patch delamination at 25 PSI.',
      modality: 'Tensile Pressure',
      divergence: false,
    },
  ];

  return (
    <div className="flex flex-col gap-6 w-full animate-fade-in">
      {/* Main Grid: Diagnostic Decision Tree on Left (8 cols) + Rubric HUD on Right (4 cols) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left Column: Causal Decision Tree & Diagnostic Workbench */}
        <div className="xl:col-span-8 flex flex-col gap-4">
          <div className="bg-surface-elevated border border-outline rounded-xl p-5 shadow-xl relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-outline pb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-cadmium-amber/15 border border-cadmium-amber/30 flex items-center justify-center text-cadmium-amber">
                  <Wrench className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-cadmium-amber font-bold">
                    DIAGNOSTIC WORKSPACE // CAUSAL DECISION TREE
                  </div>
                  <h3 className="text-base font-semibold text-on-surface">
                    Pneumatic Leak Localization & Cold-Vulcanizing Sequence
                  </h3>
                </div>
              </div>

              <div className="px-3 py-1 bg-divergence-crimson/15 border border-divergence-crimson/30 rounded font-mono text-xs text-divergence-crimson font-bold">
                ROOT CAUSE: STEP #2
              </div>
            </div>

            {/* Diagnostic Step Flowchart */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 my-4">
              {diagnosticSteps.map((s) => (
                <div
                  key={s.step}
                  onClick={() => setActiveStep(s.step)}
                  className={`p-3.5 rounded-lg border cursor-pointer transition-all ${
                    activeStep === s.step
                      ? s.divergence
                        ? 'border-divergence-crimson bg-divergence-crimson/15 shadow-lg shadow-divergence-crimson/10'
                        : 'border-transmission-emerald bg-transmission-emerald/15'
                      : 'border-outline/50 bg-surface-dim hover:border-outline'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] font-mono mb-1">
                    <span className="text-on-surface-variant">STEP 0{s.step}</span>
                    <span
                      className={`font-bold ${
                        s.status === 'SATISFIED'
                          ? 'text-transmission-emerald'
                          : s.status === 'DIVERGENT'
                          ? 'text-divergence-crimson'
                          : 'text-cadmium-amber'
                      }`}
                    >
                      {s.status}
                    </span>
                  </div>
                  <div className="font-semibold text-xs text-on-surface leading-tight">
                    {s.title}
                  </div>
                </div>
              ))}
            </div>

            {/* Step Detail Visualizer */}
            <div className="p-4 bg-surface-dim rounded-lg border border-outline/40 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-on-surface flex items-center gap-2">
                  <Eye className="w-4 h-4 text-caliper-cyan" />
                  STEP 02 FORENSIC INSPECTION // BUTYL SURFACE STATE
                </span>
                <span className="px-2 py-0.5 rounded bg-divergence-crimson/20 border border-divergence-crimson text-divergence-crimson font-mono text-[10px] font-bold">
                  FIRST DIVERGENCE LOCUS
                </span>
              </div>

              {/* Comparative Surface Microscopy Simulation */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Reference Preparation */}
                <div className="p-3 bg-surface-elevated rounded border border-transmission-emerald/40 space-y-2">
                  <div className="flex items-center justify-between text-[11px] font-mono text-transmission-emerald font-semibold">
                    <span>EXPERT STANDARD</span>
                    <span>100% MATTE ABRADED</span>
                  </div>
                  <div className="h-24 bg-zinc-950 rounded flex items-center justify-center border border-zinc-800 relative overflow-hidden">
                    {/* Simulated cross-hatch texture */}
                    <div className="absolute inset-0 opacity-40 bg-[radial-gradient(#4ade80_1px,transparent_1px)] [background-size:8px_8px]" />
                    <span className="font-mono text-xs text-transmission-emerald font-bold z-10">
                      CROSS-HATCHED BUTYL (30mm)
                    </span>
                  </div>
                  <p className="text-[11px] text-on-surface-variant font-mono">
                    Emery paper eliminated silicone mold glaze. Raw rubber polymers exposed.
                  </p>
                </div>

                {/* Learner Preparation */}
                <div className="p-3 bg-surface-elevated rounded border border-divergence-crimson/40 space-y-2">
                  <div className="flex items-center justify-between text-[11px] font-mono text-divergence-crimson font-semibold">
                    <span>LEARNER BASELINE</span>
                    <span>FACTORY MOLD GLAZE (0% ABRADED)</span>
                  </div>
                  <div className="h-24 bg-zinc-950 rounded flex items-center justify-center border border-zinc-800 relative overflow-hidden">
                    {/* Simulated glossy reflection */}
                    <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/10 to-transparent" />
                    <span className="font-mono text-xs text-divergence-crimson font-bold z-10">
                      GLAZED SLICK SURFACE
                    </span>
                  </div>
                  <p className="text-[11px] text-on-surface-variant font-mono">
                    Silicone release agent intact. Cement applied without mechanical tooth.
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
                <span>INSPECT CRITICAL DIVERGENCE (STEP 2)</span>
              </button>

              <button
                onClick={onLaunchRetry}
                className="px-5 py-2 rounded-lg bg-transmission-emerald hover:bg-transmission-emerald/90 text-background text-xs font-mono font-bold flex items-center gap-2 shadow-lg shadow-transmission-emerald/20 transition-all hover:scale-[1.02]"
              >
                <span>RETRY SURFACE PREPARATION</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Rubric HUD (4 cols) */}
        <div className="xl:col-span-4 h-full">
          <RubricHUD
            telemetry={telemetry}
            currentTime={32.0}
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
