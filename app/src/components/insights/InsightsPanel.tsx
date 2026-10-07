/**
 * InsightsPanel: aggregate, anonymous learner outcomes for one skill (K9-P3 §2.5).
 * Fetches GET /api/insights/{case_id} and renders the K9-00 §6.7 layout.
 */

import React, { useEffect, useState } from 'react';
import { Inbox, Lightbulb } from 'lucide-react';
import { api } from '../../api/client';
import type { InsightsView } from '../../api/types';
import { ErrorNote, Spinner } from '../../hero/ui';
import { fmtPct } from '../steward/format';

interface BarRowProps {
  name: string;
  count: number;
  share: number;
}
function BarRow({ name, count, share }: BarRowProps) {
  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between text-[11px]">
        <span data-plain-exempt className="text-on-surface truncate max-w-[70%]">{name}</span>
        <span className="font-mono text-on-surface-variant ml-2 shrink-0">{count} ({fmtPct(share)})</span>
      </div>
      <div className="h-2 rounded bg-surface-dim border border-outline overflow-hidden">
        <div
          className="h-full bg-cadmium-amber/70 transition-all"
          style={{ width: `${Math.max(4, share * 100)}%` }}
        />
      </div>
    </div>
  );
}

interface Props {
  caseId: string;
  title?: string;
}

export function InsightsPanel({ caseId }: Props) {
  const [data, setData] = useState<InsightsView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setData(null);
    api.getInsights(caseId)
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [caseId]);

  if (loading) return <Spinner label="Loading learner data…" />;
  if (error) return <ErrorNote error={error} />;
  if (!data) return null;

  if (data.attempts === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-8 text-center text-on-surface-variant">
        <Inbox className="w-8 h-8 opacity-40" aria-hidden="true" />
        <p className="text-sm">No learners have tried this skill yet. Insights will appear once people start practising.</p>
      </div>
    );
  }

  return (
    <div className="space-y-5 text-sm">
      {!data.enough_data && (
        <div className="flex items-start gap-2 p-3 rounded-lg border border-cadmium-amber/40 bg-cadmium-amber/5 text-[11px] text-on-surface-variant">
          Fewer than 3 learners so far: treat these numbers as anecdotes.
        </div>
      )}

      {/* Numbers row */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Learners', value: data.learners },
          { label: 'Tries', value: data.attempts },
          { label: 'Finished both tries', value: data.completed },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg border border-outline bg-surface-container p-3 text-center">
            <div className="text-2xl font-serif font-bold text-on-surface">{value}</div>
            <div className="text-[11px] font-mono text-on-surface-variant mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* First vs second try */}
      <div className="space-y-1">
        <div className="text-[11px] font-mono uppercase text-on-surface-variant font-bold">First try → Second try</div>
        <div className="flex items-center gap-2 font-mono text-sm">
          <span className="text-cadmium-amber">{fmtPct(data.baseline.pass_rate)}</span>
          <span className="text-on-surface-variant">→</span>
          <span className="text-transmission-emerald">{fmtPct(data.retry.pass_rate)}</span>
        </div>
      </div>

      {/* Where learners first go wrong */}
      <div className="space-y-2">
        <div className="text-[11px] font-mono uppercase text-on-surface-variant font-bold">Where learners first go wrong</div>
        {data.first_wrong.length === 0 ? (
          <p className="text-[11px] text-on-surface-variant">No first tries went off track yet.</p>
        ) : (
          <div className="space-y-2">
            {data.first_wrong.map((r) => (
              <BarRow key={r.criterion_id} name={r.name} count={r.count} share={r.share} />
            ))}
          </div>
        )}
      </div>

      {/* Hardest checks */}
      <div className="space-y-2">
        <div className="text-[11px] font-mono uppercase text-on-surface-variant font-bold">Hardest checks</div>
        {data.hardest.length === 0 ? (
          <p className="text-[11px] text-on-surface-variant">No data on hard checks yet.</p>
        ) : (
          <div className="space-y-2">
            {data.hardest.map((r) => (
              <BarRow key={r.criterion_id} name={r.name} count={r.n} share={r.miss_rate} />
            ))}
          </div>
        )}
      </div>

      {/* Did the feedback help? */}
      <div className="space-y-1">
        <div className="text-[11px] font-mono uppercase text-on-surface-variant font-bold">Did the feedback help?</div>
        {data.feedback_helped.sessions === 0 ? (
          <p className="text-[11px] text-on-surface-variant">Not enough second tries yet.</p>
        ) : (
          <p className="text-[11px] text-on-surface-variant">
            In {data.feedback_helped.improved} of {data.feedback_helped.sessions} second tries, the check the feedback focused on improved.
          </p>
        )}
      </div>

      {/* Suggestions */}
      <div className="space-y-2">
        <div className="text-[11px] font-mono uppercase text-on-surface-variant font-bold">Suggestions</div>
        {data.suggestions.length === 0 ? (
          <p className="text-[11px] text-on-surface-variant">No suggestions yet.</p>
        ) : (
          <ul className="space-y-2">
            {data.suggestions.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-[11px] text-on-surface-variant">
                <Lightbulb className="w-3.5 h-3.5 text-cadmium-amber shrink-0 mt-0.5" aria-hidden="true" />
                <span>{s.text}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="text-[11px] text-on-surface-variant">Suggestions follow fixed rules from these numbers. They are not written by AI.</p>
      </div>

      <p className="text-[11px] text-on-surface-variant border-t border-outline pt-3">
        Counts since this demo server last started. No names or recordings are kept.
      </p>
    </div>
  );
}
