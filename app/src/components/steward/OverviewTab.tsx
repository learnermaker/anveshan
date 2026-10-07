/**
 * OverviewTab: KPI grid and "Needs your attention" list (K9-P3 §3.3).
 */

import React, { useEffect, useState } from 'react';
import { BarChart3, CheckCircle2, Gauge, HardDrive, Inbox, Library, ListChecks, Users } from 'lucide-react';
import type { StewardOverview } from '../../api/types';
import { api } from '../../api/client';
import { ErrorNote, ProgressBar, Spinner } from '../../hero/ui';
import { fmtBytes } from './format';

interface Props {
  onSwitchToQueue: () => void;
  onReviewCase: (caseId: string) => void;
}

export function OverviewTab({ onSwitchToQueue, onReviewCase }: Props) {
  const [data, setData] = useState<StewardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    setLoading(true);
    api.stewardOverview()
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="Loading overview…" />;
  if (error) return <ErrorNote error={error} />;
  if (!data) return null;

  const hasBudget = data.daily_budget > 0;
  const hasCap = data.storage_cap_bytes > 0;

  const kpis = [
    {
      icon: Library,
      label: 'Skills in the library',
      value: data.library_skills,
      caption: null,
      bar: null,
      onClick: undefined as (() => void) | undefined,
    },
    {
      icon: Inbox,
      label: 'Waiting for review',
      value: data.waiting_review,
      caption: null,
      bar: null,
      onClick: data.waiting_review > 0 ? onSwitchToQueue : undefined,
    },
    {
      icon: Users,
      label: 'Learners today',
      value: data.learners_today,
      caption: null,
      bar: null,
      onClick: undefined,
    },
    {
      icon: ListChecks,
      label: 'Tries today',
      value: data.attempts_today,
      caption: null,
      bar: null,
      onClick: undefined,
    },
    {
      icon: Gauge,
      label: 'AI calls today',
      value: data.live_calls_today,
      caption: hasBudget ? `of ${data.daily_budget} allowed` : 'no daily limit',
      bar: hasBudget ? data.live_calls_today / data.daily_budget : null,
      onClick: undefined,
    },
    {
      icon: HardDrive,
      label: 'Storage used',
      value: fmtBytes(data.storage_bytes),
      caption: hasCap ? `of ${fmtBytes(data.storage_cap_bytes)}` : 'no cap',
      bar: hasCap ? data.storage_bytes / data.storage_cap_bytes : null,
      onClick: undefined,
    },
  ];

  return (
    <div className="space-y-6">
      {/* KPI grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {kpis.map(({ icon: Icon, label, value, caption, bar, onClick }) => (
          <button
            key={label}
            onClick={onClick}
            disabled={!onClick}
            className={`rounded-xl border border-outline bg-surface-container p-4 text-left space-y-2 transition-colors ${onClick ? 'hover:border-cadmium-amber cursor-pointer' : 'cursor-default'}`}
          >
            <div className="flex items-center gap-2 text-on-surface-variant">
              <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span className="text-[11px] font-mono uppercase">{label}</span>
            </div>
            <div className="text-2xl font-serif font-bold text-on-surface">{value}</div>
            {caption && <div className="text-[11px] text-on-surface-variant">{caption}</div>}
            {bar != null && <ProgressBar value={Math.min(1, bar)} />}
          </button>
        ))}
      </div>

      {/* Needs your attention */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-on-surface">Needs your attention</h3>
        {data.attention.length === 0 ? (
          <div className="flex items-center gap-2 text-sm text-on-surface-variant">
            <CheckCircle2 className="w-4 h-4 text-transmission-emerald shrink-0" aria-hidden="true" />
            Nothing needs your attention right now.
          </div>
        ) : (
          <ul className="space-y-2">
            {data.attention.map((item, i) => (
              <li
                key={i}
                className="flex items-start justify-between gap-3 p-3 rounded-lg border border-outline bg-surface-dim text-sm"
              >
                <span className="text-on-surface">{item.text}</span>
                {item.kind === 'submissions_waiting' && (
                  <button onClick={onSwitchToQueue} className="text-[11px] font-mono text-caliper-cyan underline shrink-0">
                    Open queue
                  </button>
                )}
                {item.kind === 'curated_unchecked' && item.case_id && (
                  <button onClick={() => onReviewCase(item.case_id!)} className="text-[11px] font-mono text-caliper-cyan underline shrink-0">
                    Review
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {data.ephemeral && (
        <p className="text-[11px] text-on-surface-variant">
          This server stores data in memory only. Counts reset when the server restarts.
        </p>
      )}
    </div>
  );
}
