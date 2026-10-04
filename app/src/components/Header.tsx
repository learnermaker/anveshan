import React from 'react';
import {
  Compass,
  CheckCircle2,
  Lock,
  Layers,
  Sparkles,
  Cpu,
  Fingerprint,
  ChevronDown,
  Settings,
  ShieldCheck,
  Award,
} from 'lucide-react';
import { ALL_CAPABILITY_IDS, CAPABILITY_CASES } from '../data/cases/registry';
import type { AppView, CapabilityCase } from '../types/workspace';
import type { AnalysisMode } from '../types/gemini';

interface HeaderProps {
  currentView: AppView;
  onSelectView: (view: AppView) => void;
  currentCase: CapabilityCase;
  onSelectCase: (caseId: string) => void;
  analysisMode: AnalysisMode;
  onOpenSettings: () => void;
  onOpenStitchDesign?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentView,
  onSelectView,
  currentCase,
  onSelectCase,
  analysisMode,
  onOpenSettings,
  onOpenStitchDesign,
}) => {
  const views: { id: AppView; label: string; number: string; icon: typeof Compass }[] = [
    { id: 'discovery', number: '00', label: 'PORTFOLIO', icon: Layers },
    { id: 'source', number: '01', label: 'SOURCE', icon: Compass },
    { id: 'practice', number: '02', label: 'PRACTICE', icon: Cpu },
    { id: 'transmission', number: '03', label: 'TRANSMISSION', icon: Award },
  ];

  return (
    <header className="border-b border-outline bg-surface-dim/95 backdrop-blur sticky top-0 z-40 px-4 lg:px-8 py-2.5">
      <div className="max-w-workbench mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Left: Brand Identity & Active Case Switcher */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2.5">
            <div
              onClick={() => onSelectView('discovery')}
              className="w-8 h-8 rounded bg-cadmium-amber/15 border border-cadmium-amber/40 flex items-center justify-center text-cadmium-amber font-mono font-bold text-sm shadow-[0_0_12px_rgba(230,126,34,0.15)] cursor-pointer hover:bg-cadmium-amber/25 transition-colors"
              title="Return to Capability Portfolio"
            >
              अ
            </div>
            <div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onSelectView('discovery')}
                  className="font-mono text-xs font-bold tracking-widest text-on-surface uppercase hover:text-cadmium-amber transition-colors"
                >
                  ANVESHAN
                </button>
                <span className="text-outline text-xs">//</span>
                <span className="font-mono text-[10px] tracking-wider text-cadmium-amber uppercase bg-cadmium-amber/10 px-1.5 py-0.5 rounded border border-cadmium-amber/20">
                  TRANSMISSION INSTRUMENT
                </span>
              </div>

              {/* Dynamic Capability Dropdown */}
              <div className="relative mt-0.5 flex items-center gap-1.5">
                <select
                  value={currentCase.id}
                  onChange={(e) => onSelectCase(e.target.value)}
                  className="bg-transparent text-xs font-mono font-medium text-caliper-cyan hover:text-white cursor-pointer focus:outline-none appearance-none pr-4 truncate max-w-[200px] sm:max-w-xs"
                >
                  {ALL_CAPABILITY_IDS.map((id) => (
                    <option key={id} value={id} className="bg-surface-elevated text-on-surface">
                      {CAPABILITY_CASES[id].title} ({CAPABILITY_CASES[id].archetype})
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3 h-3 text-caliper-cyan pointer-events-none -ml-4" />
              </div>
            </div>
          </div>

          {/* Mode Badge with clickable Settings */}
          <div className="hidden xl:flex items-center gap-2 ml-2 pl-3 border-l border-outline">
            <button
              onClick={onOpenSettings}
              className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono font-medium transition-colors ${
                analysisMode === 'LIVE'
                  ? 'bg-caliper-cyan/15 text-caliper-cyan border border-caliper-cyan/40 hover:bg-caliper-cyan/25'
                  : 'bg-surface-elevated text-cadmium-amber border border-cadmium-amber/30 hover:bg-cadmium-amber/15'
              }`}
              title="Configure Gemini Model Gateway"
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  analysisMode === 'LIVE' ? 'bg-caliper-cyan animate-ping' : 'bg-cadmium-amber'
                }`}
              />
              <span>MODE: {analysisMode === 'LIVE' ? 'GEMINI LIVE API' : 'REPLAY FIXTURE'}</span>
              <Settings className="w-3 h-3 opacity-60 ml-0.5" />
            </button>
          </div>
        </div>

        {/* Center: Stage Navigation Stepper */}
        <nav aria-label="Lifecycle Stepper" className="flex items-center bg-surface-dim p-1 rounded-lg border border-outline">
          {views.map((v, idx) => {
            const isActive = currentView === v.id;

            return (
              <React.Fragment key={v.id}>
                <button
                  onClick={() => onSelectView(v.id)}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-[11px] font-mono transition-all duration-150 ${
                    isActive
                      ? 'bg-cadmium-amber text-surface-dim font-bold shadow-[0_0_12px_rgba(230,126,34,0.3)]'
                      : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-elevated'
                  }`}
                >
                  <span className={isActive ? 'text-surface-dim' : 'text-on-surface-variant'}>
                    {v.number}.
                  </span>
                  <span>{v.label}</span>
                </button>
                {idx < views.length - 1 && (
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
              <span>SEAM: 8 CONTRACTS</span>
            </div>
            <div className="text-on-surface font-semibold flex items-center gap-1 justify-end mt-0.5">
              <ShieldCheck className="w-2.5 h-2.5 text-caliper-cyan" />
              <span className="text-caliper-cyan font-mono text-[10px]">
                REPLAY VERIFIED // HONEST SPEC
              </span>
            </div>
          </div>

          <div className="w-px h-6 bg-outline" />

          {onOpenStitchDesign && (
            <button
              onClick={onOpenStitchDesign}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-elevated hover:bg-surface-elevated/80 border border-outline hover:border-cadmium-amber text-[11px] font-mono text-on-surface transition-colors shadow-sm"
              title="View Google Stitch Generative Canvas Artifact"
            >
              <Sparkles className="w-3 h-3 text-cadmium-amber" />
              <span>STITCH CANVAS</span>
            </button>
          )}

          <button
            onClick={onOpenSettings}
            className="p-1.5 rounded bg-surface-elevated hover:bg-surface-bright border border-outline text-on-surface-variant hover:text-on-surface transition-colors"
            title="Gateway Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
