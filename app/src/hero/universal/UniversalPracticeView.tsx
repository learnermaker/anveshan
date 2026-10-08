/**
 * Practice view for universal (composed) cases (K8 §6).
 * Upload controls for each allowed learner kind.
 * If "trace" is allowed, reuses KolamCanvas.
 * Relevance refusals (INVALID_INPUT "doesn't look like an attempt") are shown inline.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, FileUp, Play, RotateCcw, Send } from 'lucide-react';
import type { AttemptKind, AttemptResult, CaseView } from '../../api/types';
import { api, type AttemptUpload } from '../../api/client';
import { API_BASE } from '../../api/runtime';
import { ApiError } from '../../api/errors';
import { AttemptProgress, ReviewNote, TaskInstructions } from '../Guidance';
import { AttemptResultView } from '../results/AttemptResultView';
import type { HeroSession, LocalAttemptMedia } from '../session';
import { sampleMedia } from '../session';
import { Badge, btn, ErrorNote, KeyHint, Panel, ProgressBar, ReviewBadge, SourceLabelBadge, Spinner } from '../ui';
import { TrustLine } from '../TrustLine';
import { KolamCanvas, buildRasterPng, buildTraceJson, type Stroke } from '../kolam/KolamCanvas';
import type { UniversalUiView } from '../../api/types';
import { lineArtToKolamUi } from './lineArt';
import { DEBUG } from '../../api/debug';
import { attemptLabel } from '../../copy/plain';
import type { SampleAttempt } from '../../api/types-product';

interface Props {
  view: CaseView;
  session: HeroSession | null;
  onSessionChange: (s: HeroSession | null) => void;
  onComplete: () => void;
  onBack: () => void;
}

type Phase = { kind: 'idle' } | { kind: 'uploading'; progress: number } | { kind: 'evaluating'; since: number };

export function UniversalPracticeView({ view, session, onSessionChange, onComplete, onBack }: Props) {
  const [learner, setLearner] = useState('');
  const [err, setErr] = useState<unknown>(null);
  const [phase, setPhase] = useState<Phase>({ kind: 'idle' });
  const [selected, setSelected] = useState(-1);
  const [showCapture, setShowCapture] = useState(true);
  const [completing, setCompleting] = useState(false);
  const [relevanceRefusal, setRelevanceRefusal] = useState<string | null>(null);

  const profile = view.profile;
  const allowedKinds: AttemptKind[] = (profile?.learner_input_kinds ?? ['image']) as AttemptKind[];
  const attempts = session?.attempts ?? [];
  const n = attempts.length;
  const shown = attempts[selected >= 0 && selected < n ? selected : n - 1];
  const canSubmit = n < 2;
  const tryLabel = n === 0 ? attemptLabel(1) : attemptLabel(2);

  const start = async () => {
    setErr(null);
    try {
      const name = learner.trim() || 'Guest';
      const s = await api.createSession(view.case_id, name);
      onSessionChange({ caseId: view.case_id, sessionId: s.session_id, learnerName: name, attempts: [], result: null });
      setShowCapture(true);
    } catch (x) {
      setErr(x);
    }
  };

  const submit = async (upload: AttemptUpload, media: LocalAttemptMedia) => {
    if (!session) return;
    setErr(null);
    setRelevanceRefusal(null);
    setPhase({ kind: 'uploading', progress: 0 });
    try {
      let switched = false;
      const result = await api.submitAttempt(session.sessionId, upload, (p) => {
        if (p >= 1 && !switched) {
          switched = true;
          setPhase({ kind: 'evaluating', since: Date.now() });
        } else if (!switched) setPhase({ kind: 'uploading', progress: p });
      });
      onSessionChange({ ...session, attempts: [...session.attempts, { result, media }] });
      setShowCapture(false);
    } catch (x) {
      // Relevance refusal: show inline, don't count as an attempt
      if (x instanceof ApiError && x.category === 'INVALID_INPUT' && x.message.toLowerCase().includes("look like an attempt")) {
        setRelevanceRefusal(x.message);
      } else {
        setErr(x);
      }
    } finally {
      setPhase({ kind: 'idle' });
    }
  };

  const submitSample = async (sample: SampleAttempt) => {
    let sid = session?.sessionId;
    let currentSession = session;
    if (!currentSession) {
      setErr(null);
      try {
        const name = 'Guest';
        const s = await api.createSession(view.case_id, name);
        currentSession = { caseId: view.case_id, sessionId: s.session_id, learnerName: name, attempts: [], result: null };
        onSessionChange(currentSession);
        sid = s.session_id;
      } catch (x) {
        setErr(x);
        return;
      }
    }
    if (!sid) return;
    setErr(null);
    setRelevanceRefusal(null);
    setPhase({ kind: 'evaluating', since: Date.now() });
    try {
      const result = await api.submitSampleAttempt(sid, sample.sample_id);
      const media = await sampleMedia(sample);
      onSessionChange({ ...currentSession!, attempts: [...(currentSession!.attempts), { result, media }] });
      setShowCapture(false);
    } catch (x) {
      setErr(x);
    } finally {
      setPhase({ kind: 'idle' });
    }
  };

  const complete = async () => {
    if (!session) return;
    setCompleting(true);
    try {
      const result = await api.completeSession(session.sessionId);
      onSessionChange({ ...session, result });
      onComplete();
    } catch (x) {
      setErr(x);
    } finally {
      setCompleting(false);
    }
  };

  return (
    <div className="flex flex-col gap-5 w-full animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          <button onClick={onBack} className={btn.ghost}><ArrowLeft className="w-3.5 h-3.5" /> Back to Learn</button>
          <div className="text-xs font-mono uppercase tracking-widest text-cadmium-amber font-bold">Step 2 of 3 · Practise · {view.task.title}</div>
          <h1 className="font-serif text-2xl text-on-surface" data-plain-exempt>{view.title}</h1>
          {!DEBUG ? (
            <TrustLine view={view} />
          ) : (
            <div className="flex flex-wrap gap-1.5">
              <SourceLabelBadge label={view.runtime_label} />
              <ReviewBadge status={view.review_status} />
              {session && <Badge tone="muted" title={`Session ${session.sessionId}`}>Learner: {session.learnerName}</Badge>}
            </div>
          )}
          {!DEBUG && session && (
            <Badge tone="muted" title="Your name for this practice">
              Learner: {session.learnerName}
            </Badge>
          )}
        </div>
        {session && (
          <div className="flex flex-wrap gap-2">
            <button onClick={() => onSessionChange(null)} className={btn.secondary} title="Discard these attempts and start again">Start over</button>
            {n >= 2 && (
              <button onClick={complete} disabled={completing} className={btn.primary}>
                {completing ? 'Saving the record…' : 'See what changed'} <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}
      </div>

      <ReviewNote status={view.review_status} />

      <AttemptProgress attempts={n} started={Boolean(session)} completing={completing} retryOpen={canSubmit && showCapture} onRetry={() => setShowCapture(true)} onComplete={() => void complete()} />

      <ErrorNote error={err} />

      {/* Relevance refusal — shown inline, not counted as an attempt */}
      {relevanceRefusal && (
        <div role="alert" className="p-3 rounded-lg border border-cadmium-amber/40 bg-cadmium-amber/10 text-sm text-on-surface">
          <span className="font-semibold text-cadmium-amber">Not counted as an attempt.</span> {relevanceRefusal}. Please upload an attempt at this skill.
        </div>
      )}

      {!session ? (
        <Panel kicker="Start" title="Start practising">
          <div className="flex flex-col sm:flex-row gap-2 max-w-lg">
            <input value={learner} onChange={(e) => setLearner(e.target.value)} placeholder="Your name (optional, shown in the record)" className="flex-1 bg-surface-dim border border-outline rounded-lg px-3 py-2 text-sm outline-none focus:border-caliper-cyan" aria-label="Your name (optional)" />
            <button onClick={() => void start()} className={btn.primary}><Play className="w-3.5 h-3.5" /> Start practising</button>
          </div>
          <div className="mt-4"><TaskInstructions text={view.task.instructions} claims={view.package.claims} /></div>
        </Panel>
      ) : (
        <>
          {canSubmit && showCapture && (
            <Panel kicker={n === 0 ? 'First try' : 'Second try'} title={view.task.title}>
              <details className="mb-4" open={n === 0}>
                <summary className="cursor-pointer text-sm font-semibold text-on-surface">Task steps</summary>
                <div className="mt-2"><TaskInstructions text={view.task.instructions} claims={view.package.claims} /></div>
              </details>
              <div className="mb-3"><KeyHint /></div>
              <UniversalCapture view={view} allowedKinds={allowedKinds} busy={phase.kind !== 'idle'} onSubmit={submit} />
              <div className="mt-4">
                {phase.kind === 'uploading' && <ProgressBar value={phase.progress} label="Uploading attempt" />}
                {phase.kind === 'evaluating' && <Spinner label={`Evaluating… ${((Date.now() - phase.since) / 1000).toFixed(0)} s elapsed · videos usually take 20–70 s, images and audio 5–20 s`} />}
              </div>
              {/* Sample picker (WI-3.1) */}
              <SamplePicker caseId={view.case_id} tryLabel={tryLabel} noSubmitsYet={n === 0} onUseSample={submitSample} busy={phase.kind !== 'idle'} />
            </Panel>
          )}

          {n > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {attempts.map((a, i) => (
                <button key={i} onClick={() => setSelected(i)} className={`px-3 py-1 rounded-md border text-[11px] font-mono ${a === shown ? 'border-cadmium-amber text-cadmium-amber bg-cadmium-amber/10' : 'border-outline text-on-surface-variant'}`}>
                  {attemptLabel(i + 1)} · {a.result.evaluation.total_score.toFixed(1)}
                </button>
              ))}
              {canSubmit && !showCapture && (
                <button onClick={() => setShowCapture(true)} className={btn.primary}><RotateCcw className="w-3.5 h-3.5" /> Retry the whole task</button>
              )}
            </div>
          )}

          {shown && <AttemptResultView view={view} result={shown.result} media={shown.media} />}

          {n > 0 && (
            <AttemptProgress attempts={n} started completing={completing} retryOpen={canSubmit && showCapture} onRetry={() => setShowCapture(true)} onComplete={() => void complete()} />
          )}
        </>
      )}
    </div>
  );
}

