import React, { useState } from 'react';
import {
  FileCheck2,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Award,
} from 'lucide-react';
import type { CriterionComparison, TransmissionTelemetry } from '../data/adapter';

interface RubricHUDProps {
  telemetry: TransmissionTelemetry;
  currentTime: number;
  onTimeChange: (time: number) => void;
  selectedCriterionId: string | null;
  onSelectCriterion: (id: string | null) => void;
}

export const RubricHUD: React.FC<RubricHUDProps> = ({
  telemetry,
  currentTime,
  onTimeChange,
  selectedCriterionId,
  onSelectCriterion,
}) => {
  const [expandedCriterionId, setExpandedCriterionId] = useState<string | null>('CRIT-RATCHET');
  const metrics = telemetry.metrics;

  const toggleExpand = (id: string) => {
    setExpandedCriterionId(expandedCriterionId === id ? null : id);
    onSelectCriterion(id);
  };

  return (
    <div className="bg-surface-container-low border border-outline rounded-lg flex flex-col h-full overflow-hidden shadow-xl">
      {/* HUD Header */}
      <div className="p-3.5 bg-surface-container border-b border-outline flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileCheck2 className="w-4 h-4 text-transmission-emerald" />
          <div>
            <div className="font-mono text-xs font-bold text-on-surface uppercase tracking-wider">
              RUBRIC HUD // 8-CONTRACT SEAM
            </div>
            <div className="text-[11px] font-sans text-on-surface-variant">
              RUBRIC-OPT-001 • REPLAY FIXTURE STANDARD
            </div>
          </div>
        </div>

        {/* Total Score Badge */}
        <div className="text-right">
          <div className="font-mono text-xs font-bold text-transmission-emerald flex items-center gap-1 justify-end">
            <Award className="w-3.5 h-3.5" />
            <span>{metrics.retryScore.toFixed(1)} / {metrics.maxPossibleScore.toFixed(1)} PTS</span>
          </div>
          <div className="text-[11px] font-mono text-on-surface-variant">
            PASSING: 4.9 PTS (70%)
          </div>
        </div>
      </div>

      {/* Criteria Breakdown List */}
      <div className="p-3 flex-1 overflow-y-auto space-y-3">
        {telemetry.criteriaComparisons.map((c) => {
          const isSelected = selectedCriterionId === c.criterionId;
          const isExpanded = expandedCriterionId === c.criterionId;
          const isRetrySatisfied = c.retryStatus === 'satisfied';

          return (
            <div
              key={c.criterionId}
              className={`rounded border transition-all duration-200 overflow-hidden ${
                c.isFirstDivergence
                  ? 'border-cadmium-amber/60 bg-surface-container-lowest shadow-[0_0_12px_rgba(230,126,34,0.1)]'
                  : isSelected
                  ? 'border-caliper-cyan bg-surface-container-lowest'
                  : 'border-outline bg-surface-container'
              }`}
            >
              {/* Criterion Card Header */}
              <div
                className="p-3 cursor-pointer select-none flex flex-col gap-1.5"
                onClick={() => toggleExpand(c.criterionId)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-caliper-cyan">
                      {c.criterionId}
                    </span>
                    {c.isFirstDivergence && (
                      <span className="font-mono text-[11px] bg-cadmium-amber/20 text-cadmium-amber border border-cadmium-amber/40 px-1.5 py-0.2 rounded font-bold">
                        FIRST DIVERGENCE
                      </span>
                    )}
                    {c.required && (
                      <span className="font-mono text-[11px] text-on-surface-variant border border-outline px-1 rounded">
                        REQ
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Score comparison pill */}
                    <div className="flex items-center gap-1 font-mono text-[11px]">
                      <span className="text-divergence-crimson line-through opacity-75">
                        {c.baselineScore.toFixed(1)}
                      </span>
                      <span className="text-outline">→</span>
                      <span className="text-transmission-emerald font-bold">
                        {c.retryScore.toFixed(1)} / {c.weight.toFixed(1)} PTS
                      </span>
                    </div>
                    {isExpanded ? (
                      <ChevronUp className="w-3.5 h-3.5 text-on-surface-variant" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5 text-on-surface-variant" />
                    )}
                  </div>
                </div>

                <div className="font-sans text-xs font-semibold text-on-surface">
                  {c.name}
                </div>

                <div className="font-sans text-[11px] text-on-surface-variant leading-relaxed line-clamp-2">
                  {c.observableIndicator}
                </div>

                {/* Status Badges Row */}
                <div className="flex items-center justify-between pt-1 border-t border-outline/50 mt-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] text-on-surface-variant">BASELINE:</span>
                    <span
                      className={`font-mono text-[11px] px-1.5 py-0.5 rounded font-bold ${
                        c.baselineStatus === 'satisfied'
                          ? 'bg-transmission-emerald/10 text-transmission-emerald border border-transmission-emerald/30'
                          : c.baselineStatus === 'partially_satisfied'
                          ? 'bg-cadmium-amber/10 text-cadmium-amber border border-cadmium-amber/30'
                          : c.baselineStatus === 'uncertain'
                          ? 'bg-surface-container-highest text-on-surface-variant border border-outline'
                          : 'bg-divergence-crimson/10 text-divergence-crimson border border-divergence-crimson/30'
                      }`}
                    >
                      {c.baselineStatus.toUpperCase()}
                    </span>

                    <span className="font-mono text-[11px] text-on-surface-variant ml-1">RETRY:</span>
                    <span className="font-mono text-[11px] px-1.5 py-0.5 rounded font-bold bg-transmission-emerald/10 text-transmission-emerald border border-transmission-emerald/30 flex items-center gap-0.5">
                      <CheckCircle2 className="w-2.5 h-2.5" />
                      SATISFIED
                    </span>
                  </div>

                  {/* Jump To Evidence Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (c.expertEvidenceSec) {
                        onTimeChange(c.expertEvidenceSec);
                      }
                    }}
                    className="flex items-center gap-1 font-mono text-[11px] text-cadmium-amber hover:underline"
                  >
                    <span>EVIDENCE</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </button>
                </div>
              </div>

              {/* Expandable Diagnostic Drawer */}
              {isExpanded && (
                <div className="px-3 pb-3 pt-1 border-t border-outline bg-surface-container-lowest/80 flex flex-col gap-2 text-[11px]">
                  {/* Divergence Observed */}
                  {c.feedback && (
                    <div className="bg-surface-container p-2 rounded border border-outline">
                      <div className="font-mono text-[11px] text-divergence-crimson font-bold flex items-center gap-1 mb-1">
                        <AlertTriangle className="w-3 h-3" />
                        DIVERGENCE OBSERVED:
                      </div>
                      <p className="text-on-surface-variant font-sans">
                        {c.feedback.what_differed}
                      </p>
                    </div>
                  )}

                  {/* Corrective Instruction */}
                  {c.feedback && (
                    <div className="bg-cadmium-amber/5 p-2 rounded border border-cadmium-amber/20">
                      <div className="font-mono text-[11px] text-cadmium-amber font-bold flex items-center gap-1 mb-1">
                        <ShieldCheck className="w-3 h-3" />
                        CORRECTIVE INSTRUCTION:
                      </div>
                      <p className="text-on-surface font-sans">
                        {c.feedback.corrective_advice}
                      </p>
                    </div>
                  )}

                  {/* Verified Retry Observation */}
                  {c.retryNotes && (
                    <div className="bg-transmission-emerald/5 p-2 rounded border border-transmission-emerald/20">
                      <div className="font-mono text-[11px] text-transmission-emerald font-bold flex items-center gap-1 mb-1">
                        <CheckCircle2 className="w-3 h-3" />
                        REPLAY RETRY OBSERVATION:
                      </div>
                      <p className="text-on-surface-variant font-sans">
                        {c.retryNotes}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer Diagnostic Summary */}
      <div className="p-3 bg-surface-container border-t border-outline text-[11px] font-mono text-on-surface-variant flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-transmission-emerald" />
          <span>3 / 3 CRITERIA SATISFIED</span>
        </div>
        <div className="text-caliper-cyan">
          ZERO-DEFECT CALIBRATION
        </div>
      </div>
    </div>
  );
};
