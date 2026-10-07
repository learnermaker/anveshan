/**
 * Source view for universal (composed) cases (K8 §6).
 *
 * Shows: reference media, property boxes/step strip/transcript,
 * claims list with certainty badges, review panel, banner.
 * All AI-perceived elements are labelled with plain language in learner mode.
 */

import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, Check, Pencil, RefreshCw, Search, X } from 'lucide-react';
import type { KnowledgeClaim } from '../../types/contracts';
import type { CaseView, ReviewAction, SourceRecord, UniversalUiView } from '../../api/types';
import { api } from '../../api/client';
import { Badge, btn, ErrorNote, MockBadge, Panel, ReviewBadge, SourceLabelBadge, Spinner, VerificationBadge } from '../ui';
import { TrustLine } from '../TrustLine';
import { pointNumber } from '../StepsList';
import { DEBUG } from '../../api/debug';
import { MessageSquareQuote } from 'lucide-react';
import type { QueryAnswer } from '../../api/types';

interface Props {
  view: CaseView;
  onViewChange: (v: CaseView) => void;
  onReload: () => void;
  onEnterPractice: () => void;
  onBack: () => void;
  /** K9: the creator's "Your skill" panel (built by P3), shown at the top of the right column for the owner */
  ownerSlot?: React.ReactNode;
}

function SourceMedia({ caseId, sources }: { caseId: string; sources: SourceRecord[] }) {
  const usable = sources.filter((s) => s.used_by_system !== false && s.role !== 'held_out_reference');
  if (usable.length === 0) return null;
  return (
    <div className="space-y-3">
      {usable.map((s) => {
        const url = api.mediaUrl(caseId, s.source_id);
        const mime = s.mime_type ?? '';
        return (
          <div key={s.source_id} className="space-y-1">
            {mime.startsWith('image/') && <img src={url} alt={`Source ${s.source_id}`} className="max-h-80 w-auto rounded border border-outline bg-surface-dim" />}
            {mime.startsWith('audio/') && <audio controls src={url} className="w-full" aria-label={`Source audio ${s.source_id}`} />}
            {mime.startsWith('video/') && <video controls src={url} className="w-full max-h-96 rounded border border-outline bg-black" aria-label={`Source video ${s.source_id}`} />}
            {DEBUG && <div className="text-[11px] font-mono text-on-surface-variant">{s.source_id} · {mime}</div>}
          </div>
        );
      })}
    </div>
  );
}