/** Sample attempt picker: "No materials? Try a sample attempt" */
function SamplePicker({ caseId, tryLabel, noSubmitsYet, onUseSample, busy }: { caseId: string; tryLabel: string; noSubmitsYet: boolean; onUseSample: (sample: SampleAttempt) => void; busy: boolean }) {
  const [samples, setSamples] = useState<SampleAttempt[] | null>(null);
  const [err, setErr] = useState<unknown>(null);

  useEffect(() => {
    api.listSamples(caseId).then(setSamples).catch(setErr);
  }, [caseId]);

  if (!samples || samples.length === 0) return null;

  return (
    <details className="mt-4" open={noSubmitsYet}>
      <summary className="cursor-pointer text-sm text-on-surface-variant font-semibold select-none">
        No materials? Try a sample attempt
      </summary>
      <div className="mt-3 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {samples.map((s) => (
            <div key={s.sample_id} className="p-3 rounded-lg border border-outline bg-surface-dim space-y-2">
              <div className="flex flex-wrap items-start gap-2">
                <span className="font-semibold text-sm text-on-surface flex-1">{s.label}</span>
                {s.synthetic && <Badge tone="crimson">Synthetic sample</Badge>}
              </div>
              <p className="text-xs text-on-surface-variant" data-plain-exempt>{s.description}</p>
              {s.credit && <p className="text-xs text-on-surface-variant" data-plain-exempt>{s.credit}</p>}
              {s.preview_url && (
                <div className="mt-1">
                  {s.attempt_kind === 'image' && (
                    <img src={`${API_BASE}${s.preview_url}`} alt={s.label} className="max-h-32 rounded border border-outline" />
                  )}
                  {s.attempt_kind === 'audio' && (
                    <audio controls src={`${API_BASE}${s.preview_url}`} className="w-full" aria-label={s.label} />
                  )}
                  {s.attempt_kind === 'video' && (
                    <video controls src={`${API_BASE}${s.preview_url}`} className="w-full max-h-32 rounded border border-outline bg-black" aria-label={s.label} />
                  )}
                </div>
              )}
              <button
                type="button"
                disabled={busy}
                onClick={() => onUseSample(s)}
                className={btn.secondary}
              >
                Use this as my {tryLabel}
              </button>
            </div>
          ))}
        </div>
        <p className="text-xs text-on-surface-variant">
          Samples let you see the feedback without your own materials. Your real practice counts more.
        </p>
        <ErrorNote error={err} />
      </div>
    </details>
  );
}

