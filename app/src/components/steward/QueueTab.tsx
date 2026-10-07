/**
 * QueueTab: list of submitted and unchecked curated skills waiting for review (K9-P3 §3.4).
 */

import React, { useEffect, useState } from 'react';
import type { StewardQueueItem } from '../../api/types';
import { api } from '../../api/client';
import { ErrorNote, Spinner, btn } from '../../hero/ui';
import { fmtRelative } from './format';
import { ReviewDetail } from './ReviewDetail';

interface Props {
  onOpenSkill: (id: string) => void;
  onLibraryChanged: () => void;
  /** If set on mount, open this case directly in review */
  reviewingCaseId?: string | null;
  onClearReviewing: () => void;
}

export function QueueTab({ onOpenSkill, onLibraryChanged, reviewingCaseId, onClearReviewing }: Props) {
  const [items, setItems] = useState<StewardQueueItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [reviewing, setReviewing] = useState<string | null>(reviewingCaseId ?? null);

  useEffect(() => {
    setLoading(true);
    api.stewardQueue()
      .then(setItems)
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  if (reviewing) {
    return (
      <ReviewDetail
        caseId={reviewing}
        onBack={() => { setReviewing(null); onClearReviewing(); }}
        onOpenSkill={onOpenSkill}
        onLibraryChanged={() => {
          onLibraryChanged();
          setLoading(true);
          api.stewardQueue()
            .then(setItems)
            .catch(setError)
            .finally(() => setLoading(false));
        }}
      />
    );
  }

  if (loading) return <Spinner label="Loading queue…" />;
  if (error) return <ErrorNote error={error} />;
  if (!items) return null;

  if (items.length === 0) {
    return (
      <p className="text-sm text-on-surface-variant py-6 text-center">
        The queue is empty. New shared skills will appear here.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div
          key={item.case_id}
          className="rounded-xl border border-outline bg-surface-container-low/80 p-4 flex flex-wrap items-start justify-between gap-3"
        >
          <div className="space-y-1 min-w-0">
            <h3 data-plain-exempt className="font-semibold text-on-surface text-sm">{item.title}</h3>
            <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-on-surface-variant">
              <span className="font-mono">{item.kind === 'submission' ? 'Shared skill' : 'Featured skill, not checked'}</span>
              {item.credit_name && <span>by {item.credit_name}</span>}
              <span>{item.steps} steps</span>
              {item.submitted_at && <span>submitted {fmtRelative(item.submitted_at)}</span>}
            </div>
          </div>
          <button onClick={() => setReviewing(item.case_id)} className={btn.primary}>Review</button>
        </div>
      ))}
    </div>
  );
}
