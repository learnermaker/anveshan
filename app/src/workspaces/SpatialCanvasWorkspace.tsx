import React, { useState } from 'react';
import { Eye, Grid, Layers, Sparkles, CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck, Compass } from 'lucide-react';
import type { CapabilityCase } from '../types/workspace';
import { RubricHUD } from '../components/RubricHUD';
import { TransmissionGainHero } from '../components/TransmissionGainHero';

interface SpatialCanvasWorkspaceProps {
  capCase: CapabilityCase;
  onOpenLineage: () => void;
  onJumpFirstDivergence: () => void;
  onLaunchRetry: () => void;
}

export function SpatialCanvasWorkspace({
  capCase,
  onOpenLineage,
  onJumpFirstDivergence,
  onLaunchRetry,
}: SpatialCanvasWorkspaceProps) {
  const telemetry = capCase.telemetry;
  const [showReference, setShowReference] = useState<boolean>(true);
  const [showLearner, setShowLearner] = useState<boolean>(true);
  const [showSymmetryGuides, setShowSymmetryGuides] = useState<boolean>(true);
  const [activePulli, setActivePulli] = useState<{ r: number; c: number } | null>({ r: 3, c: 4 });
  const [selectedCriterionId, setSelectedCriterionId] = useState<string | null>('CRIT-KOLAM-LOOP');

  // 5x5 Pulli Grid Points
  const gridSize = 5;
  const dotSpacing = 80;
  const offsetX = 80;
  const offsetY = 80;

  return (
    <div className="flex flex-col gap-6 w-full animate-fade-in">
      {/* Main Grid: Spatial Canvas on Left (8 cols) + Rubric HUD on Right (4 cols) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left Column: Interactive Spatial Practice Canvas */}
        <div className="xl:col-span-8 flex flex-col gap-4">
          <div className="bg-surface-elevated border border-outline rounded-xl p-5 shadow-xl relative overflow-hidden">
            {/* Canvas Header & Toggles */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-outline pb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-transmission-emerald/15 border border-transmission-emerald/30 flex items-center justify-center text-transmission-emerald">
                  <Compass className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-widest text-transmission-emerald font-bold">
                    SPATIAL PRACTICE CANVAS // VECTOR TRAJECTORY ENGINE
                  </div>
                  <h3 className="text-base font-semibold text-on-surface">
                    5×5 Orthogonal Pulli Lattice & Closed Brahma Mudi Topology
                  </h3>
                </div>
              </div>

              {/* Layer Visibility Controls */}
              <div className="flex items-center gap-2 text-xs font-mono">
                <button
                  onClick={() => setShowReference(!showReference)}
                  className={`px-3 py-1.5 rounded border transition-colors flex items-center gap-1.5 ${
                    showReference
                      ? 'bg-transmission-emerald/15 border-transmission-emerald text-transmission-emerald font-semibold'
                      : 'bg-surface-dim border-outline text-on-surface-variant'
                  }`}
                >
                  <span className="w-2 h-2 rounded-full bg-transmission-emerald" />
                  EXPERT PATH
                </button>
                <button
                  onClick={() => setShowLearner(!showLearner)}
                  className={`px-3 py-1.5 rounded border transition-colors flex items-center gap-1.5 ${
                    showLearner
                      ? 'bg-divergence-crimson/15 border-divergence-crimson text-divergence-crimson font-semibold'
                      : 'bg-surface-dim border-outline text-on-surface-variant'
                  }`}
                >
                  <span className="w-2 h-2 rounded-full bg-divergence-crimson" />
                  LEARNER PATH
                </button>
                <button
                  onClick={() => setShowSymmetryGuides(!showSymmetryGuides)}
                  className={`px-3 py-1.5 rounded border transition-colors flex items-center gap-1.5 ${
                    showSymmetryGuides
                      ? 'bg-caliper-cyan/15 border-caliper-cyan text-caliper-cyan font-semibold'
                      : 'bg-surface-dim border-outline text-on-surface-variant'
                  }`}
                >
                  <Grid className="w-3.5 h-3.5" />
                  SYMMETRY AXES
                </button>
              </div>
            </div>

            {/* SVG Interactive Drawing Plane */}
            <div className="relative w-full h-[440px] bg-surface-dim rounded-lg border border-outline/40 my-4 flex items-center justify-center overflow-hidden">
              <svg
                viewBox="0 0 480 480"
                className="w-full h-full max-w-[440px] max-h-[440px] select-none"
              >
                <defs>
                  <radialGradient id="pulliGlow" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#ffb951" stopOpacity="0.8" />
                    <stop offset="100%" stopColor="#ffb951" stopOpacity="0.0" />
                  </radialGradient>
                </defs>

                {/* Grid Symmetry Guidelines */}
                {showSymmetryGuides && (
                  <g className="stroke-caliper-cyan/25 stroke-[1] stroke-dasharray-[4,4]">
                    {/* Vertical Center Axis */}
                    <line x1="240" y1="20" x2="240" y2="460" strokeDasharray="4 4" />
                    {/* Horizontal Center Axis */}
                    <line x1="20" y1="240" x2="460" y2="240" strokeDasharray="4 4" />
                    {/* Diagonal Axes */}
                    <line x1="40" y1="40" x2="440" y2="440" strokeDasharray="3 3" opacity="0.6" />
                    <line x1="440" y1="40" x2="40" y2="440" strokeDasharray="3 3" opacity="0.6" />
                  </g>
                )}

                {/* Reference Path (Green Smooth Curves) */}
                {showReference && (
                  <g fill="none" stroke="#22c55e" strokeWidth="3" opacity="0.85" strokeLinecap="round" strokeLinejoin="round">
                    {/* Closed Brahma Mudi Loop Paths */}
                    <path d="M 80,240 C 80,160 160,80 240,80 C 320,80 400,160 400,240 C 400,320 320,400 240,400 C 160,400 80,320 80,240 Z" />
                    <path d="M 160,240 Q 240,160 320,240 Q 240,320 160,240 Z" strokeWidth="2.5" />
                    <path d="M 240,160 C 200,200 200,280 240,320 C 280,280 280,200 240,160 Z" strokeWidth="2" strokeDasharray="2 2" />
                  </g>
                )}

                {/* Learner Baseline Path (Red Slicing Error at Dot 3, 4) */}
                {showLearner && (
                  <g fill="none" stroke="#ef4444" strokeWidth="3" opacity="0.9" strokeLinecap="round">
                    <path d="M 80,240 C 80,160 160,80 240,80 C 320,80 360,120 320,160" />
                    {/* Slicing right through dot (3, 4) at (320, 240) */}
                    <line x1="320" y1="160" x2="320" y2="320" stroke="#ef4444" strokeWidth="3.5" />
                    <path d="M 320,320 C 320,360 280,400 240,400 C 160,400 80,320 80,240" strokeDasharray="4 2" />
                  </g>
                )}

                {/* 5x5 Pulli Dot Lattice */}
                {Array.from({ length: gridSize }).map((_, r) =>
                  Array.from({ length: gridSize }).map((_, c) => {
                    const cx = offsetX + c * dotSpacing;
                    const cy = offsetY + r * dotSpacing;
                    const isDivergent = r === 2 && c === 3; // Coordinate (3, 4) 1-based

                    return (
                      <g
                        key={`${r}-${c}`}
                        onClick={() => setActivePulli({ r: r + 1, c: c + 1 })}
                        className="cursor-pointer group"
                      >
                        {isDivergent && (
                          <circle cx={cx} cy={cy} r="18" fill="url(#pulliGlow)" className="animate-pulse" />
                        )}
                        <circle
                          cx={cx}
                          cy={cy}
                          r={isDivergent ? '7' : '4.5'}
                          className={`transition-all ${
                            isDivergent
                              ? 'fill-divergence-crimson stroke-white stroke-[1.5]'
                              : 'fill-cadmium-amber/90 group-hover:fill-white'
                          }`}
                        />
                        {isDivergent && (
                          <g transform={`translate(${cx + 12}, ${cy - 12})`}>
                            <rect x="0" y="0" width="110" height="24" rx="4" fill="#18181b" stroke="#ef4444" strokeWidth="1" />
                            <text x="6" y="16" fill="#ef4444" fontSize="10" fontFamily="monospace" fontWeight="bold">
                              FIRST DIVERGENCE
                            </text>
                          </g>
                        )}
                      </g>
                    );
                  })
                )}
              </svg>

              {/* Bottom Canvas Telemetry Pill */}
              <div className="absolute bottom-3 left-3 bg-surface-elevated/90 border border-outline px-3 py-1.5 rounded font-mono text-[11px] text-on-surface-variant flex items-center gap-3 backdrop-blur-md">
                <span>COORD: <strong className="text-on-surface">PULLI (3, 4)</strong></span>
                <span className="text-outline">|</span>
                <span>CLEARANCE: <strong className="text-divergence-crimson">0.0 mm (INTERSECTED)</strong></span>
                <span className="text-outline">|</span>
                <span>SYMMETRY: <strong className="text-cadmium-amber">64% FIDELITY</strong></span>
              </div>
            </div>

            {/* Canvas Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
              <div className="flex items-center gap-2">
                <button
                  onClick={onJumpFirstDivergence}
                  className="px-4 py-2 rounded-lg bg-divergence-crimson/20 border border-divergence-crimson/40 text-divergence-crimson hover:bg-divergence-crimson/30 text-xs font-mono font-bold flex items-center gap-2 transition-colors"
                >
                  <AlertTriangle className="w-4 h-4" />
                  <span>JUMP TO FIRST DIVERGENCE (DOT 3,4)</span>
                </button>
              </div>

              <button
                onClick={onLaunchRetry}
                className="px-5 py-2 rounded-lg bg-transmission-emerald hover:bg-transmission-emerald/90 text-background text-xs font-mono font-bold flex items-center gap-2 shadow-lg shadow-transmission-emerald/20 transition-all hover:scale-[1.02]"
              >
                <span>START ORBITAL RETRY</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Rubric HUD (4 cols) */}
        <div className="xl:col-span-4 h-full">
          <RubricHUD
            telemetry={telemetry}
            currentTime={14.2}
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