function FilePick({ accept, label, file, onFile, disabled }: { accept: string; label: string; file: File | null; onFile: (f: File | null) => void; disabled?: boolean }) {
  return (
    <label className={`flex items-center gap-3 p-3 rounded-lg border border-dashed ${disabled ? 'opacity-50' : 'hover:border-cadmium-amber cursor-pointer'} border-outline bg-surface-dim`}>
      <FileUp className="w-5 h-5 text-cadmium-amber shrink-0" />
      <div className="min-w-0">
        <div className="text-[11px] font-mono text-on-surface">{label}</div>
        <div className="text-xs text-on-surface-variant truncate">{file ? `${file.name} · ${(file.size / 1e6).toFixed(2)} MB` : 'choose a file'}</div>
      </div>
      <input type="file" accept={accept} className="hidden" disabled={disabled} onChange={(e) => onFile(e.target.files?.[0] ?? null)} />
    </label>
  );
}

function UniversalCapture({ view, allowedKinds: allowedKindsIn, busy, onSubmit }: { view: CaseView; allowedKinds: AttemptKind[]; busy: boolean; onSubmit: (u: AttemptUpload, m: LocalAttemptMedia) => void }) {
  const lineArtPayload = view.profile?.skill_model?.specialists?.['line_art'];
  const kolamUi = useMemo(() => lineArtToKolamUi(lineArtPayload), [lineArtPayload]);
  // Trace needs a real drawing canvas; without one, do not offer it.
  const allowedKinds = useMemo(() => allowedKindsIn.filter((k) => k !== 'trace' || kolamUi !== null), [allowedKindsIn, kolamUi]);
  const [activeKind, setActiveKind] = useState<AttemptKind>(allowedKinds[0] ?? 'image');
  const [file, setFile] = useState<File | null>(null);
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const startRef = useRef<number | null>(null);

  const MAX_MB = 30 * 1024 * 1024;
  const ui = view.goal.ui_view as UniversalUiView;

  const handleFile = (f: File | null) => {
    setFile(f);
    if (ui.steps) {
      // preview not needed for video
    }
  };

  const ACCEPT: Record<AttemptKind, string> = {
    image: 'image/*',
    trace: 'image/*',
    audio: 'audio/*',
    video: 'video/*',
  };

  if (activeKind === 'trace' && kolamUi) {
    return (
      <div className="space-y-2">
        <div className="flex gap-2">
          {allowedKinds.map((k) => (
            <button key={k} onClick={() => setActiveKind(k)} className={`px-3 py-1 rounded-md border text-[11px] font-mono uppercase ${activeKind === k ? 'border-cadmium-amber text-cadmium-amber' : 'border-outline text-on-surface-variant'}`}>{k}</button>
          ))}
        </div>
        <KolamCanvas ui={kolamUi} strokes={strokes} onStrokesChange={setStrokes} startRef={startRef} disabled={busy} />
        <button
          disabled={busy || !strokes.length}
          onClick={async () => {
            const json = buildTraceJson(kolamUi, view.case_id, view.goal.version, strokes, startRef.current);
            const raster = await buildRasterPng(kolamUi, strokes);
            onSubmit({ kind: 'trace', file: new Blob([json], { type: 'application/json' }), fileName: 'trace.json', raster }, { kind: 'trace', strokes });
            setStrokes([]);
          }}
          className={btn.primary}
        >
          <Send className="w-3.5 h-3.5" /> Submit drawing
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {allowedKinds.length > 1 && (
        <div className="flex gap-2">
          {allowedKinds.map((k) => (
            <button key={k} onClick={() => { setActiveKind(k); setFile(null); }} className={`px-3 py-1 rounded-md border text-[11px] font-mono uppercase ${activeKind === k ? 'border-cadmium-amber text-cadmium-amber' : 'border-outline text-on-surface-variant'}`}>{k}</button>
          ))}
        </div>
      )}
      <FilePick accept={ACCEPT[activeKind] ?? '*/*'} label={`Your ${activeKind} attempt`} file={file} onFile={handleFile} disabled={busy} />
      {file && file.size > MAX_MB && <p className="text-[11px] font-mono text-divergence-crimson">File exceeds 30 MB limit.</p>}
      {file && (
        <button
          disabled={busy || file.size > MAX_MB}
          onClick={() => {
            const url = URL.createObjectURL(file);
            onSubmit({ kind: activeKind, file, fileName: file.name }, { kind: activeKind, url, fileName: file.name });
          }}
          className={btn.primary}
        >
          <Send className="w-3.5 h-3.5" /> Submit {activeKind}
        </button>
      )}
    </div>
  );
}
