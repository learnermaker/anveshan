import React, { useState } from 'react';
import type { CapabilityCase } from '../types/workspace';
import { DualDeckPlayer } from '../components/DualDeckPlayer';
import { SensoryRibbon } from '../components/SensoryRibbon';
import { RubricHUD } from '../components/RubricHUD';
import { TransmissionGainHero } from '../components/TransmissionGainHero';

interface ForensicInstrumentWorkspaceProps {
  capCase: CapabilityCase;
  currentTime: number;
  onTimeChange: (time: number) => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onOpenLineage: () => void;
  onJumpFirstDivergence: () => void;
  onLaunchRetry: () => void;
}

export function ForensicInstrumentWorkspace({
  capCase,
  currentTime,
  onTimeChange,
  isPlaying,
  onTogglePlay,
  onOpenLineage,
  onJumpFirstDivergence,
  onLaunchRetry,
}: ForensicInstrumentWorkspaceProps) {
  const telemetry = capCase.telemetry;
  const [selectedCriterionId, setSelectedCriterionId] = useState<string | null>('CRIT-RATCHET');

  return (
    <div className="flex flex-col gap-6 w-full animate-fade-in">
      {/* Top Section: Comparative Decks & Rubric HUD */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left/Center Workspace: Dual Video Deck + Waveform Ribbon (8 columns) */}
        <div className="xl:col-span-8 flex flex-col gap-4">
          <DualDeckPlayer
            telemetry={telemetry}
            currentTime={currentTime}
            onTimeChange={onTimeChange}
            isPlaying={isPlaying}
            onTogglePlay={onTogglePlay}
          />

          <SensoryRibbon
            telemetry={telemetry}
            currentTime={currentTime}
            onTimeChange={onTimeChange}
          />
        </div>

        {/* Right Telemetry Column: Rubric HUD (4 columns) */}
        <div className="xl:col-span-4 h-full">
          <RubricHUD
            telemetry={telemetry}
            currentTime={currentTime}
            onTimeChange={onTimeChange}
            selectedCriterionId={selectedCriterionId}
            onSelectCriterion={setSelectedCriterionId}
          />
        </div>
      </div>

      {/* Bottom Section: Quantitative Transmission Gain Hero Card */}
      <TransmissionGainHero
        telemetry={telemetry}
        onOpenLineage={onOpenLineage}
      />
    </div>
  );
}
