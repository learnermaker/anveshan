/**
 * ConsentTab: consent and licence ledger with download (K9-P3 §3.6).
 */

import React, { useEffect, useState } from 'react';
import { FileDown } from 'lucide-react';
import type { ConsentRow } from '../../api/types';
import { api } from '../../api/client';
import { Badge, ErrorNote, Spinner, btn } from '../../hero/ui';
import { licenceLabel, LIBRARY_STATUS_LABEL } from '../../copy/plain';
import { fmtDate } from './format';

const STATUS_TONE: Record<string, 'muted' | 'amber' | 'emerald' | 'crimson'> = {
  private: 'muted', submitted: 'amber', published: 'emerald', returned: 'amber',
  rejected: 'crimson', unlisted: 'muted',
};

export function ConsentTab() {
  const [rows, setRows] = useState<ConsentRow[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [downloadErr, setDownloadErr] = useState<unknown>(null);

  useEffect(() => {
    api.stewardConsent()
      .then(setRows)
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  const handleDownload = async () => {
    setDownloadErr(null);
    try {
      const blob = await api.stewardConsentExport();
      const url = URL.createObjectURL(blob);
      const now = new Date();
      const yyyymmdd = now.toISOString().slice(0, 10).replace(/-/g, '');
      const a = document.createElement('a');
      a.href = url;
      a.download = `anveshan-consent-${yyyymmdd}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setDownloadErr(e);
    }
  };

  if (loading) return <Spinner label="Loading consent records…" />;
  if (error) return <ErrorNote error={error} />;
  if (!rows) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-sm font-semibold text-on-surface">Consent and licence records</h3>
        <button onClick={() => void handleDownload()} className={btn.secondary}>
          <FileDown className="w-3.5 h-3.5" aria-hidden="true" /> Download record (JSON)
        </button>
      </div>

      <ErrorNote error={downloadErr} />

      {rows.length === 0 ? (
        <p className="text-sm text-on-surface-variant">No consent records yet.</p>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden sm:block overflow-x-auto">
            <table className="w-full text-[11px] border-collapse">
              <thead>
                <tr className="border-b border-outline text-[11px] font-mono uppercase text-on-surface-variant">
                  <th className="text-left py-2 pr-3 font-normal">Skill</th>
                  <th className="text-left py-2 pr-3 font-normal">Credit</th>
                  <th className="text-left py-2 pr-3 font-normal">Licence</th>
                  <th className="text-left py-2 pr-3 font-normal">Consent</th>
                  <th className="text-left py-2 pr-3 font-normal">Rights confirmed</th>
                  <th className="text-left py-2 pr-3 font-normal">People in media</th>
                  <th className="text-left py-2 font-normal">Sources</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <React.Fragment key={row.case_id}>
                    <tr
                      className="border-b border-outline/30 hover:bg-surface-dim/50 cursor-pointer"
                      onClick={() => setExpanded((e) => e === row.case_id ? null : row.case_id)}
                    >
                      <td className="py-2 pr-3">
                        <div data-plain-exempt className="font-medium text-on-surface truncate max-w-[160px]">{row.title}</div>
                        <Badge tone={STATUS_TONE[row.library_status] ?? 'muted'}>
                          {LIBRARY_STATUS_LABEL[row.library_status]}
                        </Badge>
                      </td>
                      <td className="py-2 pr-3 text-on-surface-variant">{row.credit_name ?? '—'}</td>
                      <td className="py-2 pr-3 text-on-surface-variant">{licenceLabel(row.licence)}</td>
                      <td className="py-2 pr-3 text-on-surface-variant">Anyone may practise</td>
                      <td className="py-2 pr-3 text-on-surface-variant">
                        {row.rights_confirmed ? fmtDate(row.rights_confirmed_at) || 'Yes' : 'Not recorded'}
                      </td>
                      <td className="py-2 pr-3">
                        {!row.people_visible ? (
                          <span className="text-on-surface-variant">No</span>
                        ) : row.people_consented ? (
                          <span className="text-transmission-emerald">Yes, they agreed</span>
                        ) : (
                          <span className="text-divergence-crimson font-semibold">Yes, NOT confirmed</span>
                        )}
                      </td>
                      <td className="py-2 text-on-surface-variant" data-plain-exempt>
                        {row.sources.map((s, i) => (
                          <span key={s.source_id}>
                            {i > 0 && '; '}
                            {s.attribution} · {s.license}
                          </span>
                        ))}
                      </td>
                    </tr>
                    {expanded === row.case_id && (
                      <tr className="border-b border-outline/30 bg-surface-dim/30">
                        <td colSpan={7} className="py-2 px-3">
                          <div className="space-y-1">
                            <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-1">History</div>
                            {row.history.length === 0 ? (
                              <p className="text-[11px] text-on-surface-variant">No history.</p>
                            ) : (
                              <ul className="space-y-0.5">
                                {row.history.map((h, i) => (
                                  <li key={i} className="text-[11px] text-on-surface-variant font-mono">
                                    {fmtDate(h.at)} · {h.actor} · {h.action}{h.note ? ` — ${h.note}` : ''}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="sm:hidden space-y-3">
            {rows.map((row) => (
              <div key={row.case_id} className="rounded-xl border border-outline bg-surface-container-low/80 p-4 space-y-2">
                <h3 data-plain-exempt className="font-semibold text-on-surface text-sm">{row.title}</h3>
                <div className="text-[11px] text-on-surface-variant space-y-0.5">
                  <div>Credit: {row.credit_name ?? '—'}</div>
                  <div>Licence: {licenceLabel(row.licence)}</div>
                  <div>Rights: {row.rights_confirmed ? fmtDate(row.rights_confirmed_at) || 'Confirmed' : 'Not recorded'}</div>
                  {row.people_visible && (
                    <div className={row.people_consented ? 'text-transmission-emerald' : 'text-divergence-crimson font-semibold'}>
                      {row.people_consented ? 'People shown, they agreed' : 'People shown, NOT confirmed'}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => setExpanded((e) => e === row.case_id ? null : row.case_id)}
                  className={btn.ghost}
                >
                  {expanded === row.case_id ? 'Hide history' : 'Show history'}
                </button>
                {expanded === row.case_id && row.history.map((h, i) => (
                  <div key={i} className="text-[11px] font-mono text-on-surface-variant">
                    {fmtDate(h.at)} · {h.actor} · {h.action}{h.note ? ` — ${h.note}` : ''}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
