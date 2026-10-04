import React from 'react';
import { Volume2, Activity, Eye, Zap, Crosshair } from 'lucide-react';
import type { SensoryCueAnnotation, TransmissionTelemetry } from '../data/adapter';

interface SensoryRibbonProps {
  telemetry: TransmissionTelemetry;
  currentTime: number;
  onTimeChange: (time: number) => void;
}

export const SensoryRibbon: React.FC<SensoryRibbonProps> = ({
  telemetry,
  currentTime,
  onTimeChange,
}) => {
  const totalDuration = 35.0;
  const currentPercent = (currentTime / totalDuration) * 100;

  // Generate synthetic waveform bars for the 35-second timeline
  // Highlighting:
  // - 4.5s - 12.0s: Tactile drag (medium continuous height)
  // - 18.4s, 18.8s, 19.2s: Acoustic ratchet clicks (tall spike heights)
  // - 26.0s - 31.0s: Settle zone (decaying height)
  const numBars = 140; // 4 bars per second
  const bars = Array.from({ length: numBars }).map((_, idx) => {
    const sec = (idx / numBars) * totalDuration;
    let height = 15; // baseline noise
    let color = '#2e353b';

    // Tactile drag zone
    if (sec >= 4.5 && sec <= 12.0) {
      height = 35 + Math.sin(idx * 0.8) * 12;
      color = '#00e5ff'; // Caliper cyan
    }
    // Approach
    else if (sec > 12.0 && sec < 18.0) {
      height = 20 + Math.sin(idx * 0.5) * 8;
    }
    // Ratchet clicks (sharp impulse spikes)
    else if (Math.abs(sec - 18.4) < 0.25 || Math.abs(sec - 18.8) < 0.25 || Math.abs(sec - 19.2) < 0.25) {
      height = 85 + Math.random() * 15;
      color = '#e67e22'; // Cadmium amber
    }
    // Settle zone
    else if (sec >= 26.0 && sec <= 31.0) {
      const progress = (sec - 26.0) / 5.0;
      height = 50 * Math.exp(-progress * 2.5) + 12;
      color = '#10b981'; // Transmission emerald
    }

    return { sec, height, color };
  });

  return (
    <div className="bg-surface-container-low border border-outline rounded-lg p-3 relative flex flex-col gap-2 shadow-lg">
      {/* Ribbon Header & Legend */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cadmium-amber" />
          <span className="font-mono text-xs font-bold text-on-surface uppercase tracking-wider">
            MULTI-MODAL SENSORY CUE WAVEFORM RIBBON
          </span>
          <span className="text-[10px] font-mono text-on-surface-variant">
            (ACOUSTIC TORQUE + TACTILE DRAG + PARALLAX OPTICS)
          </span>
        </div>

        {/* Legend */}
        <div className="hidden sm:flex items-center gap-3 text-[10px] font-mono">
          <span className="flex items-center gap-1 text-caliper-cyan">
            <span className="w-2 h-2 rounded bg-caliper-cyan/60" />
            TACTILE FRICTION (04.5s – 12.0s)
          </span>
          <span className="flex items-center gap-1 text-cadmium-amber">
            <span className="w-2 h-2 rounded bg-cadmium-amber" />
            RATCHET CLUTCH SPIKES (18.4s – 19.2s)
          </span>
          <span className="flex items-center gap-1 text-transmission-emerald">
            <span className="w-2 h-2 rounded bg-transmission-emerald" />
            NEEDLE SETTLE (26.0s – 31.0s)
          </span>
        </div>
      </div>

      {/* Waveform Spectrogram Container */}
      <div
        className="relative h-20 bg-surface-container-lowest rounded border border-outline overflow-hidden cursor-pointer select-none group"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const clickX = e.clientX - rect.left;
          const ratio = Math.max(0, Math.min(1, clickX / rect.width));
          onTimeChange(ratio * totalDuration);
        }}
      >
        {/* Background Grid */}
        <div className="absolute inset-0 telemetry-grid opacity-50 pointer-events-none" />

        {/* Waveform Bars */}
        <div className="absolute inset-0 flex items-center justify-between px-1 pointer-events-none">
          {bars.map((bar, idx) => (
            <div
              key={idx}
              className="w-1 rounded-full transition-all"
              style={{
                height: `${bar.height}%`,
                backgroundColor: bar.color,
                opacity: idx / numBars <= currentPercent / 100 ? 1 : 0.45,
              }}
            />
          ))}
        </div>

        {/* Region Highlight Overlays */}
        {/* Region 1: Wipe */}
        <div
          className="absolute top-0 bottom-0 bg-caliper-cyan/5 border-l border-r border-caliper-cyan/30 pointer-events-none"
          style={{
            left: `${(4.5 / totalDuration) * 100}%`,
            width: `${((12.0 - 4.5) / totalDuration) * 100}%`,
          }}
        />

        {/* Region 2: Ratchet Clicks */}
        <div
          className="absolute top-0 bottom-0 bg-cadmium-amber/10 border-l border-r border-cadmium-amber/40 pointer-events-none"
          style={{
            left: `${(18.0 / totalDuration) * 100}%`,
            width: `${((22.5 - 18.0) / totalDuration) * 100}%`,
          }}
        />

        {/* Region 3: Dial needle settle */}
        <div
          className="absolute top-0 bottom-0 bg-transmission-emerald/5 border-l border-r border-transmission-emerald/30 pointer-events-none"
          style={{
            left: `${(26.0 / totalDuration) * 100}%`,
            width: `${((31.0 - 26.0) / totalDuration) * 100}%`,
          }}
        />

        {/* Moving Active Playhead Needle */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-cadmium-amber shadow-[0_0_10px_#e67e22] z-20 pointer-events-none transition-all duration-75"
          style={{ left: `${currentPercent}%` }}
        >
          {/* Top playhead indicator badge */}
          <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 w-2.5 h-2.5 bg-cadmium-amber rotate-45" />
          <div className="absolute top-1 left-2 font-mono text-[9px] bg-cadmium-amber text-surface-container-lowest font-bold px-1 rounded shadow">
            {currentTime.toFixed(1)}s
          </div>
        </div>
      </div>

      {/* Sensory Cue Interactive Markers Along Timeline */}
      <div className="flex flex-wrap items-center gap-1.5 pt-1">
        <span className="font-mono text-[10px] text-on-surface-variant uppercase mr-1">
          EVIDENCE PINS:
        </span>
        {telemetry.sensoryCues.map((cue) => {
          const isActive = Math.abs(currentTime - cue.timeSec) < 1.5;
          return (
            <button
              key={cue.id}
              onClick={() => onTimeChange(cue.timeSec)}
              className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono border transition-all ${
                isActive
                  ? 'bg-cadmium-amber text-surface-container-lowest border-cadmium-amber font-bold shadow-[0_0_8px_rgba(230,126,34,0.4)]'
                  : 'bg-surface-container-highest border-outline text-on-surface-variant hover:text-on-surface hover:border-on-surface-variant'
              }`}
              title={cue.description}
            >
              {cue.category === 'acoustic' && <Volume2 className="w-2.5 h-2.5" />}
              {cue.category === 'tactile' && <Zap className="w-2.5 h-2.5" />}
              {cue.category === 'visual' && <Eye className="w-2.5 h-2.5" />}
              <span>{cue.label}</span>
              <span className="opacity-70">@{cue.timeSec.toFixed(1)}s</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
