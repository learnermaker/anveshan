/**
 * CheckStepsDialog: creator reviews, edits and removes AI-parsed steps (K9-P3 §2.3).
 */

import React, { useState } from 'react';
import { Pencil, Trash2, X } from 'lucide-react';
import type { CaseView } from '../../api/types';
import { api } from '../../api/client';
import { ErrorNote, btn } from '../../hero/ui';
import { useEscape } from '../../hero/useEscape';

interface Props {
  view: CaseView;
  isOpen: boolean;
  onClose: () => void;
  onViewChange: (v: CaseView) => void;
}

type RowState =
  | { kind: 'idle' }
  | { kind: 'editing'; text: string }
  | { kind: 'confirming-remove' }
  | { kind: 'busy' };

export function CheckStepsDialog({ view, isOpen, onClose, onViewChange }: Props) {
  useEscape(isOpen, onClose);
  const [rowStates, setRowStates] = useState<Record<string, RowState>>({});
  const [dialogError, setDialogError] = useState<unknown>(null);

  if (!isOpen) return null;

  const claims = view.package.claims;

  const setState = (claimId: string, s: RowState) =>
    setRowStates((prev) => ({ ...prev, [claimId]: s }));

  const getState = (claimId: string): RowState => rowStates[claimId] ?? { kind: 'idle' };

  const handleSave = async (claimId: string, text: string) => {
    if (!text.trim()) return;
    setState(claimId, { kind: 'busy' });
    setDialogError(null);
    try {
      const updated = await api.reviewCase(view.case_id, {
        action: 'revise_claim',
        reviewer: 'creator',
        note: '',
        claim_id: claimId,
        new_statement: text.trim(),
      });
      onViewChange(updated);
      setState(claimId, { kind: 'idle' });
    } catch (e) {
      setDialogError(e);
      setState(claimId, { kind: 'idle' });
    }
  };

  const handleRemove = async (claimId: string) => {
    setState(claimId, { kind: 'busy' });
    setDialogError(null);
    try {
      const updated = await api.reviewCase(view.case_id, {
        action: 'reject_claim',
        reviewer: 'creator',
        note: '',
        claim_id: claimId,
      });
      onViewChange(updated);
      setState(claimId, { kind: 'idle' });
    } catch (e) {
      setDialogError(e);
      setState(claimId, { kind: 'idle' });
    }
  };

  const handleApprove = async () => {
    setDialogError(null);
    try {
      const updated = await api.reviewCase(view.case_id, {
        action: 'approve',
        reviewer: 'creator',
        note: '',
      });
      onViewChange(updated);
      onClose();
    } catch (e) {
      setDialogError(e);
    }
  };

  const anyBusy = Object.values(rowStates).some((s) => s.kind === 'busy');

  return (
    <div
      className="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-4 bg-background/80 backdrop-blur-md overflow-y-auto"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="check-steps-title"
        className="w-full max-w-2xl rounded-xl border border-outline bg-surface-container shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-outline">
          <h2 id="check-steps-title" className="font-semibold text-on-surface">Check what the AI understood</h2>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            title="Close (Esc)"
            className="flex items-center gap-1 px-2 py-1 rounded text-on-surface-variant hover:text-on-surface"
          >
            <X className="w-5 h-5" aria-hidden="true" />
            <span className="text-xs font-mono">Close</span>
          </button>
        </div>

        <div className="p-5 space-y-4 overflow-y-auto max-h-[65vh]">
          <p className="text-sm text-on-surface-variant">
            These are the steps the AI found in your source. Check each one — edit anything that is wrong, and remove steps that shouldn't be there.
            Learners will be checked on these steps.
          </p>

          {claims.length === 0 && (
            <p className="text-sm text-on-surface-variant">No steps found in this skill.</p>
          )}

          <ol className="space-y-3">
            {claims.map((claim, idx) => {
              const rs = getState(claim.claim_id);
              const isAiReading = claim.is_observed === false;

              return (
                <li key={claim.claim_id} className="rounded-lg border border-outline bg-surface-dim p-3 space-y-2">
                  {rs.kind === 'editing' ? (
                    <div className="space-y-2">
                      <label htmlFor={`edit-${claim.claim_id}`} className="text-[11px] font-mono text-on-surface-variant">
                        Step {idx + 1}
                      </label>
                      <textarea
                        id={`edit-${claim.claim_id}`}
                        defaultValue={rs.text}
                        rows={2}
                        onChange={(e) =>
                          setState(claim.claim_id, { kind: 'editing', text: e.target.value })
                        }
                        className="w-full bg-surface-container border border-caliper-cyan rounded px-3 py-2 text-sm outline-none resize-none"
                        autoFocus
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            const text = (rs as { kind: 'editing'; text: string }).text;
                            if (text.trim()) void handleSave(claim.claim_id, text);
                          }}
                          disabled={!(rs as { kind: 'editing'; text: string }).text?.trim()}
                          className={btn.primary}
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setState(claim.claim_id, { kind: 'idle' })}
                          className={btn.secondary}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : rs.kind === 'confirming-remove' ? (
                    <div className="space-y-2">
                      <p className="text-sm text-on-surface">
                        Remove this step? Learners will no longer be checked on it.
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => void handleRemove(claim.claim_id)}
                          className={`${btn.primary} !bg-divergence-crimson hover:!bg-divergence-crimson/90`}
                        >
                          Remove
                        </button>
                        <button
                          onClick={() => setState(claim.claim_id, { kind: 'idle' })}
                          className={btn.secondary}
                        >
                          Keep
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-2 min-w-0">
                        <span className="font-mono text-[11px] text-on-surface-variant shrink-0 mt-0.5">{idx + 1}.</span>
                        <span data-plain-exempt className="text-sm text-on-surface leading-relaxed">
                          {claim.statement}
                        </span>
                        {isAiReading && (
                          <span className="shrink-0 inline-flex items-center px-1 py-0 rounded text-[11px] font-mono font-bold uppercase bg-cadmium-amber/10 text-cadmium-amber border border-cadmium-amber/30">
                            AI's reading
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        {rs.kind === 'busy' ? (
                          <span className="text-[11px] font-mono text-on-surface-variant">Saving…</span>
                        ) : (
                          <>
                            <button
                              onClick={() =>
                                setState(claim.claim_id, { kind: 'editing', text: claim.statement })
                              }
                              aria-label={`Edit step ${idx + 1}`}
                              className={btn.ghost}
                              disabled={anyBusy}
                            >
                              <Pencil className="w-3.5 h-3.5" aria-hidden="true" />
                            </button>
                            <button
                              onClick={() => setState(claim.claim_id, { kind: 'confirming-remove' })}
                              aria-label={`Remove step ${idx + 1}`}
                              className={`${btn.ghost} text-divergence-crimson hover:text-divergence-crimson/80`}
                              disabled={anyBusy}
                            >
                              <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
          </ol>

          <ErrorNote error={dialogError} />
        </div>

        <div className="px-5 py-4 border-t border-outline space-y-3">
          <p className="text-[11px] text-on-surface-variant">
            You can change these later. Each change creates a new version; learners always practise the latest one.
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => void handleApprove()}
              disabled={anyBusy}
              className={btn.primary}
            >
              Looks right
            </button>
            <button onClick={onClose} className={btn.secondary} disabled={anyBusy}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
