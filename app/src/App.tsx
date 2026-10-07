import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Header, type CaseOption } from './components/Header';
import { DiscoveryView, type CaseKey } from './components/DiscoveryView';
import { ComposerWizard } from './components/composer/ComposerWizard';
import { SourceAnalysisView } from './components/SourceAnalysisView';
import { WorkspaceCompiler } from './workspaces/WorkspaceCompiler';
import { TransmissionCompleteView } from './components/TransmissionCompleteView';
import { FirstDivergenceModal } from './components/FirstDivergenceModal';
import { MicroPracticeRetryModal } from './components/MicroPracticeRetryModal';
import { LineageDrawer } from './components/LineageDrawer';
import { StitchModal } from './components/StitchModal';
import { SettingsModal } from './components/SettingsModal';
import { LifecycleInspectorModal } from './components/LifecycleInspectorModal';
import { HeroSourceView } from './hero/HeroSourceView';
import { HeroPracticeView } from './hero/HeroPracticeView';
import { HeroTransmissionView } from './hero/HeroTransmissionView';
import type { HeroSession } from './hero/session';
import { ErrorNote, Spinner } from './hero/ui';
import { GuideModal } from './components/HowItWorks';
import { ApiKeyModal } from './components/ApiKeyModal';
import { getUserKey, subscribeUserKey } from './api/userKey';
import { getStewardToken, subscribeStewardToken } from './api/steward';
import type { StepState } from './components/Header';
import { MySkillsView } from './components/creator/MySkillsView';
import { CreatorPanel } from './components/creator/CreatorPanel';
import { StewardConsole } from './components/steward/StewardConsole';
import { EvidencePage } from './components/EvidencePage';

import { CAPABILITY_CASES, SHOWCASE_CASE_IDS, getCapabilityCase } from './data/cases/registry';
import { api } from './api/client';
import { IS_MOCK, getRequestedMode, subscribeMode, type RequestedMode } from './api/runtime';
import type { CaseSummary, CaseView, HealthResponse } from './api/types';
import type { AppView } from './types/workspace';
import type { LifecycleStage } from './components/LifecycleInspectorModal';

const DEFAULT_KEY: CaseKey = { kind: 'hero', id: 'kolam' };

function readUrl(): { view: AppView; key: CaseKey } {
  if (typeof window === 'undefined') return { view: 'discovery', key: DEFAULT_KEY };
  const p = new URLSearchParams(window.location.search);
  const v = p.get('view') as AppView;
  const view: AppView = v && ['discovery', 'source', 'practice', 'transmission', 'composer', 'mine', 'steward', 'evidence'].includes(v) ? v : 'discovery';
  const c = p.get('case');
  const key: CaseKey = !c ? DEFAULT_KEY : SHOWCASE_CASE_IDS.includes(c) ? { kind: 'showcase', id: c } : { kind: 'hero', id: c };
  return { view, key };
}

const keyStr = (k: CaseKey) => k.kind === 'composer' ? 'composer:wizard' : `${k.kind}:${k.id}`;

