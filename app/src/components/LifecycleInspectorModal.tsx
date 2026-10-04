import React from 'react';
import {
  X,
  Compass,
  Layers,
  Cpu,
  CheckCircle2,
  FileText,
  UserCheck,
  Shield,
  Eye,
  ExternalLink,
} from 'lucide-react';
export type LifecycleStage = 'source' | 'knowledge' | 'practice' | 'transmission';
import type { TransmissionTelemetry } from '../data/adapter';

interface LifecycleInspectorModalProps {
  stage: LifecycleStage | null;
  onClose: () => void;
  telemetry: TransmissionTelemetry;
}

export const LifecycleInspectorModal: React.FC<LifecycleInspectorModalProps> = ({
  stage,
  onClose,
  telemetry,
}) => {
  if (!stage || stage === 'transmission') return null;

  const kp = telemetry.knowledgePackage;
  const task = telemetry.task;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-surface-container-low border border-outline rounded-xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-4 bg-surface-container border-b border-outline flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-cadmium-amber/10 border border-cadmium-amber/40 flex items-center justify-center text-cadmium-amber">
              {stage === 'source' && <Compass className="w-4 h-4" />}
              {stage === 'knowledge' && <Layers className="w-4 h-4" />}
              {stage === 'practice' && <Cpu className="w-4 h-4" />}
            </div>
            <div>
              <div className="font-mono text-xs font-bold text-on-surface uppercase tracking-wider">
                STAGE {stage === 'source' ? '01: CAPTURE & CONSENT' : stage === 'knowledge' ? '02: GROUNDED KNOWLEDGE PACKAGE' : '03: PRACTICE TASK SPECIFICATION'}
              </div>
              <div className="text-xs font-sans text-on-surface-variant">
                Upstream source evidence feeding the transmission instrument
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded bg-surface-container-highest hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-5 overflow-y-auto space-y-4">
          {/* STAGE 01: SOURCE */}
          {stage === 'source' && (
            <div className="space-y-4">
              {/* Reference replay fixture preview */}
              <div className="relative aspect-video rounded-lg overflow-hidden border border-outline bg-surface-container-lowest">
                <img
                  src="/assets/expert-reference.jpg"
                  alt="Micrometer reference replay fixture"
                  className="w-full h-full object-cover filter contrast-110"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-surface-container-lowest via-transparent to-surface-container-lowest/40" />
                <div className="absolute top-2 left-2 bg-surface-container-lowest/90 px-2 py-0.5 rounded font-mono text-[10px] text-transmission-emerald border border-outline flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-transmission-emerald animate-pulse" />
                  REFERENCE CAPTURE // REPLAY FIXTURE
                </div>
                <div className="absolute bottom-2 right-2 bg-surface-container-lowest/90 px-2 py-0.5 rounded font-mono text-[10px] text-cadmium-amber border border-outline">
                  SYNTHETIC FIXTURE &bull; CALIBRATION NOT VERIFIED
                </div>
              </div>

              <div className="bg-surface-container p-4 rounded-lg border border-outline space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-caliper-cyan">
                    REPLAY FIXTURE ASSET: replay_micrometer_zeroing.mp4
                  </span>
                  <span className="px-2 py-0.5 rounded bg-transmission-emerald/10 text-transmission-emerald border border-transmission-emerald/30 font-mono text-[10px]">
                    4K / 60FPS / DUAL STEREO
                  </span>
                </div>
                <p className="text-xs font-sans text-on-surface-variant leading-relaxed">
                  Replay fixture representing a controlled micrometer zeroing scenario. Media, identities, and calibration claims are illustrative engineering data unless explicitly replaced with authorized real evidence.
                </p>
              </div>

              {/* Consent & Review Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="bg-surface-container p-3 rounded border border-outline space-y-1">
                  <div className="font-mono text-[10px] text-transmission-emerald font-bold flex items-center gap-1">
                    <UserCheck className="w-3.5 h-3.5" />
                    FIXTURE SOURCE METADATA:
                  </div>
                  <div className="text-xs font-medium text-on-surface">
                    Contributor: {kp.consent.contributor_name}
                  </div>
                  <div className="text-[11px] text-on-surface-variant">
                    Scope: {kp.consent.consent_scope} &bull; Revocable: {kp.consent.revocable ? 'YES' : 'NO'}
                  </div>
                  <div className="text-[10px] font-mono text-on-surface-variant">
                    Timestamp: {kp.consent.granted_at}
                  </div>
                </div>

                <div className="bg-surface-container p-3 rounded border border-outline space-y-1">
                  <div className="font-mono text-[10px] text-caliper-cyan font-bold flex items-center gap-1">
                    <Shield className="w-3.5 h-3.5" />
                    REVIEW METADATA:
                  </div>
                  <div className="text-xs font-medium text-on-surface">
                    Reviewer: {kp.expert_review?.reviewer_name ?? 'Not supplied'}
                  </div>
                  <div className="text-[11px] text-transmission-emerald font-mono">
                    STATUS: {(kp.expert_review?.status ?? 'not supplied').toUpperCase()}
                  </div>
                  <div className="text-[10px] font-sans text-on-surface-variant">
                    &ldquo;{kp.expert_review?.notes ?? 'No human review note is present in this replay fixture.'}&rdquo;
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STAGE 02: KNOWLEDGE */}
          {stage === 'knowledge' && (
            <div className="space-y-4">
              <div className="bg-surface-container p-3 rounded border border-outline">
                <div className="font-mono text-xs font-bold text-caliper-cyan mb-1">
                  PACKAGE ID: {kp.package_id} &bull; SKILL: {kp.skill_id}
                </div>
                <h3 className="font-serif text-lg font-bold text-on-surface">{kp.title}</h3>
                <p className="text-xs font-sans text-on-surface-variant mt-1 leading-relaxed">
                  {kp.summary}
                </p>
              </div>

              <div className="space-y-2">
                <div className="font-mono text-xs text-on-surface-variant uppercase">
                  GROUNDED CLAIMS & EVIDENCE REFS ({kp.claims.length}):
                </div>
                {kp.claims.map((claim) => (
                  <div key={claim.claim_id} className="bg-surface-container p-3 rounded border border-outline space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-cadmium-amber">
                        {claim.claim_id} ({claim.claim_type.toUpperCase()})
                      </span>
                      <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-transmission-emerald/10 text-transmission-emerald border border-transmission-emerald/30">
                        CONFIDENCE: {(claim.evidence_refs[0]?.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-xs font-sans text-on-surface font-medium">
                      {claim.statement}
                    </p>
                    {claim.evidence_refs.map((ev) => (
                      <div key={ev.evidence_id} className="bg-surface-container-lowest p-2 rounded text-[10px] font-mono text-on-surface-variant flex items-center justify-between">
                        <span>
                          [{ev.modality.toUpperCase()}] {ev.cue_excerpt}
                        </span>
                        <span className="text-caliper-cyan">
                          {ev.start_sec}s - {ev.end_sec}s
                        </span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* STAGE 03: PRACTICE */}
          {stage === 'practice' && (
            <div className="space-y-4">
              {/* Authentic Apprentice Capture Preview */}
              <div className="relative aspect-video rounded-lg overflow-hidden border border-outline bg-surface-container-lowest">
                <img
                  src="/assets/learner-attempt.jpg"
                  alt="Learner replay fixture practice capture"
                  className="w-full h-full object-cover filter contrast-110"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-surface-container-lowest via-transparent to-surface-container-lowest/40" />
                <div className="absolute top-2 left-2 bg-surface-container-lowest/90 px-2 py-0.5 rounded font-mono text-[10px] text-caliper-cyan border border-outline flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-caliper-cyan animate-pulse" />
                  APPRENTICE TRIAL FEED // ATT-BASE-001 &bull; ATT-RETRY-001
                </div>
                <div className="absolute bottom-2 right-2 bg-surface-container-lowest/90 px-2 py-0.5 rounded font-mono text-[10px] text-on-surface-variant border border-outline">
                  MARCUS VANCE &bull; BENCH 04 TELEMETRY
                </div>
              </div>

              <div className="bg-surface-container p-4 rounded border border-outline space-y-2">
                <div className="font-mono text-xs font-bold text-caliper-cyan">
                  PRACTICE TASK ID: {task.task_id}
                </div>
                <h3 className="font-serif text-lg font-bold text-on-surface">{task.title}</h3>
                <p className="text-xs font-sans text-on-surface-variant leading-relaxed">
                  {task.instructions}
                </p>
              </div>

              {/* Task Execution Constraints */}
              {task.constraints && task.constraints.length > 0 && (
                <div className="space-y-2">
                  <div className="font-mono text-xs text-on-surface-variant uppercase">
                    EXECUTION CONSTRAINTS ({task.constraints.length}):
                  </div>
                  {task.constraints.map((c, idx) => (
                    <div key={idx} className="bg-surface-container p-3 rounded border border-outline flex items-center justify-between text-xs">
                      <div>
                        <span className="font-mono text-[10px] text-cadmium-amber uppercase font-bold mr-2">
                          [{c.constraint_type.toUpperCase()}]
                        </span>
                        <span className="font-sans text-on-surface">{c.description}</span>
                      </div>
                      {c.value && (
                        <span className="font-mono text-[10px] text-caliper-cyan shrink-0">
                          LIMIT: {c.value}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Target Criteria */}
              {task.target_criteria_ids && task.target_criteria_ids.length > 0 && (
                <div className="bg-surface-container p-3 rounded border border-outline flex items-center justify-between">
                  <span className="font-mono text-xs text-on-surface-variant uppercase">
                    TARGET CRITERIA:
                  </span>
                  <div className="flex items-center gap-1.5">
                    {task.target_criteria_ids.map((cid) => (
                      <span key={cid} className="font-mono text-[10px] px-2 py-0.5 rounded bg-caliper-cyan/10 text-caliper-cyan border border-caliper-cyan/30 font-bold">
                        {cid}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-3 bg-surface-container border-t border-outline flex items-center justify-between">
          <div className="font-mono text-[10px] text-on-surface-variant">
            ANVESHAN REPLAY EVIDENCE CHAIN &bull; CASE-001
          </div>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded bg-surface-container-highest hover:bg-surface-container-high border border-outline text-xs font-mono text-on-surface transition-colors"
          >
            RETURN TO TRANSMISSION
          </button>
        </div>
      </div>
    </div>
  );
};
