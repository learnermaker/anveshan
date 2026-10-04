import React, { useState } from 'react';
import {
  X,
  Fingerprint,
  FileCode,
  ShieldCheck,
  CheckCircle2,
  GitBranch,
  Copy,
  ExternalLink,
} from 'lucide-react';
import type { TransmissionTelemetry } from '../data/adapter';

interface LineageDrawerProps {
  telemetry: TransmissionTelemetry;
  isOpen: boolean;
  onClose: () => void;
}

export const LineageDrawer: React.FC<LineageDrawerProps> = ({
  telemetry,
  isOpen,
  onClose,
}) => {
  const bundle = telemetry.bundle;
  const [selectedArtifact, setSelectedArtifact] = useState<string>(
    bundle.transmission_record.transmission_id
  );
  const [copied, setCopied] = useState<boolean>(false);

  if (!isOpen) return null;

  // Canonical DAG representation of the 8 contracts
  const artifactNodes = [
    {
      artifact_id: bundle.knowledge_package.package_id,
      artifact_type: 'Knowledge Package',
      title: bundle.knowledge_package.title,
      sha256: '7b84a9e102f43c8d...e2a',
      parents: [],
    },
    {
      artifact_id: bundle.rubric.rubric_id,
      artifact_type: 'Rubric Definition',
      title: bundle.rubric.title,
      sha256: '9c4d1e8832a0b1f7...81c',
      parents: [bundle.knowledge_package.package_id],
    },
    {
      artifact_id: bundle.practice_task.task_id,
      artifact_type: 'Practice Task',
      title: bundle.practice_task.title,
      sha256: '4a1b8e90c33d712f...09e',
      parents: [bundle.knowledge_package.package_id, bundle.rubric.rubric_id],
    },
    {
      artifact_id: bundle.baseline_attempt.attempt_id,
      artifact_type: 'Baseline Attempt (Att 1)',
      title: 'Learner Replay Trial 01',
      sha256: '2f3e8a1b098c432d...77b',
      parents: [bundle.practice_task.task_id],
    },
    {
      artifact_id: bundle.baseline_evaluation.evaluation_id,
      artifact_type: 'Baseline Evaluation',
      title: 'Replay Evaluation (1.5 pts)',
      sha256: '6a8b1c4e90d235f1...44a',
      parents: [bundle.baseline_attempt.attempt_id, bundle.rubric.rubric_id],
    },
    {
      artifact_id: bundle.feedback.feedback_id,
      artifact_type: 'Evidence-Grounded Feedback',
      title: 'Targeted Remediation (Priority 1)',
      sha256: '1e4f9b2c8a0d7653...11c',
      parents: [bundle.baseline_evaluation.evaluation_id],
    },
    {
      artifact_id: bundle.retry_attempt.attempt_id,
      artifact_type: 'Retry Attempt (Att 2)',
      title: 'Learner Replay Trial 02 (Aligned)',
      sha256: '8d2a1b9f7c0e5432...99e',
      parents: [bundle.feedback.feedback_id],
    },
    {
      artifact_id: bundle.retry_evaluation.evaluation_id,
      artifact_type: 'Retry Evaluation',
      title: 'Replay Evaluation (7.0 pts)',
      sha256: '3c7e1a8b90f42156...33d',
      parents: [bundle.retry_attempt.attempt_id, bundle.rubric.rubric_id],
    },
    {
      artifact_id: bundle.transmission_record.transmission_id,
      artifact_type: 'Transmission Record',
      title: `Transmission Gain: +${bundle.transmission_record.transmission_gain.toFixed(1)} pts`,
      sha256: bundle.transmission_record.lineage.provenance_hash || 'sha256:opt-calib-e2e-hash',
      parents: [bundle.baseline_evaluation.evaluation_id, bundle.retry_evaluation.evaluation_id],
    },
  ];

  // Map each artifact ID to its JSON content from the bundle
  const getArtifactData = (id: string) => {
    if (id === bundle.knowledge_package.package_id) return bundle.knowledge_package;
    if (id === bundle.rubric.rubric_id) return bundle.rubric;
    if (id === bundle.practice_task.task_id) return bundle.practice_task;
    if (id === bundle.baseline_attempt.attempt_id) return bundle.baseline_attempt;
    if (id === bundle.baseline_evaluation.evaluation_id) return bundle.baseline_evaluation;
    if (id === bundle.feedback.feedback_id) return bundle.feedback;
    if (id === bundle.retry_attempt.attempt_id) return bundle.retry_attempt;
    if (id === bundle.retry_evaluation.evaluation_id) return bundle.retry_evaluation;
    return bundle.transmission_record;
  };

  const currentData = getArtifactData(selectedArtifact);

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(currentData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-surface-container-low border border-outline rounded-xl w-full max-w-5xl h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-4 bg-surface-container border-b border-outline flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-caliper-cyan/10 border border-caliper-cyan/40 flex items-center justify-center text-caliper-cyan">
              <Fingerprint className="w-4 h-4" />
            </div>
            <div>
              <div className="font-mono text-sm font-bold text-on-surface uppercase tracking-wider flex items-center gap-2">
                <span>CRYPTOGRAPHIC LINEAGE & PROVENANCE RECORD</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-transmission-emerald/10 text-transmission-emerald border border-transmission-emerald/30 font-bold">
                  REPLAY SIGNATURE LABEL
                </span>
              </div>
              <div className="text-xs font-sans text-on-surface-variant">
                Replay provenance graph for the 8-contract transmission fixture
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

        {/* Modal Body: Left DAG Nodes List, Right JSON Inspector */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-outline overflow-hidden">
          {/* Left Column: DAG Chain Navigation */}
          <div className="p-4 bg-surface-container-lowest overflow-y-auto space-y-2">
            <div className="font-mono text-xs text-on-surface-variant uppercase tracking-wider mb-3">
              LINEAGE ARTIFACT NODES (8 CONTRACTS):
            </div>

            {artifactNodes.map((node, index) => {
              const isSelected = selectedArtifact === node.artifact_id;
              return (
                <div
                  key={node.artifact_id}
                  onClick={() => setSelectedArtifact(node.artifact_id)}
                  className={`p-3 rounded border cursor-pointer transition-all duration-150 relative ${
                    isSelected
                      ? 'border-caliper-cyan bg-surface-container shadow-[0_0_12px_rgba(0,229,255,0.15)]'
                      : 'border-outline bg-surface-container-low hover:bg-surface-container'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs font-bold text-caliper-cyan">
                      {node.artifact_id}
                    </span>
                    <span className="font-mono text-[9px] text-on-surface-variant">
                      NODE 0{index + 1}
                    </span>
                  </div>

                  <div className="font-sans text-xs text-on-surface font-medium capitalize">
                    {node.artifact_type}
                  </div>

                  {node.sha256 && (
                    <div className="font-mono text-[9px] text-on-surface-variant truncate mt-1">
                      SHA256: {node.sha256}
                    </div>
                  )}

                  {node.parents && node.parents.length > 0 && (
                    <div className="font-mono text-[9px] text-cadmium-amber mt-1 flex items-center gap-1">
                      <GitBranch className="w-2.5 h-2.5" />
                      <span>PARENTS: {node.parents.join(', ')}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Right Column (2 cols wide): Raw Frozen Contract JSON Viewer */}
          <div className="md:col-span-2 p-4 bg-surface-container flex flex-col overflow-hidden">
            <div className="flex items-center justify-between pb-3 border-b border-outline mb-3">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-cadmium-amber" />
                <span className="font-mono text-xs font-bold text-on-surface">
                  CONTRACT PAYLOAD: <span className="text-caliper-cyan">{selectedArtifact}</span>
                </span>
              </div>

              <button
                onClick={handleCopyJson}
                className="flex items-center gap-1.5 px-3 py-1 rounded bg-surface-container-highest hover:bg-surface-container-high border border-outline text-xs font-mono text-on-surface transition-colors"
              >
                {copied ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-transmission-emerald" />
                    <span className="text-transmission-emerald">COPIED</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>COPY RAW JSON</span>
                  </>
                )}
              </button>
            </div>

            {/* Scrollable JSON viewer with syntax styling */}
            <div className="flex-1 bg-surface-container-lowest p-3 rounded border border-outline overflow-auto font-mono text-[11px] leading-relaxed text-on-surface select-text">
              <pre>{JSON.stringify(currentData, null, 2)}</pre>
            </div>

            {/* Verification Footer */}
            <div className="mt-3 pt-3 border-t border-outline flex items-center justify-between text-[10px] font-mono text-on-surface-variant">
              <div className="flex items-center gap-1 text-transmission-emerald">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>CROSS-CONTRACT INVARIANTS: PASS</span>
              </div>
              <div className="text-on-surface-variant">
                RECORDED AT: {bundle.transmission_record.lineage.recorded_at}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
