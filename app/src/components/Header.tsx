import React from 'react';
import {
  Compass,
  CheckCircle2,
  Lock,
  Layers,
  Sparkles,
  Cpu,
  Fingerprint,
} from 'lucide-react';
import type { TransmissionTelemetry } from '../data/adapter';

export type LifecycleStage = 'source' | 'knowledge' | 'practice' | 'transmission';

interface HeaderProps {
  telemetry: TransmissionTelemetry;
  activeStage: LifecycleStage;
  onSelectStage: (stage: LifecycleStage) => void;
  onOpenStitchDesign?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  telemetry,
  activeStage,
  onSelectStage,
  onOpenStitchDesign,
}) => {
  const stages: { id: LifecycleStage; label: string; number: string; icon: typeof Compass }[] = [
    { id: 'source', number: '01', label: 'SOURCE', icon: Compass },
    { id: 'knowledge', number: '02', label: 'KNOWLEDGE', icon: Layers },
    { id: 'practice', number: '03', label: 'PRACTICE', icon: Cpu },
    { id: 'transmission', number: '04', label: 'TRANSMISSION', icon: Sparkles },
  ];

  return (
    <header className="border-b border-outline bg-surface-dim/95 backdrop-blur sticky top-0 z-50 px-4 lg:px-8 py-2.5">
      <div className="max-w-workbench mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Left: Brand Identity & Fixture Context */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-cadmium-amber/10 border border-cadmium-amber/40 flex items-center justify-center text-cadmium-amber font-mono font-bold text-sm shadow-[0_0_12px_rgba(230,126,34,0.15)]">
              अ
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold tracking-widest text-on-surface uppercase">
                  ANVESHAN
                </span>
                <span className="text-outline text-xs">//</span>
                <span className="font-mono text-[10px] tracking-wider text-cadmium-amber uppercase bg-cadmium-amber/10 px-1.5 py-0.5 rounded border border-cadmium-amber/20">
                  TRANSMISSION INSTRUMENT
                </span>
              </div>
              <div className="text-[11px] font-sans text-on-surface-variant flex items-center gap-1.5 mt-0.5">
                <span className="text-caliper-cyan font-mono text-[10px]">CASE-001:</span>
                <span className="font-medium text-on-surface">Optical Dial Micrometer Zeroing</span>
              </div>
            </div>
          </div>

          <div className="hidden xl:flex items-center gap-2 ml-3 pl-3 border-l border-outline">
            <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container text-cadmium-amber border border-cadmium-amber/30 text-[10px] font-mono font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-cadmium-amber animate-pulse" />
              DETERMINISTIC REPLAY MODE
            </span>
          </div>
        </div>

        {/* Center: 4-Stage Lifecycle Stepper */}
        <nav aria-label="Lifecycle Stepper" className="flex items-center bg-surface-container-lowest p-1 rounded border border-outline">
          {stages.map((stage, idx) => {
            const isActive = activeStage === stage.id;
            const isCompleted = stage.id !== 'transmission';

            return (
              <React.Fragment key={stage.id}>
                <button
                  onClick={() => onSelectStage(stage.id)}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded text-[11px] font-mono transition-all duration-150 ${
                    isActive
                      ? 'bg-cadmium-amber text-surface-container-lowest font-bold shadow-[0_0_12px_rgba(230,126,34,0.3)]'
                      : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
                  }`}
                >
                  <span className={isActive ? 'text-surface-container-lowest' : 'text-on-surface-variant'}>
                    {stage.number}.
                  </span>
                  <span>{stage.label}</span>
                  {isCompleted && !isActive && (
                    <CheckCircle2 className="w-3 h-3 text-transmission-emerald ml-0.5" />
                  )}
                  {isActive && (
                    <span className="w-1.5 h-1.5 rounded-full bg-surface-container-lowest animate-ping ml-0.5" />
                  )}
                </button>
                {idx < stages.length - 1 && (
                  <span className="text-outline text-xs px-1 select-none">→</span>
                )}
              </React.Fragment>
            );
          })}
        </nav>

        {/* Right: Telemetry & Provenance Stamp */}
        <div className="hidden lg:flex items-center gap-3">
          <div className="text-right text-[10px] font-mono leading-tight">
            <div className="text-on-surface-variant flex items-center gap-1 justify-end">
              <Lock className="w-2.5 h-2.5 text-transmission-emerald" />
              <span>SYNC: LOCKED (0.4ms)</span>
            </div>
            <div className="text-on-surface font-semibold flex items-center gap-1 justify-end mt-0.5">
              <Fingerprint className="w-2.5 h-2.5 text-caliper-cyan" />
              <span className="text-caliper-cyan">ISO 3611 VERIFIED</span>
            </div>
          </div>
          <div className="w-px h-6 bg-outline" />
          <div className="px-2 py-1 rounded bg-surface-container border border-outline text-[11px] font-mono text-on-surface flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-transmission-emerald" />
            <span>8-CONTRACT SEAM</span>
          </div>

          {onOpenStitchDesign && (
            <button
              onClick={onOpenStitchDesign}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container hover:bg-surface-container-high border border-outline hover:border-cadmium-amber text-[11px] font-mono text-on-surface transition-colors shadow-sm"
              title="View Google Stitch Generative Canvas Artifact"
            >
              <Sparkles className="w-3 h-3 text-cadmium-amber" />
              <span>STITCH CANVAS</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
