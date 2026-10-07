/**
 * LibraryTab: steward view of the full library (K9-P3 §3.5).
 */

import React, { useEffect, useState } from 'react';
import type { StewardLibraryRow } from '../../api/types';
import { api } from '../../api/client';
import { Badge, ErrorNote, ReviewBadge, Spinner, btn } from '../../hero/ui';
import { LIBRARY_STATUS_LABEL } from '../../copy/plain';
import { fmtRelative } from './format';
import { InsightsDialog } from '../insights/InsightsDialog';
import { ReviewDetail } from './ReviewDetail';

type FilterKind = 'all' | 'featured' | 'community' | 'hidden';

const STATUS_TONE: Record<string, 'muted' | 'amber' | 'emerald' | 'crimson'> = {
  private: 'muted',
  submitted: 'amber',
  published: 'emerald',
  returned: 'amber',
  rejected: 'crimson',
  unlisted: 'muted',
};

interface Props {
  onOpenSkill: (id: string) => void;
  onLibraryChanged: () => void;
}

export function LibraryTab({ onOpenSkill, onLibraryChanged }: Props) {
  const [rows, setRows] = useState<StewardLibraryRow[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [filter, setFilter] = useState<FilterKind>('all');
  const [insightsCase, setInsightsCase] = useState<{ id: string; title: string } | null>(null);
  const [reviewing, setReviewing] = useState<string | null>(null);
  const [hideNote, setHideNote] = useState<string | null>(null);
  const [pendingHide, setPendingHide] = useState<string | null>(null);
  const [hideBusy, setHideBusy] = useState(false);

  const load = () => {
    setLoading(true);
    api.stewardLibrary()
      .then(setRows)
      .catch(setError)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (reviewing) {
    return (
      <ReviewDetail
        caseId={reviewing}
        onBack={() => setReviewing(null)}
        onOpenSkill={onOpenSkill}
        onLibraryChanged={() => { onLibraryChanged(); load(); }}
      />
    );
  }

  if (loading) return <Spinner label="Loading library…" />;
  if (error) return <ErrorNote error={error} />;
  if (!rows) return null;

  const filtered = rows.filter((r) => {
    if (filter === 'featured') return r.collection === 'curated';
    if (filter === 'community') return r.collection === 'community';
    if (filter === 'hidden') return r.library_status === 'unlisted';
    return true;
  });

  const handleHide = async (caseId: string, note: string) => {
    setHideBusy(true);
    try {
      await api.stewardDecide(caseId, { decision: 'unlist', note });
      onLibraryChanged();
      load();
      setPendingHide(null);
      setHideNote(null);
    } catch {
      /* handled in ReviewDetail; here just reset */
    } finally {
      setHideBusy(false);
    }
  };

  const handleShow = async (caseId: string) => {
    try {
      await api.stewardDecide(caseId, { decision: 'republish' });
      onLibraryChanged();
      load();
    } catch { /* ignore */ }
  };

  return (
    <div className="space-y-4">
      {/* Filter chips */}
      <div className="flex flex-wrap gap-2">
        {(['all', 'featured', 'community', 'hidden'] as FilterKind[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-full text-[11px] font-mono border transition-colors ${filter === f ? 'bg-cadmium-amber text-background border-cadmium-amber font-bold' : 'border-outline text-on-surface-variant hover:border-cadmium-amber'}`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-on-surface-variant py-6 text-center">No skills in the library yet.</p>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden sm:block overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-outline text-[10px] font-mono uppercase text-on-surface-variant">
                  <th className="text-left py-2 pr-3 font-normal">Skill</th>
                  <th className="text-left py-2 pr-3 font-normal">Collection</th>
                  <th className="text-left py-2 pr-3 font-normal">Status</th>
                  <th className="text-left py-2 pr-3 font-normal">Checked</th>
                  <th className="text-left py-2 pr-3 font-normal">Learners</th>
                  <th className="text-left py-2 pr-3 font-normal">Last activity</th>
                  <th className="text-left py-2 font-normal">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr key={row.case_id} className="border-b border-outline/30 hover:bg-surface-dim/50">
                    <td data-plain-exempt className="py-2 pr-3 font-medium text-on-surface max-w-[200px] truncate">{row.title}</td>
                    <td className="py-2 pr-3">
                      <Badge tone={row.collection === 'curated' ? 'cyan' : 'amber'}>
                        {row.collection === 'curated' ? 'Featured' : 'Community'}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3">
                      <Badge tone={STATUS_TONE[row.library_status] ?? 'muted'}>
                        {LIBRARY_STATUS_LABEL[row.library_status]}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3"><ReviewBadge status={row.review_status} /></td>
                    <td className="py-2 pr-3 font-mono text-on-surface-variant">{row.learners}</td>
                    <td className="py-2 pr-3 text-on-surface-variant text-[11px]">{row.last_activity ? fmtRelative(row.last_activity) : '—'}</td>
                    <td className="py-2">
                      <div className="flex flex-wrap gap-1">
                        <button onClick={() => setInsightsCase({ id: row.case_id, title: row.title })} className={btn.ghost}>Insights</button>
                        {pendingHide === row.case_id ? (
                          <div className="flex flex-col gap-1">
                            <input
                              type="text"
                              value={hideNote ?? ''}
                              onChange={(e) => setHideNote(e.target.value)}
                              placeholder="Reason for hiding"
                              className="bg-surface-dim border border-outline rounded px-2 py-0.5 text-[11px] outline-none focus:border-caliper-cyan"
                              autoFocus
                            />
                            <div className="flex gap-1">
                              <button
                                disabled={!hideNote?.trim() || hideBusy}
                                onClick={() => hideNote?.trim() && void handleHide(row.case_id, hideNote)}
                                className={btn.secondary}
                              >
                                {hideBusy ? 'Hiding…' : 'Confirm'}
                              </button>
                              <button onClick={() => { setPendingHide(null); setHideNote(null); }} className={btn.ghost}>Cancel</button>
                            </div>
                          </div>
                        ) : row.library_status === 'unlisted' ? (
                          <button onClick={() => void handleShow(row.case_id)} className={btn.ghost}>Show</button>
                        ) : row.library_status === 'published' ? (
                          <button onClick={() => { setPendingHide(row.case_id); setHideNote(''); }} className={`${btn.ghost} text-divergence-crimson`}>Hide</button>
                        ) : null}
                        <button onClick={() => setReviewing(row.case_id)} className={btn.ghost}>Review</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="sm:hidden space-y-3">
            {filtered.map((row) => (
              <div key={row.case_id} className="rounded-xl border border-outline bg-surface-container-low/80 p-4 space-y-2">
                <h3 data-plain-exempt className="font-semibold text-on-surface text-sm">{row.title}</h3>
                <div className="flex flex-wrap gap-1.5">
                  <Badge tone={row.collection === 'curated' ? 'cyan' : 'amber'}>
                    {row.collection === 'curated' ? 'Featured' : 'Community'}
                  </Badge>
                  <Badge tone={STATUS_TONE[row.library_status] ?? 'muted'}>
                    {LIBRARY_STATUS_LABEL[row.library_status]}
                  </Badge>
                  <ReviewBadge status={row.review_status} />
                </div>
                <div className="text-[11px] text-on-surface-variant">
                  {row.learners} learners · {row.last_activity ? fmtRelative(row.last_activity) : 'no activity'}
                </div>
                <div className="flex flex-wrap gap-1 pt-1">
                  <button onClick={() => setInsightsCase({ id: row.case_id, title: row.title })} className={btn.secondary}>Insights</button>
                  <button onClick={() => setReviewing(row.case_id)} className={btn.secondary}>Review</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {insightsCase && (
        <InsightsDialog
          caseId={insightsCase.id}
          title={insightsCase.title}
          isOpen
          onClose={() => setInsightsCase(null)}
        />
      )}
    </div>
  );
}
