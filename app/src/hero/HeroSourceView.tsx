/** 01 SOURCE for a live hero case: modality source view, claims, evidence query, expert review. */

import React, { useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, MessageSquareQuote, Pencil, RefreshCw, Search, X } from 'lucide-react';
import type { EvidenceRef, KnowledgeClaim } from '../types/contracts';
import type { CaseView, QueryAnswer, ReviewAction } from '../api/types';
import { api } from '../api/client';
import { SourcePanel } from './SourcePanels';
import { claimVerification, fmtTime } from './locators';
import { Badge, btn, ErrorNote, MockBadge, Panel, ReviewBadge, SourceLabelBadge, Spinner, VerificationBadge } from './ui';
import { TrustLine } from './TrustLine';
import { StepsList } from './StepsList';
import { pointNumber } from './StepsList';
import { UniversalSourceView } from './universal/UniversalSourceView';
import { DEBUG } from '../api/debug';

interface Props {
  view: CaseView;
  onViewChange: (v: CaseView) => void;
  onReload: () => void;
  onEnterPractice: () => void;
  onBack: () => void;
  /** K9: the creator's "Your skill" panel (built by P3), shown at the top of the right column for the owner */
  ownerSlot?: React.ReactNode;
}

export function HeroSourceView(props: Props) {
  if (props.view.goal.modality === 'universal') return <UniversalSourceView {...props} />;
  return <HeroSourceViewInner {...props} />;
}

