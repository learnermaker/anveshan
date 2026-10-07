import React from 'react';
import { Compass, Cpu, Layers, Award, ChevronDown, Settings, Sparkles, Lock, Check, HelpCircle, KeyRound } from 'lucide-react';
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
  /** Show the runtime (mode) chip: local development or ?debug=1. Hidden on the public demo. */
  showRuntime?: boolean;
  /** Per-step state for the stepper: progress hints and whether a step is ready yet. */
  steps?: Partial<Record<AppView, StepState>>;
  onOpenGuide?: () => void;
  onOpenKey?: () => void;
  hasUserKey?: boolean;
}

export interface StepState {
  status: 'done' | 'todo' | 'locked';
  /** short progress text shown under the label, e.g. "1/2 attempts" */
  hint?: string;
  /** tooltip explaining what is needed */
  title?: string;
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
  showRuntime = false,
  steps = {},
  onOpenGuide,
  onOpenKey,
  hasUserKey = false,
}) => {
  const views: { id: AppView; label: string; number: string; icon: typeof Compass }[] = [
    { id: 'discovery', number: '', label: 'Skills', icon: Layers },
    { id: 'source', number: '1', label: 'Learn', icon: Compass },
    { id: 'practice', number: '2', label: 'Practise', icon: Cpu },
    { id: 'transmission', number: '3', label: 'Results', icon: Award },
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
              <span className="text-outline text-xs hidden sm:inline">//</span>
              <span className="hidden sm:inline font-mono text-[10px] tracking-wider text-cadmium-amber uppercase bg-cadmium-amber/10 px-1.5 py-0.5 rounded border border-cadmium-amber/20 whitespace-nowrap">
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
          {(showRuntime || IS_MOCK) && (
            <button
              onClick={onOpenSettings}
              className={`ml-auto md:ml-2 flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono font-medium border transition-colors ${
                IS_MOCK ? 'text-divergence-crimson border-divergence-crimson/40 bg-divergence-crimson/10' : 'text-cadmium-amber border-cadmium-amber/30 hover:bg-cadmium-amber/15'
              }`}
              title="Runtime panel (developer)"
              aria-label={`Runtime panel, mode ${modeLabel}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${IS_MOCK ? 'bg-divergence-crimson' : 'bg-cadmium-amber'}`} />
              <span>MODE: {modeLabel}</span>
              <Settings className="w-3 h-3 opacity-60" aria-hidden="true" />
            </button>
          )}
        </div>

        <nav aria-label="Steps" className="flex items-center bg-surface-dim p-1 rounded-lg border border-outline overflow-x-auto max-w-full">
          {views.map((v, idx) => {
            const isActive = currentView === v.id;
            const st = steps[v.id];
            const locked = st?.status === 'locked' && !isActive;
            return (
              <React.Fragment key={v.id}>
                <button
                  onClick={() => onSelectView(v.id)}
                  aria-current={isActive ? 'step' : undefined}
                  title={st?.title}
                  className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-md text-xs transition-all duration-150 whitespace-nowrap ${
                    isActive
                      ? 'bg-cadmium-amber text-surface-dim font-bold'
                      : locked
                        ? 'text-on-surface-variant/70 hover:text-on-surface hover:bg-surface-container'
                        : 'text-on-surface hover:bg-surface-container'
                  }`}
                >
                  {st?.status === 'done' && !isActive ? (
                    <Check className="w-3.5 h-3.5 text-transmission-emerald" aria-label="done" />
                  ) : locked ? (
                    <Lock className="w-3 h-3" aria-label="not ready yet" />
                  ) : v.number ? (
                    <span className="font-mono">{v.number}.</span>
                  ) : null}
                  <span className="font-semibold">{v.label}</span>
                  {st?.hint && <span className={`font-mono text-[11px] ${isActive ? 'text-surface-dim/80' : 'text-on-surface-variant'}`}>· {st.hint}</span>}
                </button>
                {idx < views.length - 1 && <span className="text-outline text-xs px-0.5 select-none" aria-hidden="true">→</span>}
              </React.Fragment>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          {onOpenKey && (
            <button
              onClick={onOpenKey}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs transition-colors ${
                hasUserKey ? 'border-transmission-emerald/50 text-transmission-emerald' : 'border-outline text-on-surface hover:border-cadmium-amber'
              }`}
              title={hasUserKey ? 'AI calls use your own Gemini key' : 'Optional: use your own Gemini API key'}
            >
              <KeyRound className="w-3.5 h-3.5" aria-hidden="true" />
              <span>{hasUserKey ? 'Your key' : 'AI key'}</span>
            </button>
          )}
          {onOpenGuide && (
            <button
              onClick={onOpenGuide}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-outline hover:border-cadmium-amber text-xs text-on-surface transition-colors"
            >
              <HelpCircle className="w-3.5 h-3.5 text-cadmium-amber" aria-hidden="true" />
              <span>How it works</span>
            </button>
          )}
          {showRuntime && onOpenStitchDesign && (
            <button
              onClick={onOpenStitchDesign}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container border border-outline hover:border-cadmium-amber text-[11px] font-mono text-on-surface transition-colors"
              title="Design reference (developer)"
            >
              <Sparkles className="w-3 h-3 text-cadmium-amber" aria-hidden="true" />
              <span>Design ref</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
