/**
 * Composer wizard — "Create a new skill" (K8 §5).
 *
 * State machine: upload → perceiving → refused | needs_input | proposal → building → done.
 * All AI-perceived elements are labelled INFERRED. Nothing is "verified" or "certified".
 */

import React, { useCallback, useState } from 'react';
import type { CaseView, DraftView, SkillModel } from '../../api/types';
import { api } from '../../api/client';
import { ApiError } from '../../api/errors';
import { StepUpload, type UploadPayload } from './StepUpload';
import { StepPerceiving } from './StepPerceiving';
import { StepRefused } from './StepRefused';
import { StepNeedsInput } from './StepNeedsInput';
import { StepProposal } from './StepProposal';
import { StepBuilding } from './StepBuilding';

type WizardState =
  | { step: 'upload' }
  | { step: 'perceiving'; since: number; mime?: string }
  | { step: 'refused'; draft: DraftView }
  | { step: 'needs_input'; draft: DraftView }
  | { step: 'proposal'; draft: DraftView; edits: Partial<SkillModel> }
  | { step: 'building'; draft: DraftView; edits: Partial<SkillModel>; progress: number }
  | { step: 'done'; view: CaseView };

interface Props {
  /** Called when the wizard succeeds and should navigate to the new case. */
  onDone: (view: CaseView) => void;
  /** Called when the user cancels / starts over at the upload step. */
  onCancel: () => void;
}

export function ComposerWizard({ onDone, onCancel }: Props) {
  const [state, setState] = useState<WizardState>({ step: 'upload' });
  const [error, setError] = useState<unknown>(null);
  // Local preview of the uploaded source image (never sent anywhere; revoked on start over).
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);

  // ---------- Step 1: Upload → analyze ----------

  const handleUpload = useCallback(async (payload: UploadPayload) => {
    setError(null);
    setState({ step: 'perceiving', since: Date.now(), mime: payload.file.type });
    setSourceUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return payload.file.type.startsWith('image/') ? URL.createObjectURL(payload.file) : null;
    });
    try {
      const draft = await api.analyzeSource(
        payload.file,
        { title: payload.title, description: payload.description, rightsConfirmed: payload.rightsConfirmed },
        undefined,
      );
      if (draft.refused) {
        setState({ step: 'refused', draft });
      } else if (draft.proposal === null) {
        setState({ step: 'needs_input', draft });
      } else {
        setState({ step: 'proposal', draft, edits: {} });
      }
    } catch (e) {
      setError(e);
      setState({ step: 'upload' });
    }
  }, []);

  // ---------- Step 3b: Needs input → refine ----------

  const handleRefine = useCallback(async (draft: DraftView, title: string, description: string) => {
    setError(null);
    setState({ step: 'perceiving', since: Date.now() });
    try {
      const refined = await api.refineDraft(draft.draft_id, { title, description });
      if (refined.proposal === null) {
        setState({ step: 'needs_input', draft: refined });
      } else {
        setState({ step: 'proposal', draft: refined, edits: {} });
      }
    } catch (e) {
      setError(e);
      setState({ step: 'needs_input', draft });
    }
  }, []);

  // ---------- Step 3c → 4: Create skill ----------

  const handleCreate = useCallback(async (draft: DraftView, skillModel: SkillModel) => {
    if (!draft.proposal) return;
    setError(null);
    setState({ step: 'building', draft, edits: {}, progress: 0 });
    const p = draft.proposal;
    try {
      let prog = 0;
      const progTimer = setInterval(() => {
        prog = Math.min(prog + 0.15, 0.85);
        setState((s) => s.step === 'building' ? { ...s, progress: prog } : s);
      }, 400);
      const view = await api.createFromDraft(draft.draft_id, {
        title: p.title,
        skill_summary: p.skill_summary,
        domain: p.domain,
        transmission_mode: p.transmission_mode,
        learner_input_kinds: p.learner_input_kinds,
        goal_hint: p.goal_hint ?? null,
        skill_model: skillModel,
      });
      clearInterval(progTimer);
      setState({ step: 'done', view });
      // Auto-navigate after a brief moment
      setTimeout(() => onDone(view), 800);
    } catch (e) {
      setError(e);
      setState({ step: 'proposal', draft, edits: {} });
    }
  }, [onDone]);

  const reset = useCallback(() => {
    setError(null);
    setState({ step: 'upload' });
    setSourceUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return null;
    });
  }, []);

  // ---------- Render ----------

  if (state.step === 'upload') return <StepUpload onSubmit={handleUpload} onCancel={onCancel} error={error} />;
  if (state.step === 'perceiving') return <StepPerceiving since={state.since} mime={state.mime} />;
  if (state.step === 'refused') return <StepRefused draft={state.draft} onStartOver={reset} />;
  if (state.step === 'needs_input') return <StepNeedsInput draft={state.draft} onRefine={handleRefine} onStartOver={reset} error={error} />;
  if (state.step === 'proposal') return <StepProposal draft={state.draft} sourceUrl={sourceUrl} onCreate={handleCreate} onStartOver={reset} error={error} />;
  if (state.step === 'building') return <StepBuilding progress={state.progress} />;
  if (state.step === 'done') return (
    <div className="flex flex-col items-center gap-4 py-12 text-center animate-fade-in">
      <div className="text-transmission-emerald text-4xl font-serif">Skill created</div>
      <p className="text-sm text-on-surface-variant">Navigating to your new skill…</p>
    </div>
  );
  return null;
}
