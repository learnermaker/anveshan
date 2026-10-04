import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { DiscoveryView } from './components/DiscoveryView';
import { SourceAnalysisView } from './components/SourceAnalysisView';
import { WorkspaceCompiler } from './workspaces/WorkspaceCompiler';
import { TransmissionCompleteView } from './components/TransmissionCompleteView';
import { FirstDivergenceModal } from './components/FirstDivergenceModal';
import { MicroPracticeRetryModal } from './components/MicroPracticeRetryModal';
import { LineageDrawer } from './components/LineageDrawer';
import { StitchModal } from './components/StitchModal';
import { SettingsModal } from './components/SettingsModal';
import { LifecycleInspectorModal } from './components/LifecycleInspectorModal';

import { getCapabilityCase, DEFAULT_CASE_ID } from './data/cases/registry';
import { getStoredGeminiConfig, saveStoredGeminiConfig } from './model/geminiGateway';
import type { AppView } from './types/workspace';
import type { GeminiConfig } from './types/gemini';
import type { LifecycleStage } from './components/LifecycleInspectorModal';

const getInitialView = (): AppView => {
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    const v = params.get('view') as AppView;
    if (v && ['discovery', 'source', 'practice', 'transmission'].includes(v)) {
      return v;
    }
  }
  return 'discovery';
};

const getInitialCaseId = (): string => {
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    const c = params.get('case');
    if (c && getCapabilityCase(c)) {
      return c;
    }
  }
  return DEFAULT_CASE_ID;
};

export function App() {
  const [currentView, setCurrentView] = useState<AppView>(getInitialView);
  const [selectedCaseId, setSelectedCaseId] = useState<string>(getInitialCaseId);
  const [geminiConfig, setGeminiConfig] = useState<GeminiConfig>(getStoredGeminiConfig());

  // Synchronize view & case to URL search params for deep linking and history
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('view') !== currentView || params.get('case') !== selectedCaseId) {
        params.set('view', currentView);
        params.set('case', selectedCaseId);
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState({}, '', newUrl);
      }
    }
  }, [currentView, selectedCaseId]);

  // Dynamic Case state
  const capCase = getCapabilityCase(selectedCaseId);

  // Playhead state for temporal cases (micrometer, etc.)
  const [currentTime, setCurrentTime] = useState<number>(19.2); // Key first divergence locus
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // Modals
  const [isDivergenceModalOpen, setIsDivergenceModalOpen] = useState<boolean>(false);
  const [isMicroPracticeOpen, setIsMicroPracticeOpen] = useState<boolean>(false);
  const [isLineageOpen, setIsLineageOpen] = useState<boolean>(false);
  const [isStitchOpen, setIsStitchOpen] = useState<boolean>(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [modalStage, setModalStage] = useState<LifecycleStage | null>(null);

  const animationFrameRef = useRef<number | null>(null);
  const lastTimestampRef = useRef<number | null>(null);

  // Playback loop for video/temporal workspaces
  useEffect(() => {
    if (!isPlaying) {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
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
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlaying]);

  // Handle case selection
  const handleSelectCase = (caseId: string) => {
    setSelectedCaseId(caseId);
    setCurrentTime(19.2);
    setIsPlaying(false);
  };

  // Handle successful retry completion: transitions to verified transmission view
  const handleCompleteRetry = () => {
    setIsMicroPracticeOpen(false);
    setCurrentView('transmission');
  };

  const handleSaveConfig = (newConfig: GeminiConfig) => {
    setGeminiConfig(newConfig);
    saveStoredGeminiConfig(newConfig);
  };

  return (
    <div className="min-h-screen bg-background text-on-surface flex flex-col noise-overlay selection:bg-cadmium-amber/30 selection:text-white">
      {/* Precision Instrument Header */}
      <Header
        currentView={currentView}
        onSelectView={setCurrentView}
        currentCase={capCase}
        onSelectCase={handleSelectCase}
        analysisMode={geminiConfig.mode}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenStitchDesign={() => setIsStitchOpen(true)}
      />

      {/* Main Dynamic Viewport */}
      <main className="flex-1 max-w-workbench w-full mx-auto p-4 lg:p-6 flex flex-col gap-6">
        {currentView === 'discovery' && (
          <DiscoveryView
            selectedCaseId={selectedCaseId}
            onSelectCase={(id) => {
              handleSelectCase(id);
              setCurrentView('source');
            }}
          />
        )}

        {currentView === 'source' && (
          <SourceAnalysisView
            capCase={capCase}
            onEnterPractice={() => setCurrentView('practice')}
            onBackToDiscovery={() => setCurrentView('discovery')}
          />
        )}

        {currentView === 'practice' && (
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

        {currentView === 'transmission' && (
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
      </main>

      {/* Global Precision Instrument Footer */}
      <footer className="border-t border-outline bg-surface-dim px-6 py-3 text-[11px] font-mono text-on-surface-variant flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-on-surface font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-transmission-emerald" />
            ANVESHAN CORE v1.0.0
          </span>
          <span className="text-outline">|</span>
          <span>CAPABILITY: {capCase.id}</span>
          <span className="text-outline">|</span>
          <span className="text-cadmium-amber">GOOGLE CLOUD AI BUILDER CUP 2026</span>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsLineageOpen(true)}
            className="hover:text-caliper-cyan underline decoration-caliper-cyan/50 transition-colors"
          >
            VIEW PROVENANCE DAG
          </button>
          <span>FIXTURE: REPLAY VERIFIED // HONEST SPEC</span>
        </div>
      </footer>

      {/* Forensic First Divergence Modal */}
      <FirstDivergenceModal
        capCase={capCase}
        isOpen={isDivergenceModalOpen}
        onClose={() => setIsDivergenceModalOpen(false)}
        onLaunchMicroPractice={() => setIsMicroPracticeOpen(true)}
      />

      {/* Bounded Adaptive Micro-Practice Modal */}
      <MicroPracticeRetryModal
        capCase={capCase}
        isOpen={isMicroPracticeOpen}
        onClose={() => setIsMicroPracticeOpen(false)}
        onCompleteRetry={handleCompleteRetry}
      />

      {/* Cryptographic Lineage & Merkle Provenance DAG Drawer */}
      <LineageDrawer
        telemetry={capCase.telemetry}
        isOpen={isLineageOpen}
        onClose={() => setIsLineageOpen(false)}
      />

      {/* Google Stitch Reference Canvas Modal */}
      <StitchModal
        isOpen={isStitchOpen}
        onClose={() => setIsStitchOpen(false)}
      />

      {/* Gemini Model Gateway Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        config={geminiConfig}
        onSaveConfig={handleSaveConfig}
      />

      {/* Raw Stage Inspector Modal */}
      <LifecycleInspectorModal
        stage={modalStage}
        onClose={() => setModalStage(null)}
        telemetry={capCase.telemetry}
      />
    </div>
  );
}
export default App;
