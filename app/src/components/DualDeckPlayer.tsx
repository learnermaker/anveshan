import React, { useState, useEffect, useRef } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Rewind,
  Crosshair,
  Volume2,
  AlertTriangle,
  CheckCircle2,
  Sliders,
  Layers,
  Sparkles,
} from 'lucide-react';
import type { TransmissionTelemetry } from '../data/adapter';

interface DualDeckPlayerProps {
  telemetry: TransmissionTelemetry;
  currentTime: number;
  onTimeChange: (time: number) => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
}

export const DualDeckPlayer: React.FC<DualDeckPlayerProps> = ({
  telemetry,
  currentTime,
  onTimeChange,
  isPlaying,
  onTogglePlay,
}) => {
  const [learnerMode, setLearnerMode] = useState<'baseline' | 'retry'>('retry');
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [diffOverlay, setDiffOverlay] = useState<boolean>(false);
  const totalDuration = 35.0; // 35 seconds total procedure

  // Jump to first divergence action
  const handleJumpToFirstDivergence = () => {
    onTimeChange(telemetry.firstDivergenceSec);
    setLearnerMode('baseline'); // Automatically show the baseline divergence
  };

  // Determine current active phase based on time
  const getPhaseInfo = (time: number) => {
    if (time < 4.5) return { name: 'Anvil Surface Inspection', crit: null, desc: 'Optical magnification verify surface purity' };
    if (time <= 12.0) return { name: 'Face Cleaning Motion', crit: 'CRIT-WIPE', desc: 'Unidirectional drag with optical lint-free tissue' };
    if (time <= 18.0) return { name: 'Spindle Approach & Parallax Check', crit: null, desc: 'Smooth thimble rotation to 0.5mm clearance' };
    if (time <= 22.5) return { name: 'Ratchet Stop Torque Cadence', crit: 'CRIT-RATCHET', desc: 'Uniform 3-click clutch engagement at 5.0N' };
    if (time <= 26.0) return { name: 'Parallax Null Alignment', crit: null, desc: 'Visual alignment of thimble zero index with barrel datum' };
    return { name: 'Spindle Clamp Engagement', crit: 'CRIT-LOCK', desc: 'Lock lever engaged only after dial indicator needle settles' };
  };

  const phase = getPhaseInfo(currentTime);

  // Time format helper (MM:SS.f)
  const formatTime = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = (sec % 60).toFixed(1);
    return `${mins.toString().padStart(2, '0')}:${parseFloat(secs) < 10 ? '0' : ''}${secs}`;
  };

  return (
    <div className="bg-surface-container-low border border-outline rounded-lg overflow-hidden flex flex-col shadow-2xl relative">
      {/* Top Deck Action Bar */}
      <div className="px-4 py-2 bg-surface-container border-b border-outline flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-on-surface uppercase tracking-wider flex items-center gap-1.5">
            <Crosshair className="w-3.5 h-3.5 text-cadmium-amber" />
            DUAL-DECK COMPARATIVE TELEMETRY
          </span>
          <span className="text-outline text-xs">|</span>
          <span className="font-mono text-[11px] text-caliper-cyan">
            PHASE: <span className="text-on-surface font-semibold">{phase.name}</span>
          </span>
          {phase.crit && (
            <span className="font-mono text-[10px] bg-cadmium-amber/20 text-cadmium-amber border border-cadmium-amber/40 px-1.5 py-0.2 rounded font-bold">
              {phase.crit}
            </span>
          )}
        </div>

        {/* Quick Actions: Jump to First Divergence */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleJumpToFirstDivergence}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-cadmium-amber hover:bg-cadmium-amber/90 text-surface-container-lowest font-mono font-bold text-xs shadow-[0_0_16px_rgba(230,126,34,0.35)] transition-all transform active:scale-95"
            title="Snap playhead to 00:19.2 where baseline learner diverged on ratchet torque"
          >
            <Rewind className="w-3.5 h-3.5 fill-current" />
            <span>JUMP TO FIRST DIVERGENCE (00:19.2)</span>
          </button>

          <button
            onClick={() => setDiffOverlay(!diffOverlay)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded font-mono text-[11px] border transition-colors ${
              diffOverlay
                ? 'bg-caliper-cyan/20 border-caliper-cyan text-caliper-cyan'
                : 'bg-surface-container-highest border-outline text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <Layers className="w-3 h-3" />
            <span>DIFF OVERLAY</span>
          </button>
        </div>
      </div>

      {/* Main Comparative Video Workspaces */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-outline relative">
        {/* LEFT DECK: EXPERT REFERENCE */}
        <div className="bg-surface-container-lowest p-4 flex flex-col relative group">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cadmium-amber" />
              <span className="font-mono text-xs font-bold text-on-surface uppercase tracking-wide">
                EXPERT REFERENCE
              </span>
              <span className="text-[11px] font-sans text-on-surface-variant">
                Reference Expert (Synthetic Fixture)
              </span>
            </div>
            <div className="font-mono text-[10px] text-transmission-emerald bg-transmission-emerald/10 border border-transmission-emerald/30 px-2 py-0.5 rounded">
              REPLAY REFERENCE
            </div>
          </div>

          {/* Precision Micrometer Simulation Canvas (Left) */}
          <div className="w-full aspect-video bg-surface-container-lowest rounded border border-outline relative overflow-hidden flex items-center justify-center telemetry-grid">
            {/* Authentic Photographic Benchmark Background from Stitch */}
            <img
              src="/assets/expert-reference.jpg"
              alt="Synthetic micrometer reference replay"
              className="absolute inset-0 w-full h-full object-cover opacity-75 mix-blend-luminosity filter contrast-125 brightness-95"
            />
            {/* Subtle darkroom optics vignette */}
            <div className="absolute inset-0 bg-gradient-to-t from-surface-container-lowest via-surface-container-lowest/30 to-surface-container-lowest/60" />

            {/* Caliper Reticle Overlay */}
            <div className="reticle-corner reticle-tl" />
            <div className="reticle-corner reticle-tr" />
            <div className="reticle-corner reticle-bl" />
            <div className="reticle-corner reticle-br" />

            {/* Central Optical Micrometer Visualizer */}
            <div className="relative z-10 w-full h-full flex items-center justify-center p-6">
              {/* SVG Technical Instrument Schematics */}
              <svg className="w-full h-full max-h-56" viewBox="0 0 400 220" fill="none">
                {/* Frame C-clamp */}
                <path
                  d="M 60 110 C 60 50, 180 50, 240 70 L 240 90 C 190 75, 90 75, 90 110 C 90 145, 190 145, 240 130 L 240 150 C 180 170, 60 170, 60 110 Z"
                  fill="#1c2124"
                  stroke="#2e353b"
                  strokeWidth="2"
                />
                {/* Fixed Anvil (Left) */}
                <rect x="235" y="96" width="20" height="28" fill="#9ba1a6" stroke="#4a5560" strokeWidth="1" />
                {/* Carbide face */}
                <rect x="253" y="98" width="4" height="24" fill="#00e5ff" />

                {/* Spindle (Right) with dynamic motion based on time */}
                {(() => {
                  const spindleOffset = currentTime < 18.0 ? (18.0 - currentTime) * 1.5 : 0;
                  return (
                    <g transform={`translate(${spindleOffset}, 0)`}>
                      {/* Spindle Carbide face */}
                      <rect x="261" y="98" width="4" height="24" fill="#00e5ff" />
                      {/* Spindle shaft */}
                      <rect x="265" y="99" width="45" height="22" fill="#717a84" stroke="#4a5560" strokeWidth="1" />
                      {/* Micrometer Barrel & Sleeve with Vernier Lines */}
                      <rect x="310" y="92" width="45" height="36" fill="#242a2e" stroke="#2e353b" strokeWidth="1.5" />
                      {/* Sleeve gradations */}
                      <line x1="315" y1="110" x2="350" y2="110" stroke="#edece8" strokeWidth="1" />
                      <line x1="320" y1="102" x2="320" y2="110" stroke="#edece8" strokeWidth="0.8" />
                      <line x1="330" y1="102" x2="330" y2="110" stroke="#edece8" strokeWidth="0.8" />
                      <line x1="340" y1="102" x2="340" y2="110" stroke="#edece8" strokeWidth="0.8" />

                      {/* Ratchet Speed Thimble with Cadmium Amber clutch indicator */}
                      <rect x="355" y="95" width="28" height="30" fill="#14181a" stroke="#e67e22" strokeWidth="1.2" />
                      {/* Knurling ridges */}
                      <line x1="360" y1="96" x2="360" y2="124" stroke="#e67e22" strokeWidth="0.8" opacity="0.6" />
                      <line x1="365" y1="96" x2="365" y2="124" stroke="#e67e22" strokeWidth="0.8" opacity="0.6" />
                      <line x1="370" y1="96" x2="370" y2="124" stroke="#e67e22" strokeWidth="0.8" opacity="0.6" />
                      <line x1="375" y1="96" x2="375" y2="124" stroke="#e67e22" strokeWidth="0.8" opacity="0.6" />
                    </g>
                  );
                })()}

                {/* Optical Tissue Drag Action (4.5s – 12.0s) */}
                {currentTime >= 4.5 && currentTime <= 12.0 && (
                  <g className="animate-pulse">
                    <line x1="258" y1="70" x2="258" y2="150" stroke="#00e5ff" strokeWidth="3" strokeDasharray="4 2" />
                    <text x="265" y="65" fill="#00e5ff" fontSize="9" fontFamily="JetBrains Mono">
                      UNIDIRECTIONAL DRAG (CRIT-WIPE)
                    </text>
                  </g>
                )}

                {/* Audible Ratchet Wave Waves (18.0s – 22.5s) */}
                {currentTime >= 18.0 && currentTime <= 22.5 && (
                  <g>
                    <circle cx="370" cy="110" r="16" stroke="#10b981" strokeWidth="1" fill="none" opacity="0.8" className="animate-ping" />
                    <circle cx="370" cy="110" r="28" stroke="#10b981" strokeWidth="1" fill="none" opacity="0.4" />
                    <text x="290" y="165" fill="#10b981" fontSize="10" fontFamily="JetBrains Mono" fontWeight="bold">
                      CLICK 3x @ 0.5s CADENCE (CRIT-RATCHET)
                    </text>
                  </g>
                )}

                {/* Needle Stabilization Indicator (26.0s+) */}
                {currentTime >= 26.0 && (
                  <g>
                    <rect x="120" y="85" width="50" height="50" rx="25" fill="#0b0d0e" stroke="#10b981" strokeWidth="1.5" />
                    <line x1="145" y1="110" x2="145" y2="92" stroke="#10b981" strokeWidth="1.5" />
                    <circle cx="145" cy="110" r="2.5" fill="#10b981" />
                    <text x="122" y="150" fill="#10b981" fontSize="9" fontFamily="JetBrains Mono">
                      NEEDLE: 0.0000in
                    </text>
                  </g>
                )}

                {/* Crosshair optical reticle in cyan */}
                <line x1="200" y1="20" x2="200" y2="200" stroke="#00e5ff" strokeWidth="0.5" strokeDasharray="3 3" opacity="0.35" />
                <line x1="20" y1="110" x2="380" y2="110" stroke="#00e5ff" strokeWidth="0.5" strokeDasharray="3 3" opacity="0.35" />
                <circle cx="200" cy="110" r="40" stroke="#00e5ff" strokeWidth="0.5" opacity="0.25" />
              </svg>

              {/* Angle Caliper Telemetry Badge */}
              <div className="absolute top-2 left-2 bg-surface-container-highest/90 border border-outline px-2 py-1 rounded text-[10px] font-mono flex flex-col gap-0.5">
                <span className="text-caliper-cyan">APPROACH ANGLE: 45.2° [CALIBRATED]</span>
                <span className="text-on-surface-variant">TORQUE FORCE: 5.0N STABLE</span>
              </div>

              {/* Timecode watermark */}
              <div className="absolute bottom-2 right-2 font-mono text-[11px] bg-surface-container-lowest/80 px-2 py-0.5 rounded text-cadmium-amber border border-outline">
                {formatTime(currentTime)} / 00:35.0
              </div>
            </div>
          </div>

          {/* Expert Observation Note */}
          <div className="mt-2 text-xs font-sans text-on-surface-variant bg-surface-container p-2 rounded border border-outline flex items-start gap-2">
            <span className="font-mono text-[10px] text-cadmium-amber uppercase font-bold shrink-0 mt-0.5">
              CANONICAL EVIDENCE:
            </span>
            <span>
              {phase.desc}. Zero axial spindle twist; ratchet clutch disengages at exactly 5N contact pressure.
            </span>
          </div>
        </div>

        {/* RIGHT DECK: LEARNER ATTEMPT */}
        <div className="bg-surface-container-lowest p-4 flex flex-col relative group">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${learnerMode === 'baseline' ? 'bg-divergence-crimson' : 'bg-transmission-emerald'}`} />
              <span className="font-mono text-xs font-bold text-on-surface uppercase tracking-wide">
                LEARNER ATTEMPT
              </span>
              <span className="text-[11px] font-sans text-on-surface-variant">
                Learner (Replay Fixture)
              </span>
            </div>

            {/* Baseline vs Retry Switcher */}
            <div className="flex items-center bg-surface-container-highest p-0.5 rounded border border-outline">
              <button
                onClick={() => setLearnerMode('baseline')}
                className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                  learnerMode === 'baseline'
                    ? 'bg-divergence-crimson text-surface-container-lowest font-bold'
                    : 'text-on-surface-variant hover:text-on-surface'
                }`}
              >
                BASELINE (1.5 PTS)
              </button>
              <button
                onClick={() => setLearnerMode('retry')}
                className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                  learnerMode === 'retry'
                    ? 'bg-transmission-emerald text-surface-container-lowest font-bold'
                    : 'text-on-surface-variant hover:text-on-surface'
                }`}
              >
                RETRY 02 (7.0 PTS)
              </button>
            </div>
          </div>

          {/* Precision Micrometer Simulation Canvas (Right - Learner) */}
          <div className="w-full aspect-video bg-surface-container-lowest rounded border border-outline relative overflow-hidden flex items-center justify-center telemetry-grid">
            {/* Authentic Photographic Learner Background from Stitch */}
            <img
              src="/assets/learner-attempt.jpg"
              alt="Learner micrometer replay fixture"
              className={`absolute inset-0 w-full h-full object-cover transition-all duration-300 ${
                learnerMode === 'baseline'
                  ? 'opacity-65 mix-blend-luminosity filter sepia-[0.35] hue-rotate-[315deg] contrast-125'
                  : 'opacity-75 mix-blend-luminosity filter contrast-125 brightness-95'
              }`}
            />
            {/* Dynamic divergence vs calibrated vignette */}
            <div
              className={`absolute inset-0 transition-colors duration-300 ${
                learnerMode === 'baseline' && currentTime >= 18.0
                  ? 'bg-gradient-to-t from-divergence-crimson/25 via-surface-container-lowest/30 to-surface-container-lowest/60'
                  : 'bg-gradient-to-t from-surface-container-lowest via-surface-container-lowest/30 to-surface-container-lowest/60'
              }`}
            />

            <div className="reticle-corner reticle-tl" />
            <div className="reticle-corner reticle-tr" />
            <div className="reticle-corner reticle-bl" />
            <div className="reticle-corner reticle-br" />

            <div className="relative z-10 w-full h-full flex items-center justify-center p-6">
              <svg className="w-full h-full max-h-56" viewBox="0 0 400 220" fill="none">
                {/* Frame C-clamp */}
                <path
                  d="M 60 110 C 60 50, 180 50, 240 70 L 240 90 C 190 75, 90 75, 90 110 C 90 145, 190 145, 240 130 L 240 150 C 180 170, 60 170, 60 110 Z"
                  fill="#1c2124"
                  stroke={learnerMode === 'baseline' && currentTime >= 18.0 ? '#f87171' : '#2e353b'}
                  strokeWidth="2"
                />
                <rect x="235" y="96" width="20" height="28" fill="#9ba1a6" stroke="#4a5560" strokeWidth="1" />
                <rect x="253" y="98" width="4" height="24" fill={learnerMode === 'baseline' ? '#f87171' : '#00e5ff'} />

                {/* Spindle with simulated learner motion */}
                {(() => {
                  let spindleOffset = 0;
                  if (learnerMode === 'baseline') {
                    // Learner in baseline cranks too fast and overcompresses spindle
                    spindleOffset = currentTime < 16.0 ? (16.0 - currentTime) * 2.2 : -2;
                  } else {
                    spindleOffset = currentTime < 18.0 ? (18.0 - currentTime) * 1.5 : 0;
                  }

                  return (
                    <g transform={`translate(${spindleOffset}, 0)`}>
                      <rect x="261" y="98" width="4" height="24" fill={learnerMode === 'baseline' ? '#f87171' : '#00e5ff'} />
                      <rect x="265" y="99" width="45" height="22" fill="#717a84" stroke="#4a5560" strokeWidth="1" />
                      <rect x="310" y="92" width="45" height="36" fill="#242a2e" stroke="#2e353b" strokeWidth="1.5" />
                      <line x1="315" y1="110" x2="350" y2="110" stroke="#edece8" strokeWidth="1" />

                      {/* Thimble */}
                      <rect
                        x="355"
                        y="95"
                        width="28"
                        height="30"
                        fill="#14181a"
                        stroke={learnerMode === 'baseline' ? '#f87171' : '#10b981'}
                        strokeWidth="1.5"
                      />
                    </g>
                  );
                })()}

                {/* Divergence Visual Callouts in Baseline Mode */}
                {learnerMode === 'baseline' ? (
                  <>
                    {/* Scrubbing divergence during wipe (4.5s – 12.0s) */}
                    {currentTime >= 4.5 && currentTime <= 12.0 && (
                      <g className="animate-bounce">
                        <circle cx="258" cy="110" r="14" stroke="#f87171" strokeWidth="2" strokeDasharray="3 3" fill="none" />
                        <text x="210" y="165" fill="#f87171" fontSize="9" fontFamily="JetBrains Mono" fontWeight="bold">
                          CIRCULAR SCRUB DETECTED (PARTIAL)
                        </text>
                      </g>
                    )}

                    {/* Violent over-torque divergence (18.0s – 22.5s) */}
                    {currentTime >= 18.0 && currentTime <= 22.5 && (
                      <g>
                        <circle cx="370" cy="110" r="22" stroke="#f87171" strokeWidth="2.5" fill="#f87171" fillOpacity="0.15" className="animate-ping" />
                        <text x="200" y="55" fill="#f87171" fontSize="10" fontFamily="JetBrains Mono" fontWeight="bold">
                          CRIT-RATCHET DIVERGENCE: 6 RAPID CLICKS (12.4N)
                        </text>
                        <text x="200" y="70" fill="#f87171" fontSize="8" fontFamily="JetBrains Mono">
                          Spindle over-compressed by 0.003mm!
                        </text>
                      </g>
                    )}

                    {/* Premature Lock lever engagement */}
                    {currentTime >= 26.0 && (
                      <g>
                        <text x="210" y="155" fill="#f87171" fontSize="9" fontFamily="JetBrains Mono" fontWeight="bold">
                          LOCK ENGAGED WHILE NEEDLE DRIFTING
                        </text>
                      </g>
                    )}
                  </>
                ) : (
                  /* Verified Aligned State in Retry Mode */
                  <>
                    {currentTime >= 18.0 && currentTime <= 22.5 && (
                      <g>
                        <circle cx="370" cy="110" r="16" stroke="#10b981" strokeWidth="1" fill="none" opacity="0.8" className="animate-ping" />
                        <text x="230" y="60" fill="#10b981" fontSize="10" fontFamily="JetBrains Mono" fontWeight="bold">
                          RETRY 02: 3 CLICKS @ 0.5s (CALIBRATED)
                        </text>
                      </g>
                    )}
                    {currentTime >= 26.0 && (
                      <g>
                        <text x="220" y="150" fill="#10b981" fontSize="9" fontFamily="JetBrains Mono" fontWeight="bold">
                          ZERO DEFLECTION // CALIBRATED
                        </text>
                      </g>
                    )}
                  </>
                )}
              </svg>

              {/* Status Badge in canvas */}
              <div className="absolute top-2 left-2 bg-surface-container-highest/90 border border-outline px-2 py-1 rounded text-[10px] font-mono flex flex-col gap-0.5">
                {learnerMode === 'baseline' ? (
                  <>
                    <span className="text-divergence-crimson flex items-center gap-1 font-bold">
                      <AlertTriangle className="w-3 h-3" />
                      DIVERGENCE ACTIVE: +7.4N OVER-TORQUE
                    </span>
                    <span className="text-on-surface-variant">CADENCE: 0.15s (VIOLENT CRANK)</span>
                  </>
                ) : (
                  <>
                    <span className="text-transmission-emerald flex items-center gap-1 font-bold">
                      <CheckCircle2 className="w-3 h-3" />
                      ALIGNED TECHNIQUE: 5.0N STANDARD
                    </span>
                    <span className="text-on-surface-variant">CADENCE: 0.50s (UNIFORM CLICK)</span>
                  </>
                )}
              </div>

              {/* Learner Frame Timecode */}
              <div className="absolute bottom-2 right-2 font-mono text-[11px] bg-surface-container-lowest/80 px-2 py-0.5 rounded text-on-surface border border-outline">
                {formatTime(currentTime)} / 00:35.0
              </div>
            </div>
          </div>

          {/* Diagnostic Note */}
          <div className="mt-2 text-xs font-sans bg-surface-container p-2 rounded border border-outline flex items-start gap-2">
            <span className={`font-mono text-[10px] uppercase font-bold shrink-0 mt-0.5 ${learnerMode === 'baseline' ? 'text-divergence-crimson' : 'text-transmission-emerald'}`}>
              {learnerMode === 'baseline' ? 'DIAGNOSTIC FAULT:' : 'REPLAY RETRY:'
            </span>
            <span className="text-on-surface-variant">
              {learnerMode === 'baseline'
                ? 'Apprentice applied 6 rapid ratchet clicks, introducing 12.4N clamping force which causes zero-datum error of +0.003mm.'
                : 'Apprentice paused after approach, applied exactly 3 steady ratchet clicks at 0.5s cadence, verified zero deflection.'}
            </span>
          </div>
        </div>
      </div>

      {/* Synchronized Playback Control Strip */}
      <div className="p-3 bg-surface-container border-t border-outline flex flex-wrap items-center justify-between gap-4">
        {/* Play/Pause & Step Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onTimeChange(0)}
            className="p-1.5 rounded bg-surface-container-highest hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-colors"
            title="Reset to 00:00"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <button
            onClick={() => onTimeChange(Math.max(0, currentTime - 1.0))}
            className="p-1.5 rounded bg-surface-container-highest hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-colors"
            title="Step Back 1s"
          >
            <Rewind className="w-4 h-4" />
          </button>

          <button
            onClick={onTogglePlay}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-cadmium-amber hover:bg-cadmium-amber/90 text-surface-container-lowest font-mono font-bold text-xs shadow-[0_0_12px_rgba(230,126,34,0.3)] transition-all"
          >
            {isPlaying ? (
              <>
                <Pause className="w-3.5 h-3.5 fill-current" />
                <span>PAUSE</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>SYNC PLAY</span>
              </>
            )}
          </button>

          <button
            onClick={() => onTimeChange(Math.min(totalDuration, currentTime + 1.0))}
            className="p-1.5 rounded bg-surface-container-highest hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-colors"
            title="Step Forward 1s"
          >
            <FastForward className="w-4 h-4" />
          </button>
        </div>

        {/* Master Timecode Scrubber Bar */}
        <div className="flex-1 max-w-xl flex items-center gap-3">
          <span className="font-mono text-xs text-cadmium-amber font-semibold shrink-0">
            {formatTime(currentTime)}
          </span>
          <div className="relative flex-1 group">
            <input
              type="range"
              min="0"
              max={totalDuration}
              step="0.1"
              value={currentTime}
              onChange={(e) => onTimeChange(parseFloat(e.target.value))}
              className="w-full h-2 bg-surface-container-highest rounded-lg appearance-none cursor-pointer accent-cadmium-amber focus:outline-none"
            />
            {/* First Divergence Marker on Slider */}
            <div
              className="absolute top-0 w-1 h-3 bg-divergence-crimson rounded pointer-events-none transform -translate-x-1/2 -translate-y-0.5 shadow-[0_0_6px_#f87171]"
              style={{ left: `${(telemetry.firstDivergenceSec / totalDuration) * 100}%` }}
              title="First Divergence: CRIT-RATCHET @ 19.2s"
            />
          </div>
          <span className="font-mono text-xs text-on-surface-variant shrink-0">
            {formatTime(totalDuration)}
          </span>
        </div>

        {/* Speed & Sync Indicators */}
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-on-surface-variant uppercase">SPEED:</span>
          {[0.5, 1.0].map((spd) => (
            <button
              key={spd}
              onClick={() => setPlaybackSpeed(spd)}
              className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                playbackSpeed === spd
                  ? 'bg-cadmium-amber text-surface-container-lowest font-bold'
                  : 'bg-surface-container-highest text-on-surface-variant hover:text-on-surface'
              }`}
            >
              {spd}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
