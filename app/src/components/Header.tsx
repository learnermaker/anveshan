import React from 'react';
import { Check, ChevronDown, HelpCircle, KeyRound, Library, Lock, Settings, Share2, Sparkles, Users } from 'lucide-react';
import type { AppView } from '../types/workspace';
import type { RequestedMode } from '../api/runtime';
import { IS_MOCK } from '../api/runtime';
import { DEBUG } from '../api/debug';

export interface CaseOption {
  value: string;
  label: string;
  group: string;
}

export interface StepState {
  status: 'done' | 'todo' | 'locked';
  /** short progress text shown under the label, e.g. "1/2 attempts" */
  hint?: string;
  /** tooltip explaining what is needed */
  title?: string;
}

interface HeaderProps {
  currentView: AppView;
  onSelectView: (view: AppView) => void;
  caseOptions: CaseOption[];
  selectedCase: string;
  onSelectCase: (value: string) => void;
  requestedMode: RequestedMode;
  /** short label for the active case's source kind */
  caseKindLabel: string;
  onOpenSettings: () => void;
  onOpenStitchDesign?: () => void;
  showRuntime?: boolean;
  steps?: Partial<Record<AppView, StepState>>;
  onOpenGuide?: () => void;
  onOpenKey?: () => void;
  hasUserKey?: boolean;
  /** count of skills the current visitor owns (shows badge on My skills) */
  ownedCount?: number;
  /** whether the Steward nav button should appear */
  stewardVisible?: boolean;
  /** title of the current skill, for the breadcrumb */
  skillTitle?: string | null;
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
  ownedCount = 0,
  stewardVisible = false,
  skillTitle = null,
}) => {
  const groups = Array.from(new Set(caseOptions.map((o) => o.group)));
  const modeLabel = IS_MOCK ? 'MOCK DATA' : requestedMode === 'default' ? 'SERVER DEFAULT' : requestedMode.toUpperCase();

  // Show breadcrumb + stepper when inside a skill (not the composer)
  const inSkill = ['source', 'practice', 'transmission'].includes(currentView);

  const stepViews: { id: AppView; label: string; number: string }[] = [
    { id: 'source', number: '1', label: 'Learn' },
    { id: 'practice', number: '2', label: 'Practise' },
    { id: 'transmission', number: '3', label: 'Results' },
  ];

  return (
    <header className="border-b border-outline bg-surface-dim/95 backdrop-blur sticky top-0 z-40 px-3 lg:px-8">
      {/* ── Primary row ── */}
      <div className="max-w-workbench mx-auto flex items-center justify-between gap-2 py-2.5 flex-wrap">
        {/* Left: wordmark + nav */}
        <div className="flex items-center gap-1 sm:gap-2 flex-wrap">
          <button
            onClick={() => onSelectView('discovery')}
            className="w-8 h-8 rounded bg-cadmium-amber/15 border border-cadmium-amber/40 flex items-center justify-center text-cadmium-amber font-mono font-bold text-sm hover:bg-cadmium-amber/25 transition-colors shrink-0"
            aria-label="Return to library"
          >
            अ
          </button>
          <button
            onClick={() => onSelectView('discovery')}
            className="font-mono text-xs font-bold tracking-widest text-on-surface uppercase hover:text-cadmium-amber transition-colors hidden sm:inline"
          >
            Anveshan
          </button>

          {/* Nav buttons */}
          <nav aria-label="Main navigation" className="flex items-center gap-0.5 sm:gap-1 ml-1">
            <button
              onClick={() => onSelectView('discovery')}
              aria-current={currentView === 'discovery' ? 'page' : undefined}
              className={`flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded text-xs transition-colors whitespace-nowrap ${
                currentView === 'discovery'
                  ? 'bg-cadmium-amber text-background font-bold'
                  : 'text-on-surface hover:bg-surface-container'
              }`}
            >
              <Library className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
              <span className="sm:inline">Library</span>
            </button>

            <button
              onClick={() => onSelectView('mine')}
              aria-current={currentView === 'mine' ? 'page' : undefined}
              className={`relative flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded text-xs transition-colors whitespace-nowrap ${
                currentView === 'mine'
                  ? 'bg-cadmium-amber text-background font-bold'
                  : 'text-on-surface hover:bg-surface-container'
              }`}
            >
              <Users className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
              <span>My skills</span>
              {ownedCount > 0 && (
                <span className="ml-0.5 px-1 py-0 rounded-full bg-cadmium-amber/80 text-background text-[9px] font-bold leading-none">
                  {ownedCount}
                </span>
              )}
            </button>

            {stewardVisible && (
              <button
                onClick={() => onSelectView('steward')}
                aria-current={currentView === 'steward' ? 'page' : undefined}
                className={`flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded text-xs transition-colors whitespace-nowrap ${
                  currentView === 'steward'
                    ? 'bg-cadmium-amber text-background font-bold'
                    : 'text-on-surface hover:bg-surface-container'
                }`}
              >
                <Share2 className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                <span>Steward</span>
              </button>
            )}
          </nav>

          {/* Case select: only when DEBUG */}
          {DEBUG && (
            <div className="relative flex items-center gap-1 ml-1">
              <select
                value={selectedCase}
                onChange={(e) => onSelectCase(e.target.value)}
                className="bg-transparent text-[10px] font-mono font-medium text-caliper-cyan hover:text-white cursor-pointer focus:outline-none appearance-none pr-4 truncate max-w-[180px]"
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
          )}
        </div>

        {/* Right: runtime chip, how it works, key, design ref */}
        <div className="flex items-center gap-1.5">
          {(showRuntime || IS_MOCK) && (
            <button
              onClick={onOpenSettings}
              className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono font-medium border transition-colors ${
                IS_MOCK
                  ? 'text-divergence-crimson border-divergence-crimson/40 bg-divergence-crimson/10'
                  : 'text-cadmium-amber border-cadmium-amber/30 hover:bg-cadmium-amber/15'
              }`}
              title="Runtime panel (developer)"
              aria-label={`Runtime panel, mode ${modeLabel}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${IS_MOCK ? 'bg-divergence-crimson' : 'bg-cadmium-amber'}`} />
              <span className="hidden sm:inline">MODE: {modeLabel}</span>
              <Settings className="w-3 h-3 opacity-60" aria-hidden="true" />
            </button>
          )}

          {onOpenKey && (
            <button
              onClick={onOpenKey}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs transition-colors ${
                hasUserKey
                  ? 'border-transmission-emerald/50 text-transmission-emerald'
                  : 'border-outline text-on-surface hover:border-cadmium-amber'
              }`}
              title={hasUserKey ? 'AI calls use your own Gemini key' : 'Optional: use your own Gemini API key'}
            >
              <KeyRound className="w-3.5 h-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">{hasUserKey ? 'Your key' : 'AI key'}</span>
            </button>
          )}

          {onOpenGuide && (
            <button
              onClick={onOpenGuide}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-outline hover:border-cadmium-amber text-xs text-on-surface transition-colors"
            >
              <HelpCircle className="w-3.5 h-3.5 text-cadmium-amber" aria-hidden="true" />
              <span className="hidden sm:inline">How it works</span>
            </button>
          )}

          {showRuntime && onOpenStitchDesign && (
            <button
              onClick={onOpenStitchDesign}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container border border-outline hover:border-cadmium-amber text-[11px] font-mono text-on-surface transition-colors"
              title="Design reference (developer)"
            >
              <Sparkles className="w-3 h-3 text-cadmium-amber" aria-hidden="true" />
              <span className="hidden sm:inline">Design ref</span>
            </button>
          )}
        </div>
      </div>

      {/* ── Second row: breadcrumb + stepper (only when inside a skill, not composer) ── */}
      {inSkill && (
        <div className="max-w-workbench mx-auto flex flex-wrap items-center justify-between gap-2 pb-2">
          {/* Breadcrumb */}
          <div className="flex items-center gap-1.5 text-xs text-on-surface-variant min-w-0">
            <button
              onClick={() => onSelectView('discovery')}
              className="hover:text-cadmium-amber transition-colors shrink-0"
            >
              Library
            </button>
            {skillTitle && (
              <>
                <span className="text-outline" aria-hidden="true">›</span>
                <span data-plain-exempt className="truncate max-w-[160px] sm:max-w-xs text-on-surface">
                  {skillTitle}
                </span>
              </>
            )}
          </div>

          {/* Stepper */}
          <nav aria-label="Steps" className="flex items-center gap-0.5">
            {stepViews.map((v, idx) => {
              const isActive = currentView === v.id;
              const st = steps[v.id];
              const locked = st?.status === 'locked' && !isActive;
              return (
                <React.Fragment key={v.id}>
                  <button
                    onClick={() => onSelectView(v.id)}
                    aria-current={isActive ? 'step' : undefined}
                    title={st?.title}
                    className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-all whitespace-nowrap ${
                      isActive
                        ? 'bg-cadmium-amber text-surface-dim font-bold'
                        : locked
                          ? 'text-on-surface-variant/70 hover:text-on-surface'
                          : 'text-on-surface hover:bg-surface-container'
                    }`}
                  >
                    {st?.status === 'done' && !isActive ? (
                      <Check className="w-3 h-3 text-transmission-emerald" aria-label="done" />
                    ) : locked ? (
                      <Lock className="w-3 h-3" aria-label="not ready yet" />
                    ) : (
                      <span className="font-mono">{v.number}.</span>
                    )}
                    <span>{v.label}</span>
                    {st?.hint && (
                      <span className={`font-mono text-[10px] ${isActive ? 'text-surface-dim/80' : 'text-on-surface-variant'}`}>
                        · {st.hint}
                      </span>
                    )}
                  </button>
                  {idx < stepViews.length - 1 && (
                    <span className="text-outline text-xs px-0.5 select-none" aria-hidden="true">→</span>
                  )}
                </React.Fragment>
              );
            })}
          </nav>
        </div>
      )}
    </header>
  );
};
