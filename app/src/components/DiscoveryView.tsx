import React from 'react';
import { ArrowRight, Compass, Layers, Music, Scissors, Sparkles, Wrench, Shield, CheckCircle2, ChevronRight, Activity } from 'lucide-react';
import { CAPABILITY_CASES, ALL_CAPABILITY_IDS } from '../data/cases/registry';
import type { CapabilityCase } from '../types/workspace';

interface DiscoveryViewProps {
  onSelectCase: (caseId: string) => void;
  selectedCaseId: string;
}

export function DiscoveryView({ onSelectCase, selectedCaseId }: DiscoveryViewProps) {
  const getIcon = (id: string) => {
    switch (id) {
      case 'kolam':
        return <Compass className="w-5 h-5 text-transmission-emerald" />;
      case 'bicycle_repair':
        return <Wrench className="w-5 h-5 text-cadmium-amber" />;
      case 'weaving':
        return <Layers className="w-5 h-5 text-caliper-cyan" />;
      case 'tabla':
        return <Music className="w-5 h-5 text-transmission-emerald" />;
      case 'origami':
        return <Scissors className="w-5 h-5 text-cadmium-amber" />;
      case 'square_knot':
        return <Shield className="w-5 h-5 text-divergence-crimson" />;
      default: // micrometer
        return <Activity className="w-5 h-5 text-caliper-cyan" />;
    }
  };

  return (
    <div className="flex flex-col gap-10 max-w-6xl w-full mx-auto p-4 lg:p-8 animate-fade-in text-on-surface">
      {/* Editorial Cinematic Hero */}
      <section className="text-center max-w-3xl mx-auto space-y-4 pt-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-transmission-emerald/10 border border-transmission-emerald/30 text-transmission-emerald font-mono text-xs font-semibold uppercase tracking-widest">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Google Cloud AI Builder Cup 2026 // Prototype</span>
        </div>

        <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl font-normal tracking-tight text-on-surface leading-[1.15]">
          Transmit what matters.
        </h1>

        <p className="text-base sm:text-lg text-on-surface-variant max-w-2xl mx-auto font-sans leading-relaxed">
          From authentic physical demonstration, to Gemini-grounded multimodal understanding, to adaptive practice and verified human transmission.
        </p>

        {/* Quick Lifecycle Pipeline Ribbon */}
        <div className="pt-3 pb-2 flex flex-wrap items-center justify-center gap-1 sm:gap-2 text-[11px] font-mono text-on-surface-variant font-medium">
          <span className="text-on-surface font-semibold">DEMONSTRATE</span>
          <ChevronRight className="w-3.5 h-3.5 text-outline" />
          <span className="text-on-surface font-semibold">UNDERSTAND</span>
          <ChevronRight className="w-3.5 h-3.5 text-outline" />
          <span className="text-on-surface font-semibold">GROUND</span>
          <ChevronRight className="w-3.5 h-3.5 text-outline" />
          <span className="text-cadmium-amber font-semibold">TEACH</span>
          <ChevronRight className="w-3.5 h-3.5 text-outline" />
          <span className="text-caliper-cyan font-semibold">PRACTICE</span>
          <ChevronRight className="w-3.5 h-3.5 text-outline" />
          <span className="text-divergence-crimson font-semibold">VERIFY</span>
          <ChevronRight className="w-3.5 h-3.5 text-outline" />
          <span className="text-transmission-emerald font-bold">TRANSMIT</span>
        </div>
      </section>

      {/* Capability Archetype Library (7 Cases) */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-outline pb-3">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-widest text-cadmium-amber font-bold">
              MULTIMODAL CAPABILITY PORTFOLIO
            </div>
            <h2 className="text-xl font-semibold font-serif text-on-surface">
              Select a Capability Archetype
            </h2>
          </div>
          <p className="text-xs font-mono text-on-surface-variant max-w-md text-right hidden sm:block">
            The interface adapts because the structure of human expertise changes across physical domains.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {ALL_CAPABILITY_IDS.map((id) => {
            const c = CAPABILITY_CASES[id];
            const isSelected = selectedCaseId === id;

            return (
              <div
                key={id}
                onClick={() => onSelectCase(id)}
                className={`p-5 rounded-xl border cursor-pointer transition-all flex flex-col justify-between group relative overflow-hidden ${
                  isSelected
                    ? 'bg-surface-elevated border-cadmium-amber shadow-xl shadow-cadmium-amber/10 ring-1 ring-cadmium-amber'
                    : 'bg-surface-elevated/70 border-outline hover:border-outline-variant hover:bg-surface-elevated'
                }`}
              >
                {/* Top: Icon + Archetype Tag */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-lg bg-surface-dim border border-outline flex items-center justify-center">
                      {getIcon(id)}
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-surface-dim border border-outline text-on-surface-variant">
                      {c.archetype}
                    </span>
                  </div>

                  <div>
                    <h3 className="font-semibold text-base text-on-surface group-hover:text-cadmium-amber transition-colors">
                      {c.title}
                    </h3>
                    <div className="text-xs font-mono text-on-surface-variant mt-0.5">
                      {c.domain}
                    </div>
                  </div>

                  <p className="text-xs text-on-surface-variant line-clamp-2 leading-relaxed">
                    {c.shortDescription}
                  </p>
                </div>

                {/* Bottom: Modalities + Workspace Type + CTA */}
                <div className="pt-4 mt-4 border-t border-outline/40 space-y-3">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {c.primaryModalities.map((m) => (
                      <span
                        key={m}
                        className="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase bg-surface-dim text-on-surface-variant border border-outline/50"
                      >
                        {m}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-[11px] text-transmission-emerald font-semibold">
                      {c.workspaceSpec.title}
                    </span>
                    <span className="text-cadmium-amber font-bold flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                      ENTER →
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Trust & Architecture Statement */}
      <section className="p-6 rounded-xl bg-surface-dim/80 border border-outline/50 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex items-center gap-2 text-xs font-mono font-bold text-on-surface">
            <Shield className="w-4 h-4 text-transmission-emerald" />
            <span>AUTHENTIC EVIDENCE & FROZEN SEAM ARCHITECTURE</span>
          </div>
          <p className="text-xs text-on-surface-variant leading-relaxed">
            Every capability conforms to the 8 frozen shared contracts: <span className="text-on-surface font-mono">KnowledgePackage, RubricDefinition, PracticeTask, LearnerAttempt, Evaluation, Feedback, and TransmissionRecord</span>. Gemini interprets multimodal cues; deterministic rubrics govern scoring.
          </p>
        </div>

        <button
          onClick={() => onSelectCase(selectedCaseId)}
          className="px-6 py-3 rounded-lg bg-transmission-emerald hover:bg-transmission-emerald/90 text-background font-mono font-bold text-xs uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-transmission-emerald/20 transition-all hover:scale-[1.02] shrink-0"
        >
          <span>LAUNCH SELECTED CAPABILITY</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </section>
    </div>
  );
}