function HeroSourceViewInner({ view, onViewChange, onReload, onEnterPractice, onBack, ownerSlot }: Props) {
  const [focus, setFocus] = useState<{ claimId: string; ev: EvidenceRef } | null>(null);
  const claims = view.package.claims;

  const onShow = (claimId: string) => {
    const c = claims.find((x) => x.claim_id === claimId);
    if (c?.evidence_refs[0]) setFocus({ claimId, ev: c.evidence_refs[0] });
  };

  const firstSource = view.sources[0];

  return (
    <div className="flex flex-col gap-5 w-full animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          <button onClick={onBack} className={btn.ghost}>
            <ArrowLeft className="w-3.5 h-3.5" /> All skills
          </button>
          <div className="text-xs font-mono uppercase tracking-widest text-cadmium-amber font-bold">Step 1 of 3 · Learn from the source</div>
          <h1 className="font-serif text-2xl sm:text-3xl text-on-surface" data-plain-exempt>{view.title}</h1>
          {!DEBUG ? (
            <TrustLine view={view} />
          ) : (
            <div className="flex flex-wrap items-center gap-1.5">
              <SourceLabelBadge label={view.runtime_label} />
              <ReviewBadge status={view.review_status} />
              <Badge tone="muted" title={`goal model v${view.goal.version}`}>{view.modality}</Badge>
              {view.derived_from && <Badge tone="muted">derived from {view.derived_from}</Badge>}
              <MockBadge />
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {DEBUG && (
            <button onClick={onReload} className={btn.secondary} title="Reload case from the service">
              <RefreshCw className="w-3.5 h-3.5" /> Reload
            </button>
          )}
          <button onClick={onEnterPractice} className={btn.primary}>
            Start practising <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {!DEBUG ? (
        <p className="text-sm text-on-surface-variant max-w-3xl">
          Watch how the source does it. Each step below links to the moment in the source. When you are ready, press{' '}
          <strong className="text-on-surface">Start practising</strong>.
        </p>
      ) : (
        <p className="text-sm text-on-surface-variant max-w-3xl">
          This page shows what Anveshan learned from the source. Each step and check is a numbered claim (CLM-01, CLM-02…) linked to evidence. OBSERVED claims were
          measured or seen in the source; INFERRED ones are the AI's reading and may be wrong. When you are ready, press{' '}
          <strong className="text-on-surface">Start practising</strong>.
        </p>
      )}

      {DEBUG && [...new Set([...(view.warnings ?? []), ...(view.goal.warnings ?? [])])].length > 0 && (
        <ul className="text-[11px] font-mono text-cadmium-amber space-y-0.5">
          {[...new Set([...(view.warnings ?? []), ...(view.goal.warnings ?? [])])].map((w, i) => (
            <li key={i}>⚠ {w}</li>
          ))}
        </ul>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] gap-5">
        <div className="space-y-5 min-w-0">
          <Panel kicker={DEBUG ? 'Source evidence' : 'Source'} title={<span data-plain-exempt>{view.package.title}</span>}>
            <SourcePanel view={view} focus={focus?.ev ?? null} />
          </Panel>
          {!DEBUG && firstSource && (
            <p className="text-xs text-on-surface-variant px-1">
              Source: {firstSource.attribution} · {firstSource.license}
            </p>
          )}
          {DEBUG && (
            <Panel kicker="Provenance" title="Sources">
              <ul className="space-y-2 text-[11px]">
                {view.sources.map((s) => (
                  <li key={s.source_id} className="flex flex-wrap items-center gap-2">
                    <code className="font-mono text-caliper-cyan">{s.source_id}</code>
                    <SourceLabelBadge label={s.runtime_label} />
                    <span className="text-on-surface-variant">{s.attribution}</span>
                    <span className="font-mono text-on-surface-variant">· {s.license}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-on-surface-variant">Consent: {view.package.consent.contributor_name} — {view.package.consent.consent_scope}</p>
            </Panel>
          )}
        </div>

        <div className="space-y-5 min-w-0">
          {ownerSlot}
          {!DEBUG ? (
            <Panel kicker="What you'll learn" title={`${claims.length} steps and checks`}>
              <p className="text-xs text-on-surface-variant mb-3" data-plain-exempt>{view.package.summary}</p>
              <StepsList
                claims={claims}
                activeId={focus?.claimId ?? null}
                onShow={(id) => onShow(id)}
              />
            </Panel>
          ) : (
            <Panel kicker="Knowledge package" title={`Claims (${claims.length})`}>
              <p className="text-[11px] text-on-surface-variant mb-3">{view.package.summary}</p>
              <ul className="space-y-2">
                {claims.map((c) => (
                  <ClaimRow key={c.claim_id} claim={c} active={focus?.claimId === c.claim_id} onFocus={(ev) => setFocus(ev ? { claimId: c.claim_id, ev } : null)} />
                ))}
              </ul>
            </Panel>
          )}
          <EvidenceQuery view={view} onCite={(id) => onShow(id)} />
          {DEBUG && <ExpertReviewPanel view={view} onViewChange={onViewChange} />}
        </div>
      </div>
    </div>
  );
}

function ClaimRow({ claim, active, onFocus }: { claim: KnowledgeClaim; active: boolean; onFocus: (ev: EvidenceRef | null) => void }) {
  const ev = claim.evidence_refs[0];
  const state = claimVerification(claim);
  return (
    <li>
      <button
        type="button"
        onClick={() => onFocus(active ? null : ev ?? null)}
        disabled={!ev}
        className={`w-full text-left p-2.5 rounded-lg border transition-colors ${active ? 'border-cadmium-amber bg-cadmium-amber/10' : 'border-outline/60 bg-surface-dim hover:border-on-surface-variant'} disabled:cursor-default`}
      >
        <div className="flex flex-wrap items-center gap-1.5 mb-1">
          <code className="text-[11px] font-mono text-caliper-cyan">{claim.claim_id}</code>
          <Badge tone="muted">{claim.claim_type}</Badge>
          <VerificationBadge state={state} />
          {ev && (typeof ev.start_sec === 'number' ? <span className="text-[11px] font-mono text-on-surface-variant">{fmtTime(ev.start_sec)}{typeof ev.end_sec === 'number' ? `–${fmtTime(ev.end_sec)}` : ''}</span> : null)}
          {ev && <span className="text-[11px] font-mono text-on-surface-variant">conf {ev.confidence.toFixed(2)}</span>}
        </div>
        <div className="text-xs text-on-surface leading-relaxed">{claim.statement}</div>
        {!ev && <div className="text-[11px] font-mono text-on-surface-variant mt-1">No locatable evidence — shown for transparency only.</div>}
      </button>
    </li>
  );
}

function EvidenceQuery({ view, onCite }: { view: CaseView; onCite: (claimId: string) => void }) {
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const [ans, setAns] = useState<QueryAnswer | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const claims = view.package.claims;

  const ask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!q.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      setAns(await api.queryCase(view.case_id, q.trim()));
    } catch (x) {
      setErr(x);
      setAns(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel kicker="Ask" title="Ask about this skill">
      <form onSubmit={ask} className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={QUESTION_EXAMPLE[view.modality] ?? 'e.g. What is the most important step?'}
          className="flex-1 min-w-0 bg-surface-dim border border-outline rounded-lg px-3 py-2 text-xs text-on-surface placeholder:text-on-surface-variant/50 focus:border-caliper-cyan outline-none"
        />
        <button type="submit" disabled={busy || !q.trim()} className={btn.secondary}>
          <Search className="w-3.5 h-3.5" /> Ask
        </button>
      </form>
      <div className="mt-3 space-y-2">
        {busy && <Spinner label="Looking in the source…" />}
        <ErrorNote error={err} />
        {ans && (
          <div className={`p-3 rounded-lg border text-xs ${ans.sufficient ? 'border-outline bg-surface-dim' : 'border-cadmium-amber/40 bg-cadmium-amber/10'}`}>
            {!ans.sufficient && <p className="mb-1 text-cadmium-amber text-xs">The source does not say.</p>}
            <div className="flex gap-2">
              <MessageSquareQuote className="w-4 h-4 text-on-surface-variant shrink-0" />
              <p className="text-on-surface leading-relaxed" data-plain-exempt>{ans.answer}</p>
            </div>
            {ans.cited_claim_ids.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5 items-center">
                <span className="text-[11px] font-mono text-on-surface-variant">From:</span>
                {ans.cited_claim_ids.map((id) => {
                  const n = pointNumber(claims, id);
                  return (
                    <button key={id} onClick={() => onCite(id)} className="text-[11px] font-mono text-caliper-cyan underline decoration-dotted">
                      {n != null ? `point ${n}` : DEBUG ? id : 'a step'}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}

const QUESTION_EXAMPLE: Record<string, string> = {
  kolam_image: 'e.g. Which dots stay enclosed?',
  origami_video: 'e.g. When is the paper folded into a square base?',
  tabla_audio: 'e.g. What tempo is the pattern played at?',
};

function ExpertReviewPanel({ view, onViewChange }: { view: CaseView; onViewChange: (v: CaseView) => void }) {
  const [open, setOpen] = useState<boolean | null>(null);
  const [token, setToken] = useState('');
  useEffect(() => {
    api
      .health()
      .then((h) => setOpen(h.curated_review_open !== false || view.case_id.includes('~')))
      .catch(() => setOpen(true));
  }, [view.case_id]);
  const [reviewer, setReviewer] = useState('');
  const [note, setNote] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);

  const send = async (a: Omit<ReviewAction, 'reviewer' | 'note'>) => {
    setBusy(true);
    setErr(null);
    try {
      const v = await api.reviewCase(view.case_id, { ...a, reviewer: reviewer.trim() || 'anonymous reviewer', note: note.trim() }, token.trim() ? { reviewToken: token.trim() } : undefined);
      onViewChange(v);
      setEditing(null);
    } catch (x) {
      setErr(x);
    } finally {
      setBusy(false);
    }
  };

  const review = view.package.expert_review;
  return (
    <Panel kicker="Expert review" title="Approve, revise or reject claims" right={<ReviewBadge status={view.review_status} />}>
      {open === false && (
        <div className="mb-3 space-y-2 text-sm text-on-surface-variant">
          <p>
            In this public demo, experts review the ready-made skills <strong className="text-on-surface">by invitation</strong>, so a visitor cannot approve them.
            Learners can practise normally while review is pending. Skills you create yourself can be reviewed by you.
          </p>
          <label className="flex flex-wrap items-center gap-2 text-xs">
            <span>Invited expert? Enter your invitation code:</span>
            <input
              value={token}
              onChange={(e) => setToken(e.target.value)}
              type="password"
              autoComplete="off"
              aria-label="Invitation code"
              className="bg-surface-dim border border-outline rounded-lg px-2 py-1 text-xs outline-none focus:border-caliper-cyan"
            />
          </label>
        </div>
      )}
      <div className={`space-y-3 text-xs ${open === false && !token.trim() ? 'opacity-50 pointer-events-none' : ''}`} aria-disabled={open === false && !token.trim()}>
        {review && (
          <div className="text-[11px] font-mono text-on-surface-variant">
            Last: {review.reviewer_name} · {review.status}{review.reviewed_at ? ` · ${review.reviewed_at.slice(0, 16).replace('T', ' ')}` : ''}{review.notes ? ` · "${review.notes}"` : ''}
          </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Reviewer name" className="bg-surface-dim border border-outline rounded-lg px-3 py-2 text-xs outline-none focus:border-caliper-cyan" />
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note (optional)" className="bg-surface-dim border border-outline rounded-lg px-3 py-2 text-xs outline-none focus:border-caliper-cyan" />
        </div>
        <ul className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
          {view.package.claims.map((c) => (
            <li key={c.claim_id} className="p-2 rounded border border-outline/60 bg-surface-dim">
              <div className="flex items-center justify-between gap-2">
                <code className="text-[11px] font-mono text-caliper-cyan">{c.claim_id}</code>
                <div className="flex gap-1">
                  <button disabled={busy} onClick={() => { setEditing(c.claim_id); setDraft(c.statement); }} className={btn.ghost} title="Revise claim text">
                    <Pencil className="w-3 h-3" /> revise
                  </button>
                  <button disabled={busy} onClick={() => send({ action: 'reject_claim', claim_id: c.claim_id })} className={`${btn.ghost} hover:text-divergence-crimson`} title="Reject claim">
                    <X className="w-3 h-3" /> reject
                  </button>
                </div>
              </div>
              {editing === c.claim_id ? (
                <div className="mt-1.5 space-y-1.5">
                  <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={3} className="w-full bg-background border border-outline rounded px-2 py-1.5 text-xs outline-none focus:border-caliper-cyan" />
                  <div className="flex gap-2">
                    <button disabled={busy || !draft.trim()} onClick={() => send({ action: 'revise_claim', claim_id: c.claim_id, new_statement: draft.trim() })} className={btn.secondary}>
                      Save revision
                    </button>
                    <button onClick={() => setEditing(null)} className={btn.ghost}>cancel</button>
                  </div>
                </div>
              ) : (
                <div className="text-[11px] text-on-surface-variant mt-0.5 line-clamp-2">{c.statement}</div>
              )}
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap gap-2">
          <button disabled={busy} onClick={() => send({ action: 'approve' })} className={btn.primary}>
            <Check className="w-3.5 h-3.5" /> Approve package
          </button>
          <button disabled={busy} onClick={() => send({ action: 'reject_package' })} className={`${btn.secondary} hover:border-divergence-crimson`}>
            Reject package
          </button>
        </div>
        {busy && <Spinner label="Saving review…" />}
        <ErrorNote error={err} />
        <p className="text-xs text-on-surface-variant">Review records a human decision on the extracted claims. It does not certify the source or the learner.</p>
      </div>
    </Panel>
  );
}
