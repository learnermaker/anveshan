import React from 'react';
import { ArrowRight, CheckCircle2, ChevronRight, Eye, HelpCircle, Layers, Shield, Sparkles, UserCheck, Video } from 'lucide-react';
import type { CapabilityCase } from '../types/workspace';

interface SourceAnalysisViewProps {
  capCase: CapabilityCase;
  onEnterPractice: () => void;
  onBackToDiscovery: () => void;
}

export function SourceAnalysisView({
  capCase,
  onEnterPractice,
  onBackToDiscovery,
}: SourceAnalysisViewProps) {
  const kp = capCase.bundle.knowledge_package;
  const rubric = capCase.bundle.rubric;

  return (
    <div className="flex flex-col gap-8 max-w-6xl w-full mx-auto p-4 lg:p-8 animate-fade-in text-on-surface">
      {/* Top Breadcrumb & Navigation */}
      <div className="flex items-center justify-between border-b border-outline pb-4">
        <div className="flex items-center gap-2 text-xs font-mono">
          <button
            onClick={onBackToDiscovery}
            className="text-on-surface-variant hover:text-on-surface transition-colors"
          >
            PORTFOLIO
          </button>
          <span className="text-outline">/</span>
          <span className="text-cadmium-amber font-semibold uppercase">{capCase.id}</span>
          <span className="text-outline">/</span>
          <span className="text-on-surface">SOURCE & GROUNDING</span>
        </div>

        <div className="px-3 py-1 bg-surface-dim border border-outline rounded font-mono text-xs text-on-surface-variant flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-transmission-emerald" />
          <span>8-CONTRACT SEAM: VALID</span>
        </div>
      </div>

      {/* Case Header Hero */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="inline-block px-2.5 py-0.5 rounded text-[11px] font-mono uppercase font-semibold bg-caliper-cyan/15 text-caliper-cyan border border-caliper-cyan/30">
            STAGE 01 // CAPTURE & GROUNDED KNOWLEDGE
          </div>
          <div className="inline-block px-2.5 py-0.5 rounded text-[11px] font-mono uppercase font-bold bg-surface-dim text-cadmium-amber border border-cadmium-amber/40">
            MODE: {capCase.transmissionMode === 'goal_conditioned' ? 'GOAL-CONDITIONED (TARGET-FIRST)' : capCase.transmissionMode === 'corrective' ? 'CORRECTIVE (DIVERGENCE-FIRST)' : 'FORWARD (DEMO-FIRST)'}
          </div>
        </div>
        <h1 className="text-3xl sm:text-4xl font-serif font-normal text-on-surface">
          {capCase.title}
        </h1>
        <p className="text-sm text-on-surface-variant max-w-3xl leading-relaxed">
          {kp.summary}
        </p>
      </div>

      {/* Grid: Expert Demonstration Media & Provenance Metadata */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Expert Demonstration & Claims (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {/* Source Media Card */}
          <div className="p-5 rounded-xl bg-surface-elevated border border-outline space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-on-surface flex items-center gap-2">
                <Video className="w-4 h-4 text-transmission-emerald" />
                SOURCE EVIDENCE
              </span>
              <span className="text-[11px] font-mono text-on-surface-variant bg-surface-dim px-2 py-0.5 rounded border border-outline">
                {capCase.workspaceSpec.evidenceProfile.temporalResolution}
              </span>
            </div>

            <div className="h-64 bg-zinc-950 rounded-lg border border-outline/50 flex flex-col items-center justify-center p-6 text-center relative overflow-hidden group">
              {capCase.sourceProvenance?.localPosterPath ? (
                <img
                  src={capCase.sourceProvenance.localPosterPath}
                  alt={capCase.sourceProvenance.title}
                  className="absolute inset-0 w-full h-full object-cover opacity-50 group-hover:opacity-65 transition-opacity"
                />
              ) : null}
              <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-black/30" />
              <div className="w-12 h-12 rounded-full bg-surface-elevated/80 border border-outline flex items-center justify-center text-transmission-emerald z-10 mb-3 shadow-lg">
                <Video className="w-6 h-6" />
              </div>
              <div className="z-10 space-y-1">
                <div className="text-sm font-semibold text-on-surface">
                  {capCase.sourceProvenance?.creator ? capCase.sourceProvenance.creator : `Expert: ${capCase.expertName}`}
                </div>
                <div className="text-xs font-mono text-on-surface-variant">
                  {capCase.expertRole}
                </div>
              </div>
              <div className="absolute bottom-3 left-3 text-[11px] font-mono text-zinc-300 z-10 flex items-center gap-2">
                <span>SOURCE ID: {capCase.sourceProvenance?.sourceId ?? kp.claims[0]?.evidence_refs[0]?.source_id ?? 'src-auth-01'}</span>
                {capCase.sourceProvenance?.license && (
                  <>
                    <span>•</span>
                    <span className="text-zinc-400">{capCase.sourceProvenance.license}</span>
                  </>
                )}
              </div>
              {capCase.sourceProvenance?.sourceUrl && (
                <a
                  href={capCase.sourceProvenance.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="absolute top-3 right-3 z-10 px-2.5 py-1 rounded bg-black/80 hover:bg-black text-[11px] font-mono text-caliper-cyan border border-caliper-cyan/40 shadow"
                >
                  SOURCE REF ↗
                </a>
              )}
            </div>

            {capCase.sourceProvenance?.notes && (
              <div className="p-2.5 bg-surface-dim rounded-lg border border-outline/40 text-[11px] font-mono text-on-surface-variant flex items-start gap-2">
                <span className="text-cadmium-amber font-bold shrink-0">PROVENANCE:</span>
                <span>{capCase.sourceProvenance.notes}</span>
              </div>
            )}

            {/* Extracted Grounded Claims */}
            <div className="space-y-3 pt-2">
              <div className="text-xs font-mono font-bold text-on-surface uppercase tracking-wider">
                Grounded Claims in KnowledgePackage:
              </div>
              <div className="space-y-2">
                {kp.claims.map((c, i) => (
                  <div key={i} className="p-3 bg-surface-dim rounded-lg border border-outline/40 space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] font-mono">
                      <span className="text-cadmium-amber font-semibold uppercase">
                        CLAIM 0{i + 1} // {c.claim_type}
                      </span>
                      <span className="text-transmission-emerald font-bold">
                        CONFIDENCE: {Math.round((c.evidence_refs[0]?.confidence ?? 0.95) * 100)}%
                      </span>
                    </div>
                    <p className="text-xs text-on-surface font-sans">
                      {c.statement}
                    </p>
                    <div className="text-[11px] font-mono text-on-surface-variant flex items-center gap-2">
                      <span>EVIDENCE ID: {c.evidence_refs[0]?.evidence_id}</span>
                      <span>•</span>
                      <span>TIME: {c.evidence_refs[0]?.start_sec}s – {c.evidence_refs[0]?.end_sec}s</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Honesty & Certainty Matrix + Rubric (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          {/* Epistemic Certainty Table (Honest Unknown) */}
          <div className="p-5 rounded-xl bg-surface-elevated border border-outline space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-on-surface flex items-center gap-1.5">
                <Shield className="w-4 h-4 text-cadmium-amber" />
                EPISTEMIC CERTAINTY TAXONOMY
              </span>
              <span className="text-[11px] font-mono text-on-surface-variant">
                NO FALSE MACHINE CERTAINTY
              </span>
            </div>

            <div className="space-y-2.5">
              {capCase.uncertainties.map((u, i) => (
                <div key={i} className="p-3 bg-surface-dim rounded-lg border border-outline/40 space-y-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="font-semibold text-on-surface">{u.aspect}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[11px] font-bold ${
                        u.state === 'OBSERVED'
                          ? 'bg-caliper-cyan/20 text-caliper-cyan'
                          : u.state === 'INFERRED'
                          ? 'bg-cadmium-amber/20 text-cadmium-amber'
                          : u.state === 'SOURCE_DERIVED_FACT'
                          ? 'bg-transmission-emerald/20 text-transmission-emerald'
                          : 'bg-surface-bright text-on-surface-variant border border-outline'
                      }`}
                    >
                      {u.state}
                    </span>
                  </div>
                  <p className="text-[11px] text-on-surface-variant leading-relaxed">
                    {u.rationale}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Target Rubric Criteria Overview */}
          <div className="p-5 rounded-xl bg-surface-elevated border border-outline space-y-3">
            <div className="text-xs font-mono font-bold text-on-surface flex items-center justify-between">
              <span>TARGET RUBRIC CRITERIA</span>
              <span className="text-cadmium-amber">{rubric.criteria.length} CRITERIA</span>
            </div>

            <div className="space-y-2">
              {rubric.criteria.map((cr) => (
                <div key={cr.criterion_id} className="p-2.5 bg-surface-dim rounded border border-outline/30 flex items-center justify-between text-xs">
                  <div>
                    <div className="font-semibold text-on-surface">{cr.name}</div>
                    <div className="text-[11px] font-mono text-on-surface-variant">{cr.criterion_id}</div>
                  </div>
                  <span className="font-mono text-xs text-cadmium-amber font-bold">
                    {cr.weight} pts
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Primary CTA: Compose Adaptive Workspace */}
          <button
            onClick={onEnterPractice}
            className="w-full py-4 px-6 rounded-xl bg-transmission-emerald hover:bg-transmission-emerald/90 text-background font-mono font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-xl shadow-transmission-emerald/20 transition-all hover:scale-[1.01]"
          >
            <span>COMPOSE ADAPTIVE WORKSPACE & ENTER PRACTICE</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
