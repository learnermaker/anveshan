/** One-sentence trust line for the learner surface (K9-P2 §3.1). */

import React from 'react';
import { Info } from 'lucide-react';
import { trustLine } from '../copy/plain';

interface TrustLineProps {
  view: {
    runtime_label: string;
    review_status: string;
    access?: { credit_name: string | null; collection: string };
  };
  className?: string;
}

export function TrustLine({ view, className }: TrustLineProps) {
  const text = trustLine({
    runtime_label: view.runtime_label,
    review_status: view.review_status,
    credit_name: view.access?.credit_name,
    collection: view.access?.collection,
  });
  const isSynthetic = view.runtime_label === 'SYNTHETIC';
  return (
    <p className={`flex items-start gap-1.5 text-sm ${isSynthetic ? 'text-divergence-crimson' : 'text-on-surface-variant'} ${className ?? ''}`}>
      <Info className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
      {text}
    </p>
  );
}
