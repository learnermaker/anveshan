import React, { useState } from 'react';
import { AlertTriangle, ArrowRight, Music, Radio, Volume2, Sparkles, ShieldCheck } from 'lucide-react';
import type { CapabilityCase } from '../types/workspace';
import { RubricHUD } from '../components/RubricHUD';
import { TransmissionGainHero } from '../components/TransmissionGainHero';

interface RhythmInstrumentWorkspaceProps {
  capCase: CapabilityCase;
  onOpenLineage: () => void;
  onJumpFirstDivergence: () => void;
  onLaunchRetry: () => void;
}

export function RhythmInstrumentWorkspace({
  capCase,
  onOpenLineage,
  onJumpFirstDivergence,
  onLaunchRetry,
}: RhythmInstrumentWorkspaceProps) {
  const telemetry = capCase.telemetry;
  const [selectedCriterionId, setSelectedCriterionId] = useState<string | null>('CRIT-TIMING-SYNC');
  const [activeDrum, setActiveDrum] = useState<'both' | 'bayan' | 'dayan'>('both');

  return (
    <div className="flex flex-col gap-6 w-full animate-fade-in">
      {/* Main Grid: Audio-Visual Oscillogram on Left (8 cols) + Rubric HUD on Right (4 cols) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left Column: Rhythm Practice Instrument */}
        <div className="xl:col-span-8 flex flex-col gap-4">
          <div className="bg-surface-elevated border border-outline rounded-xl p-5 shadow-xl relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-outline pb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-transmission-emerald/15 border border-transmission-emerald/30 flex items-center justify-center text-transmission-emerald">
                  <Music className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-widest text-transmission-emerald font-bold">
                    RHYTHM PRACTICE INSTRUMENT // ACOUSTIC ONSET ENGINE
                  </div>
                  <h3 className="text-base font-semibold text-on-surface">
                    Bimanual Synchronization of "Dha" (Bayan Heel + Dayan Rim)
                  </h3>
                </div>
              </div>

              <div className="px-3 py-1 bg-divergence-crimson/15 border border-divergence-crimson/30 rounded font-mono text-xs text-divergence-crimson font-bold">
                TIMING DRIFT: -48ms
              </div>
            </div>

            {/* Drum Surface Mockup & Onset Visualization */}
            <div className="p-4 bg-surface-dim rounded-lg border border-outline/40 my-4 space-y-4">
              {/* Dual Drum Physical Surfaces */}
              <div className="grid grid-cols-2 gap-4">
                {/* Left Drum: Bayan (Bass) */}
                <div className="p-4 bg-surface-elevated rounded-lg border border-outline flex flex-col items-center justify-center relative group">
                  <div className="w-32 h-32 rounded-full bg-zinc-800 border-4 border-zinc-600 flex items-center justify-center relative shadow-inner">
                    {/* Bayan Syahi spot (black iron paste off-center) */}
                    <div className="w-16 h-16 rounded-full bg-zinc-950 border border-zinc-700 absolute top-4 left-6 flex items-center justify-center">
                      <span className="text-[11px] font-mono text-zinc-400">SYAHI</span>
                    </div>
                  </div>
                  <span className="mt-3 font-mono text-xs font-bold text-on-surface">
                    BAYAN (BASS DRUM)
                  </span>
                  <span className="text-[11px] font-mono text-cadmium-amber">
                    85Hz Modulation // Left Wrist
                  </span>
                </div>

                {/* Right Drum: Dayan (Treble) */}
                <div className="p-4 bg-surface-elevated rounded-lg border border-outline flex flex-col items-center justify-center relative group">
                  <div className="w-28 h-28 rounded-full bg-amber-950/40 border-4 border-amber-800 flex items-center justify-center relative shadow-inner">
                    {/* Dayan concentric Syahi */}
                    <div className="w-14 h-14 rounded-full bg-zinc-950 border border-zinc-700 flex items-center justify-center">
                      <span className="text-[11px] font-mono text-zinc-400">KINAR</span>
                    </div>
                  </div>
                  <span className="mt-3 font-mono text-xs font-bold text-on-surface">
                    DAYAN (TREBLE DRUM)
                  </span>
                  <span className="text-[11px] font-mono text-caliper-cyan">
                    440Hz Metallic Chime // Right Index
                  </span>
                </div>
              </div>

              {/* Acoustic Waveform & Timing Envelope */}
              <div className="p-3.5 bg-surface-elevated rounded border border-outline/40 space-y-2">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-on-surface-variant font-semibold flex items-center gap-1.5">
                    <Radio className="w-3.5 h-3.5 text-caliper-cyan" />
                    ACOUSTIC ONSET TIMELINE (44.1 kHz PCM WAVEFORM)
                  </span>
                  <span className="text-divergence-crimson font-bold">
                    DELTA T: -48ms (SPLIT HIT)
                  </span>
                </div>

                {/* Simulated Oscillogram */}
                <div className="h-28 bg-zinc-950 rounded p-2 border border-zinc-800 flex flex-col justify-center relative overflow-hidden">
                  {/* Grid Lines */}
                  <div className="absolute inset-0 flex items-center justify-between px-6 pointer-events-none opacity-20">
                    {Array.from({ length: 9 }).map((_, i) => (
                      <div key={i} className="h-full w-px bg-zinc-500" />
                    ))}
                  </div>

                  {/* Dayan Peak (Right Hand - early at 0ms) */}
                  <div className="text-[11px] font-mono text-caliper-cyan mb-1 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-caliper-cyan" />
                    DAYAN (TREBLE RIM) ONSET PEAK: 0.000s
                  </div>
                  <div className="w-full bg-zinc-900 h-6 rounded flex items-center px-1 mb-2">
                    <div className="w-12 h-5 bg-caliper-cyan/80 rounded" />
                    <div className="w-24 h-1 bg-caliper-cyan/30 rounded" />
                  </div>

                  {/* Bayan Peak (Left Hand - lagging by 48ms) */}
                  <div className="text-[11px] font-mono text-divergence-crimson mb-1 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-divergence-crimson" />
                    BAYAN (BASS HEEL) ONSET PEAK: +0.048s (LAGGING)
                  </div>
                  <div className="w-full bg-zinc-900 h-6 rounded flex items-center px-1">
                    <div className="w-16 h-1 bg-transparent" /> {/* 48ms gap */}
                    <div className="w-14 h-5 bg-divergence-crimson/80 rounded" />
                    <div className="w-32 h-1 bg-divergence-crimson/30 rounded" />
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] font-mono text-on-surface-variant pt-1">
                  <span>TARGET TOLERANCE: <strong className="text-transmission-emerald">+/- 15ms</strong></span>
                  <span>MEASURED TIMING GAP: <strong className="text-divergence-crimson">48ms FAULT</strong></span>
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
                <span>INSPECT 48ms TIMING DIVERGENCE</span>
              </button>

              <button
                onClick={onLaunchRetry}
                className="px-5 py-2 rounded-lg bg-transmission-emerald hover:bg-transmission-emerald/90 text-background text-xs font-mono font-bold flex items-center gap-2 shadow-lg shadow-transmission-emerald/20 transition-all hover:scale-[1.02]"
              >
                <span>RETRY BIMANUAL STRIKE</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Rubric HUD (4 cols) */}
        <div className="xl:col-span-4 h-full">
          <RubricHUD
            telemetry={telemetry}
            currentTime={4.2}
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
