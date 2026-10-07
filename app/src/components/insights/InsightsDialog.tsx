/**
 * InsightsDialog: accessible modal wrapping InsightsPanel (K9-P3 §2.5).
 */

import React from 'react';
import { X } from 'lucide-react';
import { useEscape } from '../../hero/useEscape';
import { InsightsPanel } from './InsightsPanel';

interface Props {
  caseId: string;
  title?: string;
  isOpen: boolean;
  onClose: () => void;
}

export function InsightsDialog({ caseId, title, isOpen, onClose }: Props) {
  useEscape(isOpen, onClose);
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-4 bg-background/80 backdrop-blur-md overflow-y-auto"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="insights-dialog-title"
        className="w-full max-w-xl rounded-xl border border-outline bg-surface-container shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-outline">
          <h2 id="insights-dialog-title" className="font-semibold text-on-surface text-sm">
            How learners are doing{title ? `: ${title}` : ''}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close insights"
            title="Close (Esc)"
            className="flex items-center gap-1 px-2 py-1 rounded text-on-surface-variant hover:text-on-surface"
          >
            <X className="w-5 h-5" aria-hidden="true" />
            <span className="text-xs font-mono">Close</span>
          </button>
        </div>
        <div className="p-5 overflow-y-auto max-h-[75vh]">
          <InsightsPanel caseId={caseId} title={title} />
        </div>
      </div>
    </div>
  );
}
