import React from 'react';
import type { CapabilityCase } from '../types/workspace';
import { ForensicInstrumentWorkspace } from './ForensicInstrumentWorkspace';
import { SpatialCanvasWorkspace } from './SpatialCanvasWorkspace';
import { DiagnosticWorkspace } from './DiagnosticWorkspace';
import { StateTransitionWorkspace } from './StateTransitionWorkspace';
import { RhythmInstrumentWorkspace } from './RhythmInstrumentWorkspace';
import { SpatialSequenceWorkspace } from './SpatialSequenceWorkspace';
import { FirstDivergenceWorkspace } from './FirstDivergenceWorkspace';
import { Cpu, Sparkles, ArrowRight, Layers } from 'lucide-react';

interface WorkspaceCompilerProps {
  capCase: CapabilityCase;
  currentTime: number;
  onTimeChange: (time: number) => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onOpenLineage: () => void;
  onJumpFirstDivergence: () => void;
  onLaunchRetry: () => void;
}

export function WorkspaceCompiler({
  capCase,
  currentTime,
  onTimeChange,
  isPlaying,
  onTogglePlay,
  onOpenLineage,
  onJumpFirstDivergence,
  onLaunchRetry,
}: WorkspaceCompilerProps) {
  const spec = capCase.workspaceSpec;

  const renderActiveWorkspace = () => {
    switch (spec.workspaceType) {
      case 'spatial_canvas':
        return (
          <SpatialCanvasWorkspace
            capCase={capCase}
            onOpenLineage={onOpenLineage}
            onJumpFirstDivergence={onJumpFirstDivergence}
            onLaunchRetry={onLaunchRetry}
          />
        );

      case 'diagnostic_workspace':
        return (
          <DiagnosticWorkspace
            capCase={capCase}
            onOpenLineage={onOpenLineage}
            onJumpFirstDivergence={onJumpFirstDivergence}
            onLaunchRetry={onLaunchRetry}
          />
        );

      case 'state_transition':
        return (
          <StateTransitionWorkspace
            capCase={capCase}
            onOpenLineage={onOpenLineage}
            onJumpFirstDivergence={onJumpFirstDivergence}
            onLaunchRetry={onLaunchRetry}
          />
        );

      case 'rhythm_instrument':
        return (
          <RhythmInstrumentWorkspace
            capCase={capCase}
            onOpenLineage={onOpenLineage}
            onJumpFirstDivergence={onJumpFirstDivergence}
            onLaunchRetry={onLaunchRetry}
          />
        );

      case 'spatial_sequence':
        return (
          <SpatialSequenceWorkspace
            capCase={capCase}
            onOpenLineage={onOpenLineage}
            onJumpFirstDivergence={onJumpFirstDivergence}
            onLaunchRetry={onLaunchRetry}
          />
        );

      case 'first_divergence':
        return (
          <FirstDivergenceWorkspace
            capCase={capCase}
            onOpenLineage={onOpenLineage}
            onJumpFirstDivergence={onJumpFirstDivergence}
            onLaunchRetry={onLaunchRetry}
          />
        );

      case 'forensic_instrument':
      default:
        return (
          <ForensicInstrumentWorkspace
            capCase={capCase}
            currentTime={currentTime}
            onTimeChange={onTimeChange}
            isPlaying={isPlaying}
            onTogglePlay={onTogglePlay}
            onOpenLineage={onOpenLineage}
            onJumpFirstDivergence={onJumpFirstDivergence}
            onLaunchRetry={onLaunchRetry}
          />
        );
    }
  };

  return (
    <div className="flex flex-col gap-5 w-full">
      {/* Declarative GenUI Composition Banner */}
      <div className="bg-surface-elevated/90 border border-outline/70 rounded-xl px-5 py-3 shadow-lg flex flex-wrap items-center justify-between gap-4 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cadmium-amber/15 border border-cadmium-amber/30 flex items-center justify-center text-cadmium-amber">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] font-mono uppercase tracking-widest text-cadmium-amber font-bold flex items-center gap-1.5">
              <span>GENERATIVE UI // WORKSPACE COMPOSITION SPECIFICATION</span>
            </div>
            <div className="text-xs text-on-surface flex flex-wrap items-center gap-2 mt-0.5 font-mono">
              <span className="text-on-surface-variant">EVIDENCE:</span>
              <span className="font-bold text-caliper-cyan">
                {capCase.primaryModalities.join(' + ').toUpperCase()}
              </span>
              <span className="text-outline">→</span>
              <span className="text-on-surface-variant">ARCHETYPE:</span>
              <span className="font-bold text-on-surface">{capCase.archetype}</span>
              <span className="text-outline">→</span>
              <span className="text-on-surface-variant">COMPOSED:</span>
              <span className="font-bold text-transmission-emerald uppercase">
                {spec.title}
              </span>
            </div>
          </div>
        </div>

        <div className="text-right hidden md:block max-w-sm text-[11px] font-mono text-on-surface-variant leading-tight">
          "{spec.compilerRationale}"
        </div>
      </div>

      {/* Render Selected Specialized Adaptive Workspace */}
      {renderActiveWorkspace()}
    </div>
  );
}
