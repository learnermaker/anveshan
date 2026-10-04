import React from 'react';
import { AlertTriangle, ArrowRight, CheckCircle2, HelpCircle, Shield, X, Eye, Sparkles } from 'lucide-react';
import type { CapabilityCase } from '../types/workspace';
import type { CertaintyState } from '../types/workspace';

interface FirstDivergenceModalProps {
  capCase: CapabilityCase;
  isOpen: boolean;
  onClose: () => void;
  onLaunchMicroPractice: () => void;
}

export function FirstDivergenceModal({
  capCase,
  isOpen,
  onClose,
  onLaunchMicroPractice,
}: FirstDivergenceModalProps) {
  if (!isOpen) return null;

  const div = capCase.firstDivergence;

  const renderBadge = (certainty: CertaintyState) => {
    switch (certainty) {
      case 'OBSERVED':
        return (
          <span className="px-2 py-0.5 text-[10px] font-mono font-semibold bg-caliper-cyan/15 text-caliper-cyan border border-caliper-cyan/30 rounded">
            OBSERVED (OPTICAL / ACOUSTIC)
          </span>
        );
      case 'INFERRED':
        return (
          <span className="px-2 py-0.5 text-[10px] font-mono font-semibold bg-cadmium-amber/15 text-cadmium-amber border border-cadmium-amber/30 rounded">
            INFERRED (PHYSICAL CAUSALITY)
          </span>
        );
      case 'SOURCE_DERIVED_FACT':
        return (
          <span className="px-2 py-0.5 text-[10px] font-mono font-semibold bg-transmission-emerald/15 text-transmission-emerald border border-transmission-emerald/30 rounded">
            SOURCE-DERIVED FACT
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-[10px] font-mono font-semibold bg-surface-bright text-on-surface-variant border border-outline rounded">
            UNKNOWN
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md animate-fade-in">
      <div className="bg-surface-elevated border border-divergence-crimson/50 rounded-xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-divergence-crimson/10 border-b border-divergence-crimson/30 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-divergence-crimson/20 flex items-center justify-center text-divergence-crimson">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] font-mono uppercase tracking-widest text-divergence-crimson font-bold">
                FORENSIC VERIFICATION // FIRST DIVERGENCE DETECTED
              </div>
              <h2 className="text-base font-semibold text-on-surface">
                {div.divergenceTitle}
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-bright transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-sm">
          {/* Rubric Criterion Mapping */}
          <div className="p-3.5 bg-surface-dim rounded-lg border border-outline/40 flex items-start justify-between gap-4">
            <div>
              <div className="text-[10px] font-mono uppercase text-on-surface-variant">
                TARGET RUBRIC CRITERION
              </div>
              <div className="font-semibold text-on-surface text-sm mt-0.5">
                {div.criterionName}
              </div>
              <div className="text-[11px] font-mono text-cadmium-amber mt-1">
                CRITERION ID: {div.criterionId}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] font-mono uppercase text-on-surface-variant">
                TEMPORAL / STEP LOCUS
              </div>
              <div className="font-mono font-bold text-on-surface text-sm mt-0.5">
                {div.timeSec ? `00:${String(Math.floor(div.timeSec)).padStart(2, '0')}.2` : `Step #${div.stepIndex}`}
              </div>
            </div>
          </div>

          {/* 1. Observation */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono uppercase tracking-wider text-on-surface-variant font-semibold flex items-center gap-1.5">
                <Eye className="w-3.5 h-3.5 text-caliper-cyan" /> 1. EMPIRICAL OBSERVATION
              </span>
              {renderBadge(div.observationCertainty)}
            </div>
            <p className="text-on-surface p-3 bg-surface-dim/80 rounded border border-outline/30 text-xs leading-relaxed font-mono">
              "{div.observation}"
            </p>
            <div className="text-[11px] text-on-surface-variant font-mono pl-1">
              LOCUS: <span className="text-on-surface">{div.evidenceLocation}</span>
            </div>
          </div>

          {/* 2. Model Interpretation */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono uppercase tracking-wider text-on-surface-variant font-semibold flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-cadmium-amber" /> 2. GEMINI MULTIMODAL INTERPRETATION
              </span>
              {renderBadge(div.interpretationCertainty)}
            </div>
            <p className="text-on-surface p-3 bg-surface-dim/80 rounded border border-outline/30 text-xs leading-relaxed">
              {div.interpretation}
            </p>
          </div>

          {/* 3. Downstream Consequence */}
          <div className="p-3 bg-divergence-crimson/5 rounded border border-divergence-crimson/20">
            <div className="text-[11px] font-mono uppercase tracking-wider text-divergence-crimson font-semibold">
              3. DETERMINISTIC FAILURE CONSEQUENCE
            </div>
            <p className="text-xs text-on-surface mt-1 leading-relaxed">
              {div.consequence}
            </p>
          </div>

          {/* 4. Uncertainty & Unknown Boundary */}
          {div.unknownFactors.length > 0 && (
            <div className="p-3 bg-surface-dim rounded border border-outline/40 text-xs">
              <div className="flex items-center gap-1.5 text-[11px] font-mono font-semibold text-on-surface-variant mb-1">
                <HelpCircle className="w-3.5 h-3.5 text-on-surface-variant" /> 4. UNCERTAINTY BOUNDARY (HONEST UNKNOWN)
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-on-surface-variant font-mono text-[11px]">
                {div.unknownFactors.map((u, i) => (
                  <li key={i}>{u}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 5. Targeted Intervention */}
          <div className="p-3.5 bg-transmission-emerald/10 rounded-lg border border-transmission-emerald/30">
            <div className="text-[11px] font-mono uppercase tracking-wider text-transmission-emerald font-semibold flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> 5. TARGETED ADAPTIVE INTERVENTION
            </div>
            <p className="text-xs text-on-surface font-medium mt-1 leading-relaxed">
              {div.targetedIntervention}
            </p>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-surface-dim border-t border-outline flex items-center justify-between gap-4">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-mono text-on-surface-variant hover:text-on-surface transition-colors"
          >
            DISMISS INSPECTOR
          </button>
          <button
            onClick={() => {
              onClose();
              onLaunchMicroPractice();
            }}
            className="px-5 py-2.5 rounded-lg bg-transmission-emerald hover:bg-transmission-emerald/90 text-background font-mono font-bold text-xs uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-transmission-emerald/20 transition-all hover:scale-[1.02]"
          >
            <span>LAUNCH TARGETED RETRY</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
