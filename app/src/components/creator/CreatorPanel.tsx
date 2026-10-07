/**
 * CreatorPanel: the "Your skill" panel shown to skill owners in the source view (K9-P3 §2.2).
 * Rendered as ownerSlot in HeroSourceView.
 */

import React, { useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import type { CaseView, LibraryRecord } from '../../api/types';
import { api } from '../../api/client';
import { Badge, ErrorNote, Panel, ReviewBadge, btn } from '../../hero/ui';
import { LIBRARY_STATUS_HELP, LIBRARY_STATUS_LABEL } from '../../copy/plain';
import { CheckStepsDialog } from './CheckStepsDialog';
import { PublishDialog } from './PublishDialog';
import { InsightsDialog } from '../insights/InsightsDialog';

interface Props {
  view: CaseView;
  onViewChange: (v: CaseView) => void;
  onPractise: () => void;
}

const STATUS_TONE: Record<string, 'muted' | 'amber' | 'emerald' | 'crimson'> = {
  private: 'muted',
  submitted: 'amber',
  published: 'emerald',
  returned: 'amber',
  rejected: 'crimson',
  unlisted: 'muted',
};

export function CreatorPanel({ view, onViewChange, onPractise }: Props) {
  const access = view.access!;
  const status = access.library_status;

  const [checkOpen, setCheckOpen] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [insightsOpen, setInsightsOpen] = useState(false);
  const [withdrawBusy, setWithdrawBusy] = useState(false);
  const [withdrawConfirm, setWithdrawConfirm] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const isChecked = view.review_status === 'approved' || view.review_status === 'revised';
  const checkDone = isChecked;
  const submitDone = status === 'submitted' || status === 'published';

  const handleWithdraw = async () => {
    setWithdrawBusy(true);
    setError(null);
    try {
      await api.withdrawFromLibrary(view.case_id);
      const updated = await api.getCase(view.case_id);
      onViewChange(updated);
    } catch (e) {
      setError(e);
    } finally {
      setWithdrawBusy(false);
      setWithdrawConfirm(false);
    }
  };

  const handleSubmitted = async (_rec: LibraryRecord) => {
    setPublishOpen(false);
    const updated = await api.getCase(view.case_id);
    onViewChange(updated);
  };

  return (
    <>
      <Panel kicker="Your skill" className="mb-2">
        <div className="space-y-3">
          {/* Status */}
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <Badge tone={STATUS_TONE[status] ?? 'muted'}>
                {LIBRARY_STATUS_LABEL[status]}
              </Badge>
              <ReviewBadge status={view.review_status} own />
            </div>
            <p className="text-[11px] text-on-surface-variant">{LIBRARY_STATUS_HELP[status]}</p>
          </div>

          {/* Steward note */}
          {access.steward_note && (
            <blockquote className="border-l-2 border-cadmium-amber/50 pl-3 text-[11px] text-on-surface-variant italic">
              {access.steward_note}
            </blockquote>
          )}

          {/* Checklist */}
          <ol className="space-y-2">
            {/* Step 1: Check */}
            <li className="flex items-start gap-2">
              {checkDone ? (
                <CheckCircle2 className="w-4 h-4 text-transmission-emerald shrink-0 mt-0.5" aria-hidden="true" />
              ) : (
                <div className="w-4 h-4 rounded-full border-2 border-outline shrink-0 mt-0.5" aria-hidden="true" />
              )}
              <div className="space-y-1 min-w-0">
                <div className="text-sm text-on-surface font-medium">Check what the AI understood</div>
                <button
                  onClick={() => setCheckOpen(true)}
                  className={btn.secondary}
                >
                  {checkDone ? 'Review again' : 'Check steps'}
                </button>
              </div>
            </li>

            {/* Step 2: Practise (optional) */}
            <li className="flex items-start gap-2">
              <div className="w-4 h-4 rounded-full border-2 border-outline shrink-0 mt-0.5" aria-hidden="true" />
              <div className="space-y-1 min-w-0">
                <div className="text-sm text-on-surface font-medium">Try it yourself (optional)</div>
                <button onClick={onPractise} className={btn.secondary}>Practise</button>
              </div>
            </li>

            {/* Step 3: Publish */}
            <li className="flex items-start gap-2">
              {submitDone ? (
                <CheckCircle2 className="w-4 h-4 text-transmission-emerald shrink-0 mt-0.5" aria-hidden="true" />
              ) : (
                <div className="w-4 h-4 rounded-full border-2 border-outline shrink-0 mt-0.5" aria-hidden="true" />
              )}
              <div className="space-y-1 min-w-0">
                <div className="text-sm text-on-surface font-medium">Publish to the library</div>
                {access.can_submit || status === 'returned' ? (
                  <button
                    onClick={() => setPublishOpen(true)}
                    className={btn.primary}
                  >
                    {status === 'returned' ? 'Fix and send again' : 'Publish…'}
                  </button>
                ) : status !== 'submitted' && status !== 'published' ? (
                  <div className="space-y-1">
                    <button disabled className={btn.primary}>Publish…</button>
                    {access.submit_blockers.length > 0 && (
                      <ul className="text-[11px] text-on-surface-variant space-y-0.5">
                        {access.submit_blockers.map((b, i) => <li key={i}>{b}</li>)}
                      </ul>
                    )}
                  </div>
                ) : null}
              </div>
            </li>
          </ol>

          {/* Status-specific actions */}
          {(status === 'submitted' || status === 'published') && (
            <div className="flex flex-wrap gap-2 pt-1">
              {status === 'published' && (
                <button onClick={() => setInsightsOpen(true)} className={btn.primary}>
                  See how learners are doing
                </button>
              )}
              {withdrawConfirm ? (
                <div className="space-y-2">
                  <p className="text-[11px] text-on-surface-variant">
                    {status === 'published'
                      ? 'Remove it from the library? Learners who already started can finish.'
                      : 'Withdraw from review? It becomes private again.'}
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => void handleWithdraw()}
                      disabled={withdrawBusy}
                      className={`${btn.secondary} !border-divergence-crimson !text-divergence-crimson`}
                    >
                      {withdrawBusy ? 'Withdrawing…' : 'Confirm'}
                    </button>
                    <button onClick={() => setWithdrawConfirm(false)} className={btn.secondary}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setWithdrawConfirm(true)}
                  className={btn.secondary}
                >
                  {status === 'published' ? 'Make private' : 'Withdraw'}
                </button>
              )}
            </div>
          )}

          <ErrorNote error={error} />
        </div>
      </Panel>

      <CheckStepsDialog
        view={view}
        isOpen={checkOpen}
        onClose={() => setCheckOpen(false)}
        onViewChange={onViewChange}
      />

      <PublishDialog
        view={view}
        isOpen={publishOpen}
        onClose={() => setPublishOpen(false)}
        onSubmitted={(rec) => void handleSubmitted(rec)}
      />

      {insightsOpen && (
        <InsightsDialog
          caseId={view.case_id}
          title={view.title}
          isOpen={insightsOpen}
          onClose={() => setInsightsOpen(false)}
        />
      )}
    </>
  );
}
