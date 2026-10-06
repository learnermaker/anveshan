/**
 * Practice view for universal (composed) cases (K8 §6).
 * Upload controls for each allowed learner kind.
 * If "trace" is allowed, reuses KolamCanvas.
 * Relevance refusals (INVALID_INPUT "doesn't look like an attempt") are shown inline.
 */

import React, { useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, FileUp, Play, RotateCcw, Send } from 'lucide-react';
import type { AttemptKind, CaseView } from '../../api/types';
import { api, type AttemptUpload } from '../../api/client';
import { ApiError } from '../../api/errors';
import { AttemptResultView } from '../results/AttemptResultView';
import type { HeroSession, LocalAttemptMedia } from '../session';
import { Badge, btn, ErrorNote, MockBadge, Panel, ProgressBar, ReviewBadge, SourceLabelBadge, Spinner } from '../ui';
import { KolamCanvas, buildRasterPng, buildTraceJson, type Stroke } from '../kolam/KolamCanvas';
import type { KolamUiView, UniversalUiView } from '../../api/types';

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

  const start = async () => {
    setErr(null);
    try {
      const s = await api.createSession(view.case_id, learner.trim() || 'Learner');
      onSessionChange({ caseId: view.case_id, sessionId: s.session_id, learnerName: learner.trim() || 'Learner', attempts: [], result: null });
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
          <button onClick={onBack} className={btn.ghost}><ArrowLeft className="w-3.5 h-3.5" /> Source</button>
          <div className="text-[10px] font-mono uppercase tracking-widest text-cadmium-amber font-bold">02 // Practice · {view.task.title}</div>
          <h1 className="font-serif text-2xl text-on-surface">{view.title}</h1>
          <div className="flex flex-wrap gap-1.5">
            <SourceLabelBadge label={view.runtime_label} />
            <ReviewBadge status={view.review_status} />
            {session && <Badge tone="muted">session {session.sessionId}</Badge>}
            <MockBadge />
          </div>
        </div>
        {session && (
          <div className="flex flex-wrap gap-2">
            <button onClick={() => onSessionChange(null)} className={btn.secondary}>New session</button>
            {n >= 2 && (
              <button onClick={complete} disabled={completing} className={btn.primary}>
                {completing ? 'Recording…' : 'Complete transmission'} <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}
      </div>

      <ErrorNote error={err} />

      {/* Relevance refusal — shown inline, not counted as an attempt */}
      {relevanceRefusal && (
        <div className="p-3 rounded-lg border border-cadmium-amber/40 bg-cadmium-amber/10 text-[11px] font-mono text-cadmium-amber">
          ⚠ This upload doesn't look like a valid attempt: {relevanceRefusal}. Please try a different file.
        </div>
      )}

      {!session ? (
        <Panel kicker="Start" title="Start a practice session">
          <div className="flex flex-col sm:flex-row gap-2 max-w-lg">
            <input value={learner} onChange={(e) => setLearner(e.target.value)} placeholder="Learner name" className="flex-1 bg-surface-dim border border-outline rounded-lg px-3 py-2 text-xs outline-none focus:border-caliper-cyan" aria-label="Learner name" />
            <button onClick={() => void start()} className={btn.primary}><Play className="w-3.5 h-3.5" /> Start session</button>
          </div>
          <p className="mt-3 text-xs text-on-surface-variant leading-relaxed">{view.task.instructions}</p>
        </Panel>
      ) : (
        <>
          {canSubmit && showCapture && (
            <Panel kicker={n === 0 ? 'Attempt 1 · baseline' : 'Attempt 2 · retry'} title={view.task.title}>
              <p className="text-xs text-on-surface-variant leading-relaxed mb-4">{view.task.instructions}</p>
              <UniversalCapture view={view} allowedKinds={allowedKinds} busy={phase.kind !== 'idle'} onSubmit={submit} />
              <div className="mt-4">
                {phase.kind === 'uploading' && <ProgressBar value={phase.progress} label="Uploading attempt" />}
                {phase.kind === 'evaluating' && <Spinner label={`Evaluating… ${((Date.now() - phase.since) / 1000).toFixed(0)} s`} />}
              </div>
            </Panel>
          )}

          {n > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {attempts.map((a, i) => (
                <button key={i} onClick={() => setSelected(i)} className={`px-3 py-1 rounded-md border text-[11px] font-mono ${a === shown ? 'border-cadmium-amber text-cadmium-amber bg-cadmium-amber/10' : 'border-outline text-on-surface-variant'}`}>
                  {a.result.attempt.attempt_type.toUpperCase()} · {a.result.evaluation.total_score.toFixed(1)}
                </button>
              ))}
              {canSubmit && !showCapture && (
                <button onClick={() => setShowCapture(true)} className={btn.primary}><RotateCcw className="w-3.5 h-3.5" /> Retry</button>
              )}
            </div>
          )}

          {shown && <AttemptResultView view={view} result={shown.result} media={shown.media} />}
        </>
      )}
    </div>
  );
}

function FilePick({ accept, label, file, onFile, disabled }: { accept: string; label: string; file: File | null; onFile: (f: File | null) => void; disabled?: boolean }) {
  return (
    <label className={`flex items-center gap-3 p-3 rounded-lg border border-dashed ${disabled ? 'opacity-50' : 'hover:border-cadmium-amber cursor-pointer'} border-outline bg-surface-dim`}>
      <FileUp className="w-5 h-5 text-cadmium-amber shrink-0" />
      <div className="min-w-0">
        <div className="text-[11px] font-mono text-on-surface">{label}</div>
        <div className="text-[10px] text-on-surface-variant truncate">{file ? `${file.name} · ${(file.size / 1e6).toFixed(2)} MB` : 'choose a file'}</div>
      </div>
      <input type="file" accept={accept} className="hidden" disabled={disabled} onChange={(e) => onFile(e.target.files?.[0] ?? null)} />
    </label>
  );
}

function UniversalCapture({ view, allowedKinds, busy, onSubmit }: { view: CaseView; allowedKinds: AttemptKind[]; busy: boolean; onSubmit: (u: AttemptUpload, m: LocalAttemptMedia) => void }) {
  const [activeKind, setActiveKind] = useState<AttemptKind>(allowedKinds[0] ?? 'image');
  const [file, setFile] = useState<File | null>(null);
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const startRef = useRef<number | null>(null);

  const MAX_MB = 30 * 1024 * 1024;
  const ui = view.goal.ui_view as UniversalUiView;

  // If trace is available (has line_art specialist) and no kolam ui_view, make a simple placeholder
  const kolamUi: KolamUiView = {
    canvas: { width: 400, height: 400 },
    dots: [],
    curves: [],
  };

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

  if (activeKind === 'trace' && (view.profile?.skill_model?.specialists?.['line_art'] !== undefined)) {
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
