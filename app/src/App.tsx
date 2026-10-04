import React, { useState, useEffect, useRef } from 'react';
import { Header, LifecycleStage } from './components/Header';
import { DualDeckPlayer } from './components/DualDeckPlayer';
import { SensoryRibbon } from './components/SensoryRibbon';
import { RubricHUD } from './components/RubricHUD';
import { TransmissionGainHero } from './components/TransmissionGainHero';
import { LineageDrawer } from './components/LineageDrawer';
import { LifecycleInspectorModal } from './components/LifecycleInspectorModal';
import { getTransmissionTelemetry } from './data/adapter';

export function App() {
  const telemetry = getTransmissionTelemetry();
  const [currentTime, setCurrentTime] = useState<number>(19.2); // Start at key divergence moment!
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [activeStage, setActiveStage] = useState<LifecycleStage>('transmission');
  const [selectedCriterionId, setSelectedCriterionId] = useState<string | null>('CRIT-RATCHET');
  const [isLineageOpen, setIsLineageOpen] = useState<boolean>(false);
  const [modalStage, setModalStage] = useState<LifecycleStage | null>(null);

  const animationFrameRef = useRef<number | null>(null);
  const lastTimestampRef = useRef<number | null>(null);

  // Playback loop
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

  const handleStageSelect = (stage: LifecycleStage) => {
    if (stage === 'transmission') {
      setActiveStage('transmission');
    } else {
      setModalStage(stage);
    }
  };

  return (
    <div className="min-h-screen bg-background text-on-surface flex flex-col noise-overlay">
      {/* Precision Instrument Header */}
      <Header
        telemetry={telemetry}
        activeStage={activeStage}
        onSelectStage={handleStageSelect}
      />

      {/* Main Workbench Body */}
      <main className="flex-1 max-w-workbench w-full mx-auto p-4 lg:p-6 flex flex-col gap-6">
        {/* Top Section: Comparative Decks & Rubric HUD */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          {/* Left/Center Workspace: Dual Video Deck + Waveform Ribbon (8 columns) */}
          <div className="xl:col-span-8 flex flex-col gap-4">
            <DualDeckPlayer
              telemetry={telemetry}
              currentTime={currentTime}
              onTimeChange={setCurrentTime}
              isPlaying={isPlaying}
              onTogglePlay={() => setIsPlaying(!isPlaying)}
            />

            <SensoryRibbon
              telemetry={telemetry}
              currentTime={currentTime}
              onTimeChange={setCurrentTime}
            />
          </div>

          {/* Right Telemetry Column: Rubric HUD (4 columns) */}
          <div className="xl:col-span-4 h-full">
            <RubricHUD
              telemetry={telemetry}
              currentTime={currentTime}
              onTimeChange={setCurrentTime}
              selectedCriterionId={selectedCriterionId}
              onSelectCriterion={setSelectedCriterionId}
            />
          </div>
        </div>

        {/* Bottom Section: Quantitative Transmission Gain Hero Card */}
        <TransmissionGainHero
          telemetry={telemetry}
          onOpenLineage={() => setIsLineageOpen(true)}
        />
      </main>

      {/* Footer / System Status Line */}
      <footer className="border-t border-outline bg-surface-dim px-6 py-3 text-[11px] font-mono text-on-surface-variant flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-on-surface font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-transmission-emerald" />
            ANVESHAN CORE v1.0.0
          </span>
          <span className="text-outline">|</span>
          <span>FIXTURE: transmission_case_001</span>
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
          <span>BUILD: PRODUCTION VERIFIED</span>
        </div>
      </footer>

      {/* Lineage & Provenance Modal */}
      <LineageDrawer
        telemetry={telemetry}
        isOpen={isLineageOpen}
        onClose={() => setIsLineageOpen(false)}
      />

      {/* Upstream Lifecycle Stage Inspector (01. Source, 02. Knowledge, 03. Practice) */}
      <LifecycleInspectorModal
        stage={modalStage}
        onClose={() => setModalStage(null)}
        telemetry={telemetry}
      />
    </div>
  );
}

export default App;
