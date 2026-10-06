import React from 'react';
import { Compass, Cpu, Layers, Award, ChevronDown, Settings, Sparkles, Lock } from 'lucide-react';
import type { AppView } from '../types/workspace';
import type { RequestedMode } from '../api/runtime';
import { IS_MOCK } from '../api/runtime';

export interface CaseOption {
  value: string;
  label: string;
  group: string;
}

interface HeaderProps {
  currentView: AppView;
  onSelectView: (view: AppView) => void;
  caseOptions: CaseOption[];
  selectedCase: string;
  onSelectCase: (value: string) => void;
  requestedMode: RequestedMode;
  /** short label for the active case's source kind, e.g. LIVE CASE or SYNTHETIC REPLAY */
  caseKindLabel: string;
  onOpenSettings: () => void;
  onOpenStitchDesign?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentView,
  onSelectView,
  caseOptions,
  selectedCase,
  onSelectCase,
  requestedMode,
  caseKindLabel,
  onOpenSettings,
  onOpenStitchDesign,
}) => {
  const views: { id: AppView; label: string; number: string; icon: typeof Compass }[] = [
    { id: 'discovery', number: '00', label: 'PORTFOLIO', icon: Layers },
    { id: 'source', number: '01', label: 'SOURCE', icon: Compass },
    { id: 'practice', number: '02', label: 'PRACTICE', icon: Cpu },
    { id: 'transmission', number: '03', label: 'TRANSMISSION', icon: Award },
  ];
  const groups = Array.from(new Set(caseOptions.map((o) => o.group)));
  const modeLabel = IS_MOCK ? 'MOCK DATA' : requestedMode === 'default' ? 'SERVER DEFAULT' : requestedMode.toUpperCase();

  return (
    <header className="border-b border-outline bg-surface-dim/95 backdrop-blur sticky top-0 z-40 px-3 lg:px-8 py-2.5">
      <div className="max-w-workbench mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-3 w-full md:w-auto">
          <div
            onClick={() => onSelectView('discovery')}
            className="w-8 h-8 rounded bg-cadmium-amber/15 border border-cadmium-amber/40 flex items-center justify-center text-cadmium-amber font-mono font-bold text-sm cursor-pointer hover:bg-cadmium-amber/25 transition-colors shrink-0"
            title="Return to portfolio"
          >
            अ
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <button onClick={() => onSelectView('discovery')} className="font-mono text-xs font-bold tracking-widest text-on-surface uppercase hover:text-cadmium-amber transition-colors">
                ANVESHAN
              </button>
              <span className="text-outline text-xs">//</span>
              <span className="font-mono text-[10px] tracking-wider text-cadmium-amber uppercase bg-cadmium-amber/10 px-1.5 py-0.5 rounded border border-cadmium-amber/20 whitespace-nowrap">
                {caseKindLabel}
              </span>
            </div>
            <div className="relative mt-0.5 flex items-center gap-1.5">
              <select
                value={selectedCase}
                onChange={(e) => onSelectCase(e.target.value)}
                className="bg-transparent text-xs font-mono font-medium text-caliper-cyan hover:text-white cursor-pointer focus:outline-none appearance-none pr-4 truncate max-w-[240px] sm:max-w-xs"
                aria-label="Select case"
              >
                {groups.map((g) => (
                  <optgroup key={g} label={g} className="bg-surface-container text-on-surface">
                    {caseOptions
                      .filter((o) => o.group === g)
                      .map((o) => (
                        <option key={o.value} value={o.value} className="bg-surface-container text-on-surface">
                          {o.label}
                        </option>
                      ))}
                  </optgroup>
                ))}
              </select>
              <ChevronDown className="w-3 h-3 text-caliper-cyan pointer-events-none -ml-4" />
            </div>
          </div>
          <button
            onClick={onOpenSettings}
            className={`ml-auto md:ml-2 flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono font-medium border transition-colors ${
              IS_MOCK ? 'text-divergence-crimson border-divergence-crimson/40 bg-divergence-crimson/10' : 'text-cadmium-amber border-cadmium-amber/30 hover:bg-cadmium-amber/15'
            }`}
            title="Runtime panel"
          >
            <span className={`w-1.5 h-1.5 rounded-full ${IS_MOCK ? 'bg-divergence-crimson' : 'bg-cadmium-amber'}`} />
            <span>MODE: {modeLabel}</span>
            <Settings className="w-3 h-3 opacity-60" />
          </button>
        </div>

        <nav aria-label="Lifecycle Stepper" className="flex items-center bg-surface-dim p-1 rounded-lg border border-outline overflow-x-auto max-w-full">
          {views.map((v, idx) => {
            const isActive = currentView === v.id;
            return (
              <React.Fragment key={v.id}>
                <button
                  onClick={() => onSelectView(v.id)}
                  className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-md text-[11px] font-mono transition-all duration-150 whitespace-nowrap ${
                    isActive ? 'bg-cadmium-amber text-surface-dim font-bold' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
                  }`}
                >
                  <span>{v.number}.</span>
                  <span>{v.label}</span>
                </button>
                {idx < views.length - 1 && <span className="text-outline text-xs px-0.5 select-none">→</span>}
              </React.Fragment>
            );
          })}
        </nav>

        <div className="hidden lg:flex items-center gap-3">
          <div className="text-right text-[10px] font-mono leading-tight text-on-surface-variant flex items-center gap-1">
            <Lock className="w-2.5 h-2.5 text-transmission-emerald" />
            <span>SEAM: 8 CONTRACTS · SCORES DETERMINISTIC</span>
          </div>
          {onOpenStitchDesign && (
            <button
              onClick={onOpenStitchDesign}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container border border-outline hover:border-cadmium-amber text-[11px] font-mono text-on-surface transition-colors"
              title="View Google Stitch design reference"
            >
              <Sparkles className="w-3 h-3 text-cadmium-amber" />
              <span>STITCH</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
