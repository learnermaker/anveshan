/** "Why this feedback?" progressive-disclosure block (K9-P2 §3.3 / K9-00 §5). */

import React from 'react';
import type { CaseView } from '../api/types';
import { pointNumber } from './StepsList';

interface WhyThisFeedbackProps {
  view: CaseView;
  claimIds: string[];
  measured?: string | null;
  aiWorded?: boolean;
  onShowSource?: (claimId: string) => void;
  defaultOpen?: boolean;
}

export function WhyThisFeedback({ view, claimIds, measured, aiWorded, onShowSource, defaultOpen = false }: WhyThisFeedbackProps) {
  const claims = view.package.claims;

  return (
    <details open={defaultOpen} className="text-xs mt-2">
      <summary className="text-xs text-caliper-cyan cursor-pointer select-none hover:underline">
        Why this feedback?
      </summary>
      <div className="mt-2 space-y-2.5 p-3 rounded-lg border border-outline/60 bg-surface-dim">
        {/* 1. From the source */}
        <div>
          <div className="text-[11px] font-mono uppercase text-on-surface-variant font-bold mb-1">From the source</div>
          {claimIds.length === 0 ? (
            <p className="text-on-surface-variant text-xs">
              This check comes from the skill's goal rather than a single step.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {claimIds.map((id) => {
                const claim = claims.find((c) => c.claim_id === id);
                const n = pointNumber(claims, id);
                if (!claim) return null;
                return (
                  <li key={id} className="flex items-start gap-2 text-xs">
                    <span className="text-[11px] font-mono text-cadmium-amber shrink-0 pt-0.5">Point {n ?? '?'}</span>
                    <span data-plain-exempt className="text-on-surface leading-relaxed flex-1">
                      {claim.statement}
                    </span>
                    {onShowSource && claim.evidence_refs[0] && (
                      <button
                        type="button"
                        className="text-[11px] font-mono text-caliper-cyan hover:underline shrink-0"
                        onClick={() => onShowSource(id)}
                      >
                        Show me
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* 2. What was measured */}
        {measured && (
          <div>
            <div className="text-[11px] font-mono uppercase text-on-surface-variant font-bold mb-1">What was measured</div>
            <p data-plain-exempt className="text-on-surface text-xs leading-relaxed">
              {measured}
            </p>
          </div>
        )}

        {/* 3. How it was scored */}
        <div>
          <div className="text-[11px] font-mono uppercase text-on-surface-variant font-bold mb-1">How it was scored</div>
          <p className="text-on-surface-variant text-xs">
            Scored by fixed rules from what was measured; the AI never sets a score.
          </p>
        </div>

        {/* 4. AI-worded advice */}
        {aiWorded && (
          <div>
            <p className="text-on-surface-variant text-xs">The advice was worded by AI from these findings.</p>
          </div>
        )}

        {/* Link to evidence page */}
        <div className="border-t border-outline/40 pt-2">
          <button
            type="button"
            className="text-[11px] font-mono text-caliper-cyan hover:underline"
            onClick={() => window.dispatchEvent(new CustomEvent('anveshan:go-evidence'))}
          >
            How we check results →
          </button>
        </div>
      </div>
    </details>
  );
}
