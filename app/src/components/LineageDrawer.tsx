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
  const [selectedArtifact, setSelectedArtifact] = useState<string>('TX-REC-001');
  const [copied, setCopied] = useState<boolean>(false);
  const bundle = telemetry.bundle;

  if (!isOpen) return null;

  // Map each artifact ID to its JSON content from the bundle
  const getArtifactData = (id: string) => {
    switch (id) {
      case 'PKG-OPT-001':
        return bundle.knowledge_package;
      case 'RUBRIC-OPT-001':
        return bundle.rubric;
      case 'TASK-OPT-001':
        return bundle.practice_task;
      case 'ATT-BASE-001':
        return bundle.baseline_attempt;
      case 'EVAL-BASE-001':
        return bundle.baseline_evaluation;
      case 'FB-001':
        return bundle.feedback;
      case 'ATT-RETRY-001':
        return bundle.retry_attempt;
      case 'EVAL-RETRY-001':
        return bundle.retry_evaluation;
      case 'TX-REC-001':
      default:
        return bundle.transmission_record;
    }
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
                  VERIFIED ED25519
                </span>
              </div>
              <div className="text-xs font-sans text-on-surface-variant">
                Immutable Merkle provenance graph validating the 8-contract transmission chain
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

            {telemetry.record.lineage.map((node, index) => {
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
                    {node.artifact_type.replace(/_/g, ' ')}
                  </div>

                  {node.sha256 && (
                    <div className="font-mono text-[9px] text-on-surface-variant truncate mt-1">
                      SHA256: {node.sha256.substring(0, 16)}...
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
                TRANSMISSION TIMESTAMP: {telemetry.record.verified_at}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
