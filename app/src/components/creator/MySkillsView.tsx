/**
 * MySkillsView: the creator's "My skills" page (K9-P3 §2.1).
 * Shows all cases the current visitor owns, with status and next-action buttons.
 */

import React, { useState } from 'react';
import { Share2 } from 'lucide-react';
import type { CaseSummary, HealthResponse } from '../../api/types';
import { ErrorNote, ReviewBadge, Spinner, btn } from '../../hero/ui';
import { LIBRARY_STATUS_HELP, LIBRARY_STATUS_LABEL } from '../../copy/plain';
import { InsightsDialog } from '../insights/InsightsDialog';

interface Props {
  cases: CaseSummary[] | null;
  loading: boolean;
  error: unknown;
  health: HealthResponse | null;
  onRefresh: () => void;
  onOpen: (caseId: string) => void;
  onCreate: () => void;
}

const STATUS_CHIP_CLASS: Record<string, string> = {
  private: 'bg-surface-dim text-on-surface-variant border-outline',
  submitted: 'bg-cadmium-amber/10 text-cadmium-amber border-cadmium-amber/30',
  published: 'bg-transmission-emerald/10 text-transmission-emerald border-transmission-emerald/30',
  returned: 'bg-cadmium-amber/10 text-cadmium-amber border-cadmium-amber/30',
  rejected: 'bg-divergence-crimson/10 text-divergence-crimson border-divergence-crimson/30',
  unlisted: 'bg-surface-dim text-on-surface-variant border-outline',
};

interface CardProps {
  c: CaseSummary;
  isDerivedUpload: boolean;
  onOpen: (id: string) => void;
  onShowInsights: (c: CaseSummary) => void;
}

function SkillStatusCard({ c, isDerivedUpload, onOpen, onShowInsights }: CardProps) {
  const access = c.access!;
  const status = access.library_status;
  const chipCls = STATUS_CHIP_CLASS[status] ?? STATUS_CHIP_CLASS.private;

  return (
    <div className="rounded-xl border border-outline bg-surface-container-low/80 p-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-0.5 min-w-0">
          <h3 data-plain-exempt className="font-semibold text-on-surface text-sm leading-snug">{c.title}</h3>
          {access.credit_name && (
            <p className="text-[11px] text-on-surface-variant">by {access.credit_name}</p>
          )}
        </div>
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase border whitespace-nowrap ${chipCls}`}>
          {LIBRARY_STATUS_LABEL[status]}
        </span>
      </div>

      <p className="text-[11px] text-on-surface-variant">{LIBRARY_STATUS_HELP[status]}</p>

      {isDerivedUpload && (
        <p className="text-[11px] text-on-surface-variant italic">
          Uploads made from a featured skill stay private.
        </p>
      )}

      {access.steward_note && (
        <blockquote className="border-l-2 border-cadmium-amber/50 pl-3 text-[11px] text-on-surface-variant italic">
          {access.steward_note}
        </blockquote>
      )}

      <ReviewBadge status={c.review_status} />

      <div className="pt-1">
        {status === 'private' && (
          <button onClick={() => onOpen(c.case_id)} className={btn.secondary}>Open and check</button>
        )}
        {status === 'submitted' && (
          <button onClick={() => onOpen(c.case_id)} className={btn.secondary}>Open</button>
        )}
        {status === 'returned' && (
          <button onClick={() => onOpen(c.case_id)} className={btn.primary}>Fix and send again</button>
        )}
        {status === 'published' && (
          <button onClick={() => onShowInsights(c)} className={btn.primary}>See how learners are doing</button>
        )}
        {(status === 'rejected' || status === 'unlisted') && (
          <button onClick={() => onOpen(c.case_id)} className={btn.secondary}>Open</button>
        )}
      </div>
    </div>
  );
}

export function MySkillsView({ cases, loading, error, health, onRefresh, onOpen, onCreate }: Props) {
  const [insightsCase, setInsightsCase] = useState<CaseSummary | null>(null);

  if (loading && !cases) {
    return <Spinner label="Loading your skills…" />;
  }
  if (error) {
    return (
      <div className="space-y-3">
        <ErrorNote error={error} />
        <button onClick={onRefresh} className={btn.secondary}>Try again</button>
      </div>
    );
  }

  const owned = (cases ?? []).filter((c) => c.access?.owner);
  const composed = owned.filter((c) => c.composed && !c.derived_from);
  const derivedUploads = owned.filter((c) => c.derived_from);

  const ttlHours = health?.data_ttl_hours;

  return (
    <div className="flex flex-col gap-6 w-full max-w-3xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-serif text-3xl text-on-surface">My skills</h1>
        <button onClick={onCreate} className={btn.primary}>
          <Share2 className="w-3.5 h-3.5" aria-hidden="true" />
          Share a new skill
        </button>
      </div>

      {/* Explanation */}
      <p className="text-sm text-on-surface-variant">
        Skills you create are private to this browser until you publish them.
        {ttlHours != null && ttlHours > 0 && (
          <> Private skills are kept for about {ttlHours} hours on this demo.</>
        )}
      </p>

      {/* Empty state */}
      {owned.length === 0 && (
        <div className="flex flex-col items-center gap-4 py-16 text-center text-on-surface-variant">
          <p className="text-sm max-w-sm">
            You haven't shared any skills yet. Upload a photo, video or audio of something you know how to do.
          </p>
          <button onClick={onCreate} className={btn.primary}>
            <Share2 className="w-3.5 h-3.5" aria-hidden="true" />
            Share a new skill
          </button>
        </div>
      )}

      {/* Composed skills */}
      {composed.length > 0 && (
        <div className="space-y-3">
          {composed.map((c) => (
            <SkillStatusCard
              key={c.case_id}
              c={c}
              isDerivedUpload={false}
              onOpen={onOpen}
              onShowInsights={(cas) => setInsightsCase(cas)}
            />
          ))}
        </div>
      )}

      {/* Derived uploads */}
      {derivedUploads.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-on-surface-variant font-mono uppercase tracking-wider">
            Your uploads of featured skills
          </h2>
          {derivedUploads.map((c) => (
            <SkillStatusCard
              key={c.case_id}
              c={c}
              isDerivedUpload
              onOpen={onOpen}
              onShowInsights={(cas) => setInsightsCase(cas)}
            />
          ))}
        </div>
      )}

      {insightsCase && (
        <InsightsDialog
          caseId={insightsCase.case_id}
          title={insightsCase.title}
          isOpen
          onClose={() => setInsightsCase(null)}
        />
      )}
    </div>
  );
}
