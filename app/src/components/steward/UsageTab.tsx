/**
 * UsageTab: server usage metrics (K9-P3 §3.7).
 */

import React, { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import type { UsageView } from '../../api/types';
import { api } from '../../api/client';
import { ErrorNote, ProgressBar, Spinner, btn } from '../../hero/ui';
import { fmtBytes, fmtDuration } from './format';

const CLASS_FRIENDLY: Record<string, string> = {
  compose: 'Analyse an upload',
  compose_step: 'Edit a skill',
  attempt: 'Submit a try',
  query: 'Ask a question',
  auth: 'Steward sign-in',
};

const ERR_FRIENDLY: Record<string, string> = {
  INVALID_INPUT: 'Rejected input',
  MODEL_FAILURE: 'AI service problem',
  MODEL_TIMEOUT: 'AI took too long',
  RATE_LIMITED: 'Rate limited',
  STEWARD_REQUIRED: 'Steward code missing',
};

export function UsageTab() {
  const [data, setData] = useState<UsageView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api.stewardUsage()
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading) return <Spinner label="Loading usage…" />;
  if (error) return <ErrorNote error={error} />;
  if (!data) return null;

  const hasBudget = data.daily_budget > 0;
  const hasCap = data.storage_cap_bytes > 0;
  const aiPct = hasBudget ? data.live_calls_today / data.daily_budget : null;

  const requestsByClass = Object.entries(data.requests_by_class ?? {});
  const rateLimited = Object.entries(data.rate_limited ?? {});
  const errorsByCategory = Object.entries(data.errors_by_category ?? {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-on-surface">Server usage</h3>
        <button onClick={load} className={btn.secondary}>
          <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" /> Refresh
        </button>
      </div>

      {/* Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div className="rounded-xl border border-outline bg-surface-container p-4 space-y-2">
          <div className="text-[10px] font-mono uppercase text-on-surface-variant">AI calls today</div>
          <div className="text-2xl font-serif font-bold text-on-surface">{data.live_calls_today}</div>
          <div className="text-[10px] text-on-surface-variant">{hasBudget ? `of ${data.daily_budget} allowed` : 'no daily limit'}</div>
          {hasBudget && aiPct != null && <ProgressBar value={Math.min(1, aiPct)} />}
        </div>

        <div className="rounded-xl border border-outline bg-surface-container p-4 space-y-1">
          <div className="text-[10px] font-mono uppercase text-on-surface-variant">Calls with your own key</div>
          <div className="text-2xl font-serif font-bold text-on-surface">{data.own_key_calls}</div>
        </div>

        <div className="rounded-xl border border-outline bg-surface-container p-4 space-y-1">
          <div className="text-[10px] font-mono uppercase text-on-surface-variant">Repeat calls from cache</div>
          <div className="text-2xl font-serif font-bold text-on-surface">{data.cache_hits}</div>
        </div>

        <div className="rounded-xl border border-outline bg-surface-container p-4 space-y-1">
          <div className="text-[10px] font-mono uppercase text-on-surface-variant">Tries today</div>
          <div className="text-2xl font-serif font-bold text-on-surface">{data.attempts_today}</div>
        </div>

        <div className="rounded-xl border border-outline bg-surface-container p-4 space-y-1">
          <div className="text-[10px] font-mono uppercase text-on-surface-variant">New skills analysed today</div>
          <div className="text-2xl font-serif font-bold text-on-surface">{data.compose_today}</div>
        </div>

        <div className="rounded-xl border border-outline bg-surface-container p-4 space-y-2">
          <div className="text-[10px] font-mono uppercase text-on-surface-variant">Storage</div>
          <div className="text-lg font-serif font-bold text-on-surface">{fmtBytes(data.storage_bytes)}</div>
          <div className="text-[10px] text-on-surface-variant">{hasCap ? `of ${fmtBytes(data.storage_cap_bytes)}` : 'no cap'}</div>
          {hasCap && <ProgressBar value={Math.min(1, data.storage_bytes / data.storage_cap_bytes)} />}
        </div>

        <div className="rounded-xl border border-outline bg-surface-container p-4 space-y-1">
          <div className="text-[10px] font-mono uppercase text-on-surface-variant">Private data kept for</div>
          <div className="text-lg font-serif font-bold text-on-surface">
            {data.data_ttl_hours > 0 ? `${data.data_ttl_hours} hours` : 'kept until restart'}
          </div>
        </div>

        <div className="rounded-xl border border-outline bg-surface-container p-4 space-y-1">
          <div className="text-[10px] font-mono uppercase text-on-surface-variant">Server mode</div>
          <div className="text-lg font-serif font-bold text-on-surface">
            {data.mode === 'live' ? 'Live AI' : 'Recorded results'}
          </div>
        </div>

        <div className="rounded-xl border border-outline bg-surface-container p-4 space-y-1">
          <div className="text-[10px] font-mono uppercase text-on-surface-variant">Running for</div>
          <div className="text-lg font-serif font-bold text-on-surface">{fmtDuration(data.uptime_s)}</div>
        </div>
      </div>

      {/* Requests by type */}
      {requestsByClass.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[10px] font-mono uppercase text-on-surface-variant font-bold">Requests by type</h4>
          <table className="w-full text-[11px] border-collapse">
            <tbody>
              {requestsByClass.map(([cls, count]) => (
                <tr key={cls} className="border-b border-outline/20">
                  <td className="py-1 pr-3 text-on-surface">{CLASS_FRIENDLY[cls] ?? cls}</td>
                  <td className="py-1 font-mono text-on-surface-variant text-right">{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Blocked by rate limits */}
      {rateLimited.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[10px] font-mono uppercase text-on-surface-variant font-bold">Blocked by rate limits</h4>
          <table className="w-full text-[11px] border-collapse">
            <tbody>
              {rateLimited.map(([cls, count]) => (
                <tr key={cls} className="border-b border-outline/20">
                  <td className="py-1 pr-3 text-on-surface">{CLASS_FRIENDLY[cls] ?? cls}</td>
                  <td className="py-1 font-mono text-cadmium-amber text-right">{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Problems by type */}
      {errorsByCategory.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[10px] font-mono uppercase text-on-surface-variant font-bold">Problems by type</h4>
          <table className="w-full text-[11px] border-collapse">
            <tbody>
              {errorsByCategory.map(([cat, count]) => (
                <tr key={cat} className="border-b border-outline/20">
                  <td className="py-1 pr-3 text-on-surface">{ERR_FRIENDLY[cat] ?? cat}</td>
                  <td className="py-1 font-mono text-divergence-crimson text-right">{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="text-[10px] text-on-surface-variant">
        All counts are since the server started. No personal data is stored.
      </div>
    </div>
  );
}