function GoalStateSection({ ui, caseId, reviewed }: { ui: UniversalUiView; caseId: string; reviewed: boolean }) {
  const props = ui.goal_state ?? [];
  const steps = ui.steps ?? [];
  const transcript = ui.transcript;

  return (
    <div className="space-y-4">
      {transcript && (
        <div className="p-3 rounded-lg border border-outline bg-surface-dim">
          <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-1">
            {DEBUG ? 'Transcript (INFERRED)' : 'What was said (AI transcript)'}
          </div>
          <p className="font-mono text-sm text-on-surface" data-plain-exempt>"{transcript}"</p>
        </div>
      )}

      {props.length > 0 && (
        <div>
          <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-2">
            {DEBUG ? 'Goal properties' : 'What the finished result should look like'}
          </div>
          <ul className="space-y-1.5">
            {props.filter((p) => p.keep !== false).map((p) => (
              <li key={p.prop_id} className="flex items-start gap-2 text-[11px]">
                <VerificationBadge state={p.certainty as 'observed' | 'inferred' | 'unverified' ?? 'inferred'} />
                <span className="text-on-surface" data-plain-exempt>{p.statement}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {steps.length > 0 && (
        <div>
          <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-2">Steps</div>
          <ul className="space-y-2">
            {steps.map((s, stepIdx) => (
              <li key={s.step_id} className="flex items-start gap-3">
                {s.keyframe_asset ? (
                  <img src={api.goalAssetUrl(caseId, s.keyframe_asset)} alt={s.name} className="w-28 shrink-0 aspect-video object-cover rounded border border-outline bg-surface-dim" />
                ) : (
                  <div className="w-28 shrink-0 aspect-video bg-surface-dim border border-outline rounded flex items-center justify-center text-[11px] font-mono text-on-surface-variant">
                    Step {stepIdx + 1}
                  </div>
                )}
                <div className="min-w-0 space-y-1">
                  <div className="text-[11px] text-on-surface" data-plain-exempt>
                    {stepIdx + 1}. {s.name}
                    {s.critical && <span className="text-divergence-crimson"> (key step)</span>}
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {s.start_sec != null && (
                      <span className="text-[10px] font-mono text-on-surface-variant">{s.start_sec.toFixed(1)}–{(s.end_sec ?? s.start_sec).toFixed(1)} s</span>
                    )}
                    {!reviewed && <VerificationBadge state="inferred" />}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {DEBUG && ui.structures.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {ui.structures.map((s) => <Badge key={s} tone="cyan">{s}</Badge>)}
        </div>
      )}
    </div>
  );
}

// Inline review panel (subset of HeroSourceView's review functionality)
function ReviewPanel({ view, onViewChange }: { view: CaseView; onViewChange: (v: CaseView) => void }) {
  const [reviewer, setReviewer] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);

  const act = async (action: ReviewAction['action']) => {
    if (!reviewer.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const updated = await api.reviewCase(view.case_id, { action, reviewer: reviewer.trim(), note });
      onViewChange(updated);
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <ReviewBadge status={view.review_status} />
        <span className="text-[11px] text-on-surface-variant">{view.review_status === 'approved' ? 'AI-perceived elements approved for use.' : 'Pending expert review of AI-perceived elements.'}</span>
      </div>
      <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Your name (reviewer)" className="w-full bg-surface-dim border border-outline rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-caliper-cyan" aria-label="Reviewer name" />
      <textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Optional note" rows={2} className="w-full bg-surface-dim border border-outline rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-caliper-cyan resize-none" aria-label="Review note" />
      <div className="flex flex-wrap gap-2">
        <button disabled={busy || !reviewer.trim()} onClick={() => void act('approve')} className={`${btn.primary} text-[10px] py-1.5`}><Check className="w-3 h-3" /> Approve</button>
        <button disabled={busy || !reviewer.trim()} onClick={() => void act('reject_package')} className={`${btn.secondary} text-[10px] py-1.5`}><X className="w-3 h-3" /> Reject</button>
      </div>
      <ErrorNote error={err} />
    </div>
  );
}

export function UniversalSourceView({ view, onViewChange, onReload, onEnterPractice, onBack, ownerSlot }: Props) {
  const ui = view.goal.ui_view as UniversalUiView;
  const claims = view.package.claims;
  const profile = view.profile;

  const [queryText, setQueryText] = useState('');
  const [queryAnswer, setQueryAnswer] = useState<QueryAnswer | null>(null);
  const [queryBusy, setQueryBusy] = useState(false);
  const [queryErr, setQueryErr] = useState<unknown>(null);
  const [editClaim, setEditClaim] = useState<{ id: string; text: string } | null>(null);
  const [reviseErr, setReviseErr] = useState<unknown>(null);

  const firstSource = view.sources[0];

  const doQuery = async () => {
    if (!queryText.trim()) return;
    setQueryBusy(true);
    setQueryErr(null);
    try {
      const r = await api.queryCase(view.case_id, queryText);
      setQueryAnswer(r);
    } catch (e) {
      setQueryErr(e);
    } finally {
      setQueryBusy(false);
    }
  };

  const doRevise = async (claimId: string, newStatement: string) => {
    setReviseErr(null);
    try {
      const updated = await api.reviewCase(view.case_id, { action: 'revise_claim', reviewer: 'editor', note: '', claim_id: claimId, new_statement: newStatement });
      onViewChange(updated);
    } catch (e) {
      setReviseErr(e);
    } finally {
      setEditClaim(null);
    }
  };

  return (
    <div className="flex flex-col gap-5 w-full animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          <button onClick={onBack} className={btn.ghost}><ArrowLeft className="w-3.5 h-3.5" /> All skills</button>
          <div className="text-xs font-mono uppercase tracking-widest text-caliper-cyan font-bold">Step 1 of 3 · Learn from the source</div>
          <h1 className="font-serif text-2xl sm:text-3xl text-on-surface" data-plain-exempt>{view.title}</h1>
          {!DEBUG ? (
            <TrustLine view={view} />
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-1.5">
                <SourceLabelBadge label={view.runtime_label} />
                <ReviewBadge status={view.review_status} />
                <Badge tone="cyan">UNIVERSAL</Badge>
                <MockBadge />
              </div>
              <p className="text-[11px] font-mono text-cadmium-amber">Composed skill · AI-perceived elements are INFERRED until reviewed by an expert.</p>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          {DEBUG && (
            <button onClick={onReload} className={btn.secondary} title="Reload case from the service"><RefreshCw className="w-3.5 h-3.5" /> Reload</button>
          )}
          <button onClick={onEnterPractice} className={btn.primary}>Start practising <ArrowRight className="w-3.5 h-3.5" /></button>
        </div>
      </div>

      {DEBUG && [...new Set([...(view.warnings ?? []), ...(view.goal.warnings ?? [])])].map((w, i) => (
        <p key={i} className="text-[11px] font-mono text-cadmium-amber">⚠ {w}</p>
      ))}

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] gap-5">
        <div className="space-y-5 min-w-0">
          <Panel kicker="Source" title="Uploaded source media">
            <SourceMedia caseId={view.case_id} sources={view.sources} />
          </Panel>
          {!DEBUG && firstSource && (
            <p className="text-xs text-on-surface-variant px-1">
              Source: {firstSource.attribution} · {firstSource.license}
            </p>
          )}

          <Panel kicker={DEBUG ? 'Goal state' : "What you'll learn"} title={<span data-plain-exempt>{view.package.title}</span>}>
            <GoalStateSection ui={ui} caseId={view.case_id} reviewed={view.review_status === 'approved'} />
          </Panel>

          {DEBUG && profile && (
            <Panel kicker="Skill profile" title={`Domain: ${profile.domain}`}>
              <div className="space-y-2 text-[11px]">
                <p className="text-on-surface">{profile.skill_summary}</p>
                <div className="flex flex-wrap gap-1">
                  <span className="font-mono text-on-surface-variant">Mode:</span>
                  <Badge tone="muted">{profile.transmission_mode}</Badge>
                  <span className="font-mono text-on-surface-variant">Learner inputs:</span>
                  {profile.learner_input_kinds.map((k) => <Badge key={k} tone="muted">{k}</Badge>)}
                </div>
              </div>
            </Panel>
          )}

          {DEBUG ? (
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
              <p className="mt-2 text-[10px] text-on-surface-variant">Consent: {view.package.consent.contributor_name} — {view.package.consent.consent_scope}</p>
            </Panel>
          ) : null}
        </div>

        <div className="space-y-5 min-w-0">
          {ownerSlot}

          {DEBUG && (
            <Panel kicker="Knowledge package" title={`Claims (${claims.length})`}>
              <ul className="space-y-2 text-[11px]">
                {claims.map((c: KnowledgeClaim) => (
                  <li key={c.claim_id} className="flex items-start gap-2">
                    <VerificationBadge state={c.is_observed ? 'observed' : 'inferred'} />
                    {editClaim?.id === c.claim_id ? (
                      <div className="flex-1 flex gap-1">
                        <input value={editClaim!.text} onChange={(e) => setEditClaim({ id: c.claim_id, text: e.target.value })} className="flex-1 bg-surface-dim border border-outline rounded px-2 py-0.5 text-[10px] font-mono outline-none focus:border-caliper-cyan" aria-label="Edit claim" />
                        <button onClick={() => void doRevise(c.claim_id, editClaim!.text)} className={`${btn.primary} py-0.5 text-[11px]`}>Save</button>
                        <button onClick={() => setEditClaim(null)} className={`${btn.ghost}`}><X className="w-3 h-3" /></button>
                      </div>
                    ) : (
                      <>
                        <span className="flex-1 text-on-surface">{c.statement}</span>
                        <button onClick={() => setEditClaim({ id: c.claim_id, text: c.statement })} className={`${btn.ghost} shrink-0`} title="Edit claim" aria-label="Edit claim"><Pencil className="w-3 h-3" /></button>
                      </>
                    )}
                  </li>
                ))}
              </ul>
              {reviseErr != null && <ErrorNote error={reviseErr} />}
            </Panel>
          )}

          {/* Query / Ask — always shown */}
          <Panel kicker="Ask" title="Ask about this skill">
            <div className="flex gap-2">
              <input
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && void doQuery()}
                placeholder="e.g. What is the most important step?"
                className="flex-1 bg-surface-dim border border-outline rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-caliper-cyan"
                aria-label="Query text"
              />
              <button onClick={() => void doQuery()} disabled={queryBusy} className={btn.secondary} aria-label="Submit query">
                <Search className="w-3.5 h-3.5" />
              </button>
            </div>
            {queryBusy && <Spinner label="Looking in the source…" />}
            {queryAnswer && (
              <div className={`mt-2 p-3 rounded-lg border text-xs ${queryAnswer.sufficient ? 'border-outline bg-surface-dim' : 'border-cadmium-amber/40 bg-cadmium-amber/10'}`}>
                {!queryAnswer.sufficient && <p className="mb-1 text-cadmium-amber text-xs">The source does not say.</p>}
                <div className="flex gap-2">
                  <MessageSquareQuote className="w-4 h-4 text-on-surface-variant shrink-0" />
                  <p className="text-on-surface leading-relaxed" data-plain-exempt>{queryAnswer.answer}</p>
                </div>
                {queryAnswer.cited_claim_ids.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5 items-center">
                    <span className="text-[10px] font-mono text-on-surface-variant">From:</span>
                    {queryAnswer.cited_claim_ids.map((id) => {
                      const n = pointNumber(claims, id);
                      return (
                        <span key={id} className="text-[10px] font-mono text-caliper-cyan">
                          {n != null ? `point ${n}` : DEBUG ? id : 'a step'}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
            <ErrorNote error={queryErr} />
          </Panel>

          {DEBUG && (
            <Panel kicker="Expert review" title="Review AI-perceived elements">
              <ReviewPanel view={view} onViewChange={onViewChange} />
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