export function App() {
  const initial = readUrl();
  const [currentView, setCurrentView] = useState<AppView>(initial.view);
  const [selected, setSelected] = useState<CaseKey>(initial.key);
  const [requestedMode, setMode] = useState<RequestedMode>(getRequestedMode());
  useEffect(() => subscribeMode(setMode), []);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);
  const debug = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('debug') === '1';
  const showRuntime = debug || health?.mode_override === true;
  const [guideOpen, setGuideOpen] = useState(false);
  const [keyOpen, setKeyOpen] = useState(false);
  const [hasKey, setHasKey] = useState<boolean>(Boolean(getUserKey()));
  useEffect(() => subscribeUserKey((k) => setHasKey(Boolean(k))), []);
  useEffect(() => {
    const open = () => setKeyOpen(true);
    window.addEventListener('anveshan:open-key-dialog', open);
    return () => window.removeEventListener('anveshan:open-key-dialog', open);
  }, []);
  useEffect(() => {
    const goEvidence = () => setCurrentView('evidence');
    window.addEventListener('anveshan:go-evidence', goEvidence);
    return () => window.removeEventListener('anveshan:go-evidence', goEvidence);
  }, []);

  // Steward token (for nav visibility)
  const [stewardToken, setStewardTokenState] = useState<string | null>(getStewardToken());
  useEffect(() => subscribeStewardToken(setStewardTokenState), []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    params.set('view', currentView);
    if (currentView === 'mine' || currentView === 'steward') {
      params.delete('case');
    } else if (selected.kind !== 'composer') {
      params.set('case', selected.id);
    }
    window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
  }, [currentView, selected]);

  // A new screen starts at the top (otherwise the header and title can be scrolled out of view).
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [currentView, selected]);

  // ---------------- hero cases (service) ----------------
  const [heroCases, setHeroCases] = useState<CaseSummary[] | null>(null);
  const [heroError, setHeroError] = useState<unknown>(null);
  const [heroLoading, setHeroLoading] = useState(false);
  const loadCases = useCallback(async () => {
    setHeroLoading(true);
    setHeroError(null);
    try {
      setHeroCases(await api.listCases());
    } catch (e) {
      setHeroError(e);
    } finally {
      setHeroLoading(false);
    }
  }, []);
  useEffect(() => {
    void loadCases();
  }, [loadCases]);

  const [caseView, setCaseView] = useState<CaseView | null>(null);
  const [caseError, setCaseError] = useState<unknown>(null);
  const [caseLoading, setCaseLoading] = useState(false);
  const loadCase = useCallback(async (id: string) => {
    setCaseLoading(true);
    setCaseError(null);
    try {
      setCaseView(await api.getCase(id));
    } catch (e) {
      setCaseError(e);
      setCaseView(null);
    } finally {
      setCaseLoading(false);
    }
  }, []);
  useEffect(() => {
    if (selected.kind === 'hero') void loadCase(selected.id);
  }, [selected, loadCase, requestedMode]);

  const [sessions, setSessions] = useState<Record<string, HeroSession | null>>({});
  const heroSession = selected.kind === 'hero' ? sessions[selected.id] ?? null : null;
  const setHeroSession = (s: HeroSession | null) => {
    if (selected.kind === 'hero') setSessions((prev) => ({ ...prev, [selected.id]: s }));
  };
  // ---------------- showcase (SYNTHETIC replay) ----------------
  const capCase = getCapabilityCase(selected.kind === 'showcase' ? selected.id : 'micrometer');
  const [currentTime, setCurrentTime] = useState<number>(19.2);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isDivergenceModalOpen, setIsDivergenceModalOpen] = useState(false);
  const [isMicroPracticeOpen, setIsMicroPracticeOpen] = useState(false);
  const [isLineageOpen, setIsLineageOpen] = useState(false);
  const [isStitchOpen, setIsStitchOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [modalStage, setModalStage] = useState<LifecycleStage | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const lastTimestampRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isPlaying) {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      lastTimestampRef.current = null;
      return;
    }
    const step = (now: number) => {
      if (lastTimestampRef.current !== null) {
        const delta = (now - lastTimestampRef.current) / 1000;
        setCurrentTime((prev) => {
          const next = prev + delta;
          if (next >= 35.0) {
            setIsPlaying(false);
            return 35.0;
          }
          return next;
        });
      }
      lastTimestampRef.current = now;
      animationFrameRef.current = requestAnimationFrame(step);
    };
    animationFrameRef.current = requestAnimationFrame(step);
    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [isPlaying]);

  const select = (key: CaseKey, view: AppView = 'source') => {
    setSelected(key);
    setCurrentView(key.kind === 'composer' ? 'composer' : view);
    setCurrentTime(19.2);
    setIsPlaying(false);
    if (key.kind === 'hero' && heroCases && !heroCases.some((c) => c.case_id === key.id)) void loadCases();
  };

  // Derived header props
  const ownedCount = (heroCases ?? []).filter((c) => c.access?.owner).length;
  const stewardVisible = Boolean(stewardToken) || health?.steward_open === true;
  const skillTitle: string | null =
    selected.kind === 'hero' && caseView ? caseView.title :
    selected.kind === 'showcase' ? (capCase.title ?? null) :
    null;

  const caseOptions: CaseOption[] = [
    // Synthetic case packs from the API are listed once, below, as the replay showcase.
    ...(heroCases ?? []).filter((c) => c.hero || c.composed || c.derived_from)
      .map((c) => ({ value: `hero:${c.case_id}`, label: c.title, group: c.hero ? 'Live hero cases' : c.composed ? 'Your composed skills' : 'Your uploads' })),
    ...(selected.kind === 'hero' && !(heroCases ?? []).some((c) => c.case_id === selected.id) ? [{ value: keyStr(selected), label: selected.id, group: 'Live hero cases' }] : []),
    ...SHOWCASE_CASE_IDS.map((id) => ({ value: `showcase:${id}`, label: `${CAPABILITY_CASES[id]?.title ?? id} (synthetic)`, group: 'Synthetic replay showcase' })),
  ];

  const selectedId = selected.kind !== 'composer' ? selected.id : '';

  // Stepper state for live cases: what is done, what is next, and what is not ready yet.
  const steps: Partial<Record<AppView, StepState>> = {};
  if (selected.kind === 'hero') {
    const n = heroSession?.attempts.length ?? 0;
    const done = Boolean(heroSession?.result);
    steps.source = { status: heroSession ? 'done' : 'todo' };
    steps.practice = {
      status: n >= 2 ? 'done' : 'todo',
      hint: heroSession ? `${Math.min(n, 2)}/2 attempts` : undefined,
      title: 'Do the task once (baseline), read the feedback, then retry once.',
    };
    steps.transmission = done
      ? { status: 'done' }
      : n >= 2
        ? { status: 'todo', hint: 'ready', title: 'Both attempts are done: open Results to see what changed.' }
        : { status: 'locked', title: 'Available after a baseline and one retry in Practise.' };
  }

  const heroBody = (render: (v: CaseView) => React.ReactNode) => {
    if (caseLoading && !caseView) return <Spinner label={`Loading ${selectedId}…`} />;
    if (caseError) return <ErrorNote error={caseError} />;
    if (!caseView || caseView.case_id !== selectedId) return <Spinner label={`Loading ${selectedId}…`} />;
    return render(caseView);
  };

  return (
    <div className="min-h-screen bg-background text-on-surface flex flex-col noise-overlay selection:bg-cadmium-amber/30 selection:text-white">
      <Header
        currentView={currentView}
        onSelectView={setCurrentView}
        caseOptions={caseOptions}
        selectedCase={keyStr(selected)}
        onSelectCase={(v) => {
          const [kind, ...rest] = v.split(':');
          if (kind === 'composer') {
            select({ kind: 'composer' });
          } else {
            select({ kind: kind as CaseKey['kind'], id: rest.join(':') }, currentView === 'discovery' ? 'source' : currentView);
          }
        }}
        requestedMode={requestedMode}
        caseKindLabel={selected.kind === 'hero' ? (IS_MOCK ? 'LIVE CASE · MOCK DATA' : 'LIVE CASE') : selected.kind === 'composer' ? 'COMPOSER' : 'SYNTHETIC REPLAY'}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenStitchDesign={() => setIsStitchOpen(true)}
        showRuntime={showRuntime}
        steps={steps}
        onOpenGuide={() => setGuideOpen(true)}
        onOpenKey={() => setKeyOpen(true)}
        hasUserKey={hasKey}
        ownedCount={ownedCount}
        stewardVisible={stewardVisible}
        skillTitle={skillTitle}
      />

      <main className="flex-1 max-w-workbench w-full mx-auto p-3 sm:p-4 lg:p-6 flex flex-col gap-6">
        {currentView === 'discovery' && (
          <DiscoveryView
            heroCases={heroCases}
            heroError={heroError}
            heroLoading={heroLoading}
            onRefreshHero={loadCases}
            onSelect={(k) => select(k)}
            selected={selected}
            onOpenGuide={() => setGuideOpen(true)}
            onOpenMine={() => setCurrentView('mine')}
          />
        )}

        {(currentView === 'composer' || selected.kind === 'composer') && (
          <div className="flex flex-col gap-4 w-full animate-fade-in">
            <h1 className="font-serif text-2xl">Share a skill you know</h1>
            <p className="text-sm text-on-surface-variant">Upload a photo, video or audio of something you know how to do. Anveshan proposes a practice task; you check it before anyone else sees it.</p>
            <ComposerWizard
              onDone={(view) => {
                void loadCases();
                setSelected({ kind: 'hero', id: view.case_id });
                setCurrentView('source');
                void loadCase(view.case_id);
              }}
              onCancel={() => { setSelected(DEFAULT_KEY); setCurrentView('discovery'); }}
            />
          </div>
        )}

        {selected.kind === 'hero' && currentView === 'source' &&
          heroBody((v) => (
            <HeroSourceView
              view={v}
              onViewChange={(nv) => {
                setCaseView(nv);
                void loadCases();
              }}
              onReload={() => loadCase(selected.id)}
              onEnterPractice={() => setCurrentView('practice')}
              onBack={() => setCurrentView('discovery')}
              ownerSlot={v.access?.owner ? (
                <CreatorPanel
                  view={v}
                  onViewChange={(nv) => { setCaseView(nv); void loadCases(); }}
                  onPractise={() => setCurrentView('practice')}
                />
              ) : null}
            />
          ))}
        {selected.kind === 'hero' && currentView === 'practice' &&
          heroBody((v) => (
            <HeroPracticeView view={v} session={heroSession} onSessionChange={setHeroSession} onComplete={() => setCurrentView('transmission')} onBack={() => setCurrentView('source')} />
          ))}
        {selected.kind === 'hero' && currentView === 'transmission' &&
          heroBody((v) => (
            <HeroTransmissionView
              view={v}
              session={heroSession}
              onBackToPractice={() => setCurrentView('practice')}
              onPractiseAgain={() => {
                setHeroSession(null);
                setCurrentView('practice');
              }}
              onStudySource={() => setCurrentView('source')}
              onExploreMore={() => setCurrentView('discovery')}
            />
          ))}

        {selected.kind === 'showcase' && currentView === 'source' && (
          <SourceAnalysisView capCase={capCase} onEnterPractice={() => setCurrentView('practice')} onBackToDiscovery={() => setCurrentView('discovery')} />
        )}
        {selected.kind === 'showcase' && currentView === 'practice' && (
          <WorkspaceCompiler
            capCase={capCase}
            currentTime={currentTime}
            onTimeChange={setCurrentTime}
            isPlaying={isPlaying}
            onTogglePlay={() => setIsPlaying(!isPlaying)}
            onOpenLineage={() => setIsLineageOpen(true)}
            onJumpFirstDivergence={() => setIsDivergenceModalOpen(true)}
            onLaunchRetry={() => setIsMicroPracticeOpen(true)}
          />
        )}
        {selected.kind === 'showcase' && currentView === 'transmission' && (
          <TransmissionCompleteView
            capCase={capCase}
            onOpenLineage={() => setIsLineageOpen(true)}
            onRestartCase={() => {
              setCurrentTime(0.0);
              setCurrentView('practice');
            }}
            onExploreMore={() => setCurrentView('discovery')}
          />
        )}

        {currentView === 'mine' && (
          <MySkillsView
            cases={heroCases}
            loading={heroLoading}
            error={heroError}
            health={health}
            onRefresh={loadCases}
            onOpen={(id) => select({ kind: 'hero', id }, 'source')}
            onCreate={() => select({ kind: 'composer' })}
          />
        )}

        {currentView === 'steward' && (
          <StewardConsole
            health={health}
            onOpenSkill={(id) => select({ kind: 'hero', id }, 'source')}
            onLibraryChanged={loadCases}
          />
        )}
        {currentView === 'evidence' && (
          <EvidencePage onBack={() => setCurrentView('discovery')} />
        )}
      </main>

      <footer className="border-t border-outline bg-surface-dim px-4 sm:px-6 py-3 text-[11px] font-mono text-on-surface-variant flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-1.5 text-on-surface font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-cadmium-amber" />
            ANVESHAN PROTOTYPE
          </span>
          <span className="text-outline">|</span>
          <span className="text-cadmium-amber">GOOGLE CLOUD AI BUILDER CUP 2026</span>
        </div>
        <div className="flex items-center gap-4">
          {selected.kind === 'showcase' && debug && (
            <button onClick={() => setIsLineageOpen(true)} className="hover:text-caliper-cyan underline decoration-caliper-cyan/50 transition-colors">
              VIEW PROVENANCE DAG
            </button>
          )}
          <span data-plain-exempt>{selected.kind === 'showcase' ? 'SYNTHETIC REPLAY FIXTURE' : IS_MOCK ? 'MOCK DATA (SYNTHETIC)' : 'Scores come from fixed rules, never from the AI'}</span>
          {health?.steward_enabled !== false && currentView !== 'steward' && (
            <button
              onClick={() => setCurrentView('steward')}
              className="hover:text-caliper-cyan transition-colors"
            >
              Steward sign-in
            </button>
          )}
          <button
            onClick={() => setCurrentView('evidence')}
            className="hover:text-caliper-cyan transition-colors"
          >
            How we check results
          </button>
        </div>
      </footer>

      {selected.kind === 'showcase' && (
        <>
          <FirstDivergenceModal capCase={capCase} isOpen={isDivergenceModalOpen} onClose={() => setIsDivergenceModalOpen(false)} onLaunchMicroPractice={() => setIsMicroPracticeOpen(true)} />
          <MicroPracticeRetryModal
            capCase={capCase}
            isOpen={isMicroPracticeOpen}
            onClose={() => setIsMicroPracticeOpen(false)}
            onCompleteRetry={() => {
              setIsMicroPracticeOpen(false);
              setCurrentView('transmission');
            }}
          />
          <LineageDrawer telemetry={capCase.telemetry} isOpen={isLineageOpen} onClose={() => setIsLineageOpen(false)} />
          <LifecycleInspectorModal stage={modalStage} onClose={() => setModalStage(null)} telemetry={capCase.telemetry} />
        </>
      )}
      <StitchModal isOpen={isStitchOpen} onClose={() => setIsStitchOpen(false)} />
      <GuideModal isOpen={guideOpen} onClose={() => setGuideOpen(false)} />
      <ApiKeyModal isOpen={keyOpen} onClose={() => setKeyOpen(false)} />
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  );
}
export default App;
