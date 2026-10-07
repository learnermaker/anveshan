/**
 * ReviewDetail: steward reviews one skill from the queue (K9-P3 §3.4).
 */

import React, { useEffect, useState } from 'react';
import { ArrowLeft, FileDown, Pencil, Trash2 } from 'lucide-react';
import type { CaseView, StewardDecisionKind } from '../../api/types';
import { api } from '../../api/client';
import { SourcePanel } from '../../hero/SourcePanels';
import { Badge, ErrorNote, ReviewBadge, Spinner, btn } from '../../hero/ui';
import { licenceLabel, LIBRARY_STATUS_LABEL } from '../../copy/plain';
import { fmtDate, fmtRelative } from './format';
import { DEBUG } from '../../api/debug';

interface Props {
  caseId: string;
  onBack: () => void;
  onOpenSkill: (id: string) => void;
  onLibraryChanged: () => void;
}

type Decision = 'publish' | 'return' | 'reject';
type FeaturedDecision = 'approve' | 'unlist' | 'republish';

function NoteForm({
  placeholder,
  onSubmit,
  onCancel,
  label,
  busy,
}: {
  placeholder: string;
  onSubmit: (note: string) => void;
  onCancel: () => void;
  label: string;
  busy: boolean;
}) {
  const [note, setNote] = useState('');
  return (
    <div className="space-y-2 p-3 rounded-lg border border-outline bg-surface-dim">
      <textarea
        value={note}
        maxLength={500}
        rows={3}
        onChange={(e) => setNote(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-surface-container border border-outline rounded px-3 py-2 text-sm outline-none resize-none focus:border-caliper-cyan"
        autoFocus
      />
      <div className="flex gap-2">
        <button
          disabled={!note.trim() || busy}
          onClick={() => onSubmit(note.trim())}
          className={btn.primary}
        >
          {busy ? 'Saving…' : label}
        </button>
        <button onClick={onCancel} className={btn.secondary} disabled={busy}>Cancel</button>
      </div>
    </div>
  );
}

export function ReviewDetail({ caseId, onBack, onOpenSkill, onLibraryChanged }: Props) {
  const [view, setView] = useState<CaseView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [focus, setFocus] = useState<{ claimId: string; ev: unknown } | null>(null);

  // Submission decisions
  const [pendingDecision, setPendingDecision] = useState<Decision | null>(null);
  const [confirmPublish, setConfirmPublish] = useState(false);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [actionError, setActionError] = useState<unknown>(null);

  // Featured decisions
  const [reviewerName, setReviewerName] = useState('');
  const [featuredAction, setFeaturedAction] = useState<FeaturedDecision | null>(null);

  // Edit/remove claims
  const [editingClaim, setEditingClaim] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [removingClaim, setRemovingClaim] = useState<string | null>(null);
  const [claimBusy, setClaimBusy] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.getCase(caseId)
      .then(setView)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [caseId]);

  if (loading) return <Spinner label="Loading skill…" />;
  if (error) return <ErrorNote error={error} />;
  if (!view) return null;

  const access = view.access;
  const isSubmission = access?.library_status === 'submitted';
  const isCurated = view.hero && !view.case_id.includes('~');
  const isUniversal = view.goal.modality === 'universal';

  const doDecide = async (decision: StewardDecisionKind, note?: string) => {
    setBusy(true);
    setActionError(null);
    try {
      await api.stewardDecide(caseId, { decision, note });
      onLibraryChanged();
      const toastMap: Record<string, string> = {
        publish: 'Published.',
        return: 'Sent back to the creator.',
        reject: 'Rejected.',
        unlist: 'Hidden from library.',
        republish: 'Restored to library.',
      };
      setToast(toastMap[decision] ?? 'Done.');
      setTimeout(() => { setToast(null); onBack(); }, 1500);
    } catch (e) {
      setActionError(e);
      setBusy(false);
    }
  };

  const doApprove = async () => {
    if (!reviewerName.trim() && isCurated) return;
    setBusy(true);
    setActionError(null);
    try {
      const updated = await api.reviewCase(caseId, {
        action: 'approve',
        reviewer: reviewerName.trim() || 'steward',
        note: '',
      });
      setView(updated);
      onLibraryChanged();
      setToast('Marked as checked.');
      setTimeout(() => setToast(null), 2000);
    } catch (e) {
      setActionError(e);
    } finally {
      setBusy(false);
    }
  };

  const doDownloadExport = async () => {
    try {
      const blob = await api.stewardReviewExport(caseId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `anveshan-review-${caseId}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setActionError(e);
    }
  };

  const doEditClaim = async (claimId: string, newStatement: string) => {
    setClaimBusy(true);
    try {
      const updated = await api.reviewCase(caseId, {
        action: 'revise_claim',
        reviewer: reviewerName.trim() || 'steward',
        note: '',
        claim_id: claimId,
        new_statement: newStatement,
      });
      setView(updated);
      setEditingClaim(null);
    } catch (e) {
      setActionError(e);
    } finally {
      setClaimBusy(false);
    }
  };

  const doRemoveClaim = async (claimId: string) => {
    setClaimBusy(true);
    try {
      const updated = await api.reviewCase(caseId, {
        action: 'reject_claim',
        reviewer: reviewerName.trim() || 'steward',
        note: '',
        claim_id: claimId,
      });
      setView(updated);
      setRemovingClaim(null);
    } catch (e) {
      setActionError(e);
    } finally {
      setClaimBusy(false);
    }
  };

  const claims = view.package.claims;

  return (
    <div className="space-y-5 animate-fade-in">
      {toast && (
        <div className="p-3 rounded-lg bg-transmission-emerald/10 border border-transmission-emerald/30 text-sm text-transmission-emerald font-mono">
          {toast}
        </div>
      )}

      {/* Back */}
      <button onClick={onBack} className={btn.ghost}>
        <ArrowLeft className="w-3.5 h-3.5" /> Back to the queue
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2 min-w-0">
          <h2 data-plain-exempt className="font-serif text-2xl text-on-surface">{view.title}</h2>
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge tone={isCurated ? 'cyan' : 'amber'}>{isCurated ? 'Featured' : 'Community'}</Badge>
            {access && <Badge tone="muted">{LIBRARY_STATUS_LABEL[access.library_status]}</Badge>}
            <ReviewBadge status={view.review_status} />
          </div>
          <div className="text-[11px] text-on-surface-variant space-y-0.5">
            {access?.credit_name && <div>by {access.credit_name}</div>}
            {access?.licence && <div>{licenceLabel(access.licence)}</div>}
            {(view as any).submitted_at && <div>submitted {fmtRelative((view as any).submitted_at)}</div>}
          </div>
        </div>
        <button onClick={() => onOpenSkill(caseId)} className={btn.secondary}>Open as a learner</button>
      </div>

      {/* Main layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Left: source */}
        <div className="space-y-3">
          <div className="text-[10px] font-mono uppercase text-on-surface-variant font-bold">Source</div>
          {!isUniversal ? (
            <SourcePanel view={view} focus={(focus?.ev as any) ?? null} />
          ) : (
            (() => {
              const src = view.sources.find((s) => s.used_by_system !== false);
              if (!src) return <div className="text-[11px] text-on-surface-variant">No source available.</div>;
              const url = api.mediaUrl(caseId, src.source_id);
              if (src.mime_type.startsWith('image/'))
                return <img src={url} alt="Source" className="rounded-lg border border-outline w-full" />;
              if (src.mime_type.startsWith('video/'))
                return <video src={url} controls className="rounded-lg border border-outline w-full" />;
              if (src.mime_type.startsWith('audio/'))
                return <audio src={url} controls className="w-full" />;
              return <div className="text-[11px] text-on-surface-variant">Source type: {src.mime_type}</div>;
            })()
          )}
        </div>

        {/* Right: claims */}
        <div className="space-y-3">
          <div className="text-[10px] font-mono uppercase text-on-surface-variant font-bold">
            Steps and checks ({claims.length})
          </div>
          <ol className="space-y-2">
            {claims.map((c, idx) => (
              <li
                key={c.claim_id}
                className={`rounded-lg border p-3 space-y-1 cursor-pointer transition-colors ${focus?.claimId === c.claim_id ? 'border-caliper-cyan bg-caliper-cyan/5' : 'border-outline bg-surface-dim hover:border-cadmium-amber/50'}`}
                onClick={() => {
                  const ev = c.evidence_refs?.[0];
                  if (ev) setFocus({ claimId: c.claim_id, ev });
                }}
              >
                {editingClaim === c.claim_id ? (
                  <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                    <textarea
                      defaultValue={c.statement}
                      rows={2}
                      onChange={(e) => setEditText(e.target.value)}
                      className="w-full bg-surface-container border border-caliper-cyan rounded px-2 py-1.5 text-sm outline-none resize-none"
                      autoFocus
                    />
                    <div className="flex gap-2">
                      <button
                        disabled={claimBusy}
                        onClick={() => editText.trim() && void doEditClaim(c.claim_id, editText.trim())}
                        className={btn.primary}
                      >
                        {claimBusy ? 'Saving…' : 'Save'}
                      </button>
                      <button onClick={() => setEditingClaim(null)} className={btn.secondary}>Cancel</button>
                    </div>
                  </div>
                ) : removingClaim === c.claim_id ? (
                  <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                    <p className="text-[11px] text-on-surface">Remove this step? Learners will no longer be checked on it.</p>
                    <div className="flex gap-2">
                      <button disabled={claimBusy} onClick={() => void doRemoveClaim(c.claim_id)} className={`${btn.primary} !bg-divergence-crimson`}>
                        {claimBusy ? 'Removing…' : 'Remove'}
                      </button>
                      <button onClick={() => setRemovingClaim(null)} className={btn.secondary}>Keep</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2 min-w-0">
                        <span className="font-mono text-[11px] text-on-surface-variant shrink-0">{idx + 1}.</span>
                        <span data-plain-exempt className="text-sm text-on-surface">{c.statement}</span>
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <button
                          onClick={(e) => { e.stopPropagation(); setEditingClaim(c.claim_id); setEditText(c.statement); }}
                          aria-label={`Edit step ${idx + 1}`}
                          className={btn.ghost}
                        >
                          <Pencil className="w-3.5 h-3.5" aria-hidden="true" />
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); setRemovingClaim(c.claim_id); }}
                          aria-label={`Remove step ${idx + 1}`}
                          className={`${btn.ghost} text-divergence-crimson`}
                        >
                          <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                        </button>
                      </div>
                    </div>
                    {DEBUG && (
                      <div className="text-[9px] font-mono text-on-surface-variant">
                        {c.claim_id} · {c.claim_type ?? ''} · {c.is_observed ? 'Seen in the source' : "AI's reading"}
                        {(c as any).confidence != null && ` · confidence ${(c as any).confidence}`}
                      </div>
                    )}
                  </>
                )}
              </li>
            ))}
          </ol>
        </div>
      </div>

      {/* Decision bar */}
      <div className="sticky bottom-0 bg-surface-dim/95 backdrop-blur border-t border-outline p-4 space-y-3">
        <ErrorNote error={actionError} />

        {isSubmission && (
          <>
            {confirmPublish ? (
              <div className="space-y-2">
                <p className="text-sm text-on-surface">Publish to the library? Anyone will be able to practise it.</p>
                <div className="flex gap-2">
                  <button onClick={() => void doDecide('publish')} disabled={busy} className={btn.primary}>
                    {busy ? 'Publishing…' : 'Publish'}
                  </button>
                  <button onClick={() => setConfirmPublish(false)} className={btn.secondary}>Cancel</button>
                </div>
              </div>
            ) : pendingDecision === 'return' ? (
              <NoteForm
                placeholder="What should the creator change?"
                onSubmit={(note) => void doDecide('return', note)}
                onCancel={() => setPendingDecision(null)}
                label="Send back"
                busy={busy}
              />
            ) : pendingDecision === 'reject' ? (
              <NoteForm
                placeholder="Why is it not accepted?"
                onSubmit={(note) => void doDecide('reject', note)}
                onCancel={() => setPendingDecision(null)}
                label="Reject"
                busy={busy}
              />
            ) : (
              <div className="flex flex-wrap gap-2">
                <button onClick={() => setConfirmPublish(true)} className={btn.primary}>Publish</button>
                <button onClick={() => setPendingDecision('return')} className={btn.secondary}>Send back to creator</button>
                <button
                  onClick={() => setPendingDecision('reject')}
                  className={`${btn.secondary} !border-divergence-crimson !text-divergence-crimson`}
                >
                  Reject
                </button>
              </div>
            )}
          </>
        )}

        {isCurated && !isSubmission && (
          <div className="space-y-3">
            <div>
              <label htmlFor="reviewer-name" className="block text-[10px] font-mono uppercase text-on-surface-variant mb-1">
                Reviewer name (shown in the record)
              </label>
              <input
                id="reviewer-name"
                value={reviewerName}
                onChange={(e) => setReviewerName(e.target.value)}
                className="w-full max-w-xs bg-surface-dim border border-outline rounded-lg px-3 py-2 text-sm outline-none focus:border-caliper-cyan"
                required
              />
            </div>

            {featuredAction === 'unlist' ? (
              <NoteForm
                placeholder="Why are you hiding this skill?"
                onSubmit={(note) => void doDecide('unlist', note)}
                onCancel={() => setFeaturedAction(null)}
                label="Hide"
                busy={busy}
              />
            ) : (
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => void doApprove()}
                  disabled={busy || !reviewerName.trim()}
                  className={btn.primary}
                >
                  {busy ? 'Saving…' : 'Mark as checked by an expert'}
                </button>
                <button onClick={() => void doDownloadExport()} className={btn.secondary}>
                  <FileDown className="w-3.5 h-3.5" aria-hidden="true" /> Download decisions
                </button>
                {access?.library_status === 'published' || access?.library_status === 'unlisted' ? (
                  access.library_status === 'unlisted' ? (
                    <button onClick={() => void doDecide('republish')} disabled={busy} className={btn.secondary}>
                      Show in library
                    </button>
                  ) : (
                    <button onClick={() => setFeaturedAction('unlist')} className={`${btn.secondary} !border-divergence-crimson !text-divergence-crimson`}>
                      Hide from library
                    </button>
                  )
                ) : null}
              </div>
            )}

            <p className="text-[10px] text-on-surface-variant">
              The demo server forgets changes when it restarts. Download the decisions and commit them with{' '}
              <code className="font-mono">tools/apply_expert_review.py</code> to keep them.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
