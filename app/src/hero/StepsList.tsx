/** "What you'll learn" — ordered list of steps with Show me links (K9-P2 §3.2). */

import React from 'react';
import { Eye } from 'lucide-react';
import type { KnowledgeClaim } from '../types/contracts';
import { VerificationBadge } from './ui';
import { claimVerification, fmtTime } from './locators';

interface StepsListProps {
  claims: KnowledgeClaim[];
  activeId: string | null;
  onShow: (claimId: string) => void;
}

export function StepsList({ claims, activeId, onShow }: StepsListProps) {
  return (
    <ol className="space-y-2">
      {claims.map((claim, i) => {
        const verif = claimVerification(claim);
        const ev = claim.evidence_refs[0];
        const isActive = claim.claim_id === activeId;
        return (
          <li
            key={claim.claim_id}
            className={`p-2.5 rounded-lg border transition-colors ${
              isActive ? 'border-cadmium-amber bg-cadmium-amber/10' : 'border-outline/60 bg-surface-dim'
            }`}
          >
            <div className="flex items-start gap-2">
              <span className="text-[11px] font-mono text-cadmium-amber font-bold shrink-0 pt-0.5">{i + 1}.</span>
              <div className="flex-1 space-y-1 min-w-0">
                <span className="text-xs text-on-surface leading-relaxed" data-plain-exempt>
                  {claim.statement}
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  {verif === 'inferred' && <VerificationBadge state="inferred" />}
                  {ev?.start_sec != null && (
                    <span className="text-[11px] font-mono text-on-surface-variant">at {fmtTime(ev.start_sec)}</span>
                  )}
                  {ev && (
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 text-[11px] font-mono text-caliper-cyan hover:underline"
                      aria-label={`Show step ${i + 1} in the source`}
                      onClick={() => onShow(claim.claim_id)}
                    >
                      <Eye className="w-3.5 h-3.5" aria-hidden="true" /> Show me
                    </button>
                  )}
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/** 1-based position of a claim in the list, or null when not found. */
export function pointNumber(claims: KnowledgeClaim[], claimId: string): number | null {
  const idx = claims.findIndex((c) => c.claim_id === claimId);
  return idx >= 0 ? idx + 1 : null;
}
