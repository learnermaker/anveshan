/** 02 PRACTICE for a live hero case: learner capture (canvas / upload) → evaluation → results → retry. */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Eraser, FileUp, Play, RotateCcw, Send, Undo2 } from 'lucide-react';
import type { AttemptKind, AttemptResult, CaseView, KolamUiView, OrigamiUiView, TablaUiView } from '../api/types';
import { api, type AttemptUpload } from '../api/client';
import { API_BASE } from '../api/runtime';
import { KolamCanvas, buildRasterPng, buildTraceJson, type Stroke } from './kolam/KolamCanvas';
import { KolamFigure } from './kolam/KolamFigure';
import { KolamTeach } from './kolam/KolamTeach';
import { BeatTimeline } from './tabla/BeatTimeline';
import { AttemptResultView } from './results/AttemptResultView';
import type { HeroSession, LocalAttemptMedia } from './session';
import { Badge, btn, ErrorNote, KeyHint, Panel, ProgressBar, ReviewBadge, SourceLabelBadge, Spinner } from './ui';
import { TrustLine } from './TrustLine';
import { fmtTime } from './locators';
import { UniversalPracticeView } from './universal/UniversalPracticeView';
import { AttemptProgress, ReviewNote, TaskInstructions } from './Guidance';
import { DEBUG } from '../api/debug';
import { attemptLabel } from '../copy/plain';
import type { SampleAttempt } from '../api/types-product';

interface Props {
  view: CaseView;
  session: HeroSession | null;
  onSessionChange: (s: HeroSession | null) => void;
  onComplete: () => void;
  onBack: () => void;
}

export function HeroPracticeView(props: Props) {
  if (props.view.goal.modality === 'universal') return <UniversalPracticeView {...props} />;
  return <HeroPracticeViewInner {...props} />;
}

const EXPECTED: Record<string, string> = {
  trace: 'a few seconds (deterministic geometry)',
  image: '5–15 s (registration + geometry)',
  video: '1–3 min (the AI reads sampled frames)',
  audio: 'a few seconds (deterministic onsets + alignment)',
};

type Phase = { kind: 'idle' } | { kind: 'uploading'; progress: number } | { kind: 'evaluating'; since: number; attemptKind: AttemptKind };

function HeroPracticeViewInner({ view, session, onSessionChange, onComplete, onBack }: Props) {
  const [learner, setLearner] = useState('');
  const [err, setErr] = useState<unknown>(null);
  const [phase, setPhase] = useState<Phase>({ kind: 'idle' });
  const [selected, setSelected] = useState<number>(-1);
  const [showCapture, setShowCapture] = useState(true);
  const [completing, setCompleting] = useState(false);
  const captureRef = useRef<HTMLDivElement>(null);

  const attempts = session?.attempts ?? [];
  const n = attempts.length;
  const shown = attempts[selected >= 0 && selected < n ? selected : n - 1];
  const canSubmit = n < 2;

  useEffect(() => {
    setSelected(-1);
  }, [n]);

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

  const handleResult = (result: AttemptResult) => {
    if (!session) return;
    onSessionChange({ ...session, attempts: [...session.attempts, { result, media: { kind: 'image' } }] });
    setShowCapture(false);
  };

  const submit = async (upload: AttemptUpload, media: LocalAttemptMedia) => {
    if (!session) return;
    setErr(null);
    setPhase({ kind: 'uploading', progress: 0 });
    try {
      let switched = false;
      const result = await api.submitAttempt(session.sessionId, upload, (p) => {
        if (p >= 1 && !switched) {
          switched = true;
          setPhase({ kind: 'evaluating', since: Date.now(), attemptKind: upload.kind });
        } else if (!switched) setPhase({ kind: 'uploading', progress: p });
      });
      onSessionChange({ ...session, attempts: [...session.attempts, { result, media }] });
      setShowCapture(false);
    } catch (x) {
      setErr(x);
    } finally {
      setPhase({ kind: 'idle' });
    }
  };

  const submitSample = async (sampleId: string) => {
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
    setPhase({ kind: 'evaluating', since: Date.now(), attemptKind: 'image' });
    try {
      const result = await api.submitSampleAttempt(sid, sampleId);
      onSessionChange({ ...currentSession!, attempts: [...(currentSession!.attempts), { result, media: { kind: 'image' } }] });
      setShowCapture(false);
    } catch (x) {
      setErr(x);
    } finally {
      setPhase({ kind: 'idle' });
    }
  };

  const openRetry = () => {
    setShowCapture(true);
    setTimeout(() => captureRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
  };

  const complete = async () => {
    if (!session) return;
    setCompleting(true);
    setErr(null);
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

  const tryLabel = n === 0 ? attemptLabel(1) : attemptLabel(2);

  return (
    <div className="flex flex-col gap-5 w-full animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          <button onClick={onBack} className={btn.ghost}>
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Learn
          </button>
          <div className="text-xs font-mono uppercase tracking-widest text-cadmium-amber font-bold">Step 2 of 3 · Practise · {view.task.title}</div>
          <h1 className="font-serif text-2xl text-on-surface" data-plain-exempt>{view.title}</h1>
          {!DEBUG ? (
            <TrustLine view={view} />
          ) : (
            <div className="flex flex-wrap gap-1.5">
              <SourceLabelBadge label={view.runtime_label} />
              <ReviewBadge status={view.review_status} />
              {session && (
                <Badge tone="muted" title="Your name for this practice">
                  Learner: {session.learnerName}
                </Badge>
              )}
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
            <button onClick={() => onSessionChange(null)} className={btn.secondary} title="Discard these attempts and start again">
              Start over
            </button>
            {n >= 2 && (
              <button onClick={complete} disabled={completing} className={btn.primary}>
                {completing ? 'Saving the record…' : 'See what changed'} <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}
      </div>

      <ReviewNote status={view.review_status} />

      <AttemptProgress
        attempts={n}
        started={Boolean(session)}
        completing={completing}
        retryOpen={canSubmit && showCapture}
        onRetry={openRetry}
        onComplete={complete}
      />

      <ErrorNote error={err} />

      {!session ? (
        <Panel kicker="Start" title="Start practising">
          <div className="flex flex-col sm:flex-row gap-2 max-w-lg">
            <input
              value={learner}
              onChange={(e) => setLearner(e.target.value)}
              placeholder="Your name (optional, shown in the record)"
              aria-label="Your name (optional)"
              className="flex-1 bg-surface-dim border border-outline rounded-lg px-3 py-2 text-sm outline-none focus:border-caliper-cyan"
            />
            <button onClick={start} className={btn.primary}>
              <Play className="w-3.5 h-3.5" /> Start practising
            </button>
          </div>
          <div className="mt-4">
            <TaskInstructions text={view.task.instructions} claims={view.package.claims} />
          </div>
        </Panel>
      ) : (
        <>
          {canSubmit && showCapture && (
            <div ref={captureRef}>
              <Panel
                kicker={n === 0 ? 'First try' : 'Second try (the whole task again)'}
                title={view.task.title}
                right={<Badge tone="muted">{view.task.constraints.map((c) => c.description).join(' · ')}</Badge>}
              >
                <details className="mb-4" open={n === 0}>
                  <summary className="cursor-pointer text-sm font-semibold text-on-surface">Task steps</summary>
                  <div className="mt-2">
                    <TaskInstructions text={view.task.instructions} claims={view.package.claims} />
                  </div>
                </details>
                <Capture view={view} busy={phase.kind !== 'idle'} onSubmit={submit} />
                <div className="mt-4">
                  <PhaseStatus phase={phase} />
                </div>
                {/* Sample picker (WI-3.1) */}
                <SamplePicker caseId={view.case_id} tryLabel={tryLabel} noSubmitsYet={n === 0} onUseSample={submitSample} busy={phase.kind !== 'idle'} />
              </Panel>
            </div>
          )}

          {n > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {attempts.map((a, i) => (
                <button
                  key={i}
                  onClick={() => setSelected(i)}
                  className={`px-3 py-1 rounded-md border text-[11px] font-mono ${a === shown ? 'border-cadmium-amber text-cadmium-amber bg-cadmium-amber/10' : 'border-outline text-on-surface-variant'}`}
                >
                  {attemptLabel(i + 1)} · {a.result.evaluation.total_score.toFixed(1)}
                </button>
              ))}
              {canSubmit && !showCapture && (
                <button onClick={openRetry} className={btn.primary}>
                  <RotateCcw className="w-3.5 h-3.5" /> Retry the whole task
                </button>
              )}
            </div>
          )}

          {shown && <AttemptResultView view={view} result={shown.result} media={shown.media} />}

          {n > 0 && (
            <AttemptProgress attempts={n} started completing={completing} retryOpen={canSubmit && showCapture} onRetry={openRetry} onComplete={complete} />
          )}
        </>
      )}
    </div>
  );
}

/** Sample attempt picker: "No materials? Try a sample attempt" */
function SamplePicker({ caseId, tryLabel, noSubmitsYet, onUseSample, busy }: { caseId: string; tryLabel: string; noSubmitsYet: boolean; onUseSample: (sampleId: string) => void; busy: boolean }) {
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
                onClick={() => onUseSample(s.sample_id)}
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

function PhaseStatus({ phase }: { phase: Phase }) {
  const [, tick] = useState(0);
  useEffect(() => {
    if (phase.kind !== 'evaluating') return;
    const id = setInterval(() => tick((x) => x + 1), 500);
    return () => clearInterval(id);
  }, [phase.kind]);
  if (phase.kind === 'uploading') return <ProgressBar value={phase.progress} label="Uploading attempt" />;
  if (phase.kind === 'evaluating')
    return <Spinner label={`Evaluating… ${((Date.now() - phase.since) / 1000).toFixed(0)} s elapsed · expected ${EXPECTED[phase.attemptKind]}`} />;
  return null;
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

function Capture({ view, busy, onSubmit }: { view: CaseView; busy: boolean; onSubmit: (u: AttemptUpload, m: LocalAttemptMedia) => void }) {
  if (view.modality === 'kolam_image') return <KolamCapture view={view} busy={busy} onSubmit={onSubmit} />;
  // Kolam is checked by geometry alone (no AI call), so the key hint is shown only for origami and tabla.
  return (
    <div className="space-y-3">
      <KeyHint />
      {view.modality === 'origami_video' ? <OrigamiCapture view={view} busy={busy} onSubmit={onSubmit} /> : <TablaCapture view={view} busy={busy} onSubmit={onSubmit} />}
    </div>
  );
}

function KolamCapture({ view, busy, onSubmit }: { view: CaseView; busy: boolean; onSubmit: (u: AttemptUpload, m: LocalAttemptMedia) => void }) {
  const ui = view.goal.ui_view as KolamUiView;
  const [mode, setMode] = useState<'draw' | 'photo'>('draw');
  const [aside, setAside] = useState<'target' | 'teach'>('teach');
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [photo, setPhoto] = useState<File | null>(null);
  const photoUrl = useMemo(() => (photo ? URL.createObjectURL(photo) : null), [photo]);
  const startRef = useRef<number | null>(null);
  const MAX_UPLOAD_BYTES = 30 * 1024 * 1024;

  const submitTrace = async () => {
    const json = buildTraceJson(ui, view.case_id, view.goal.version, strokes, startRef.current);
    const raster = await buildRasterPng(ui, strokes);
    onSubmit({ kind: 'trace', file: new Blob([json], { type: 'application/json' }), fileName: 'trace.json', raster }, { kind: 'trace', strokes });
    setStrokes([]);
    startRef.current = null;
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {(['draw', 'photo'] as const).map((m) => (
          <button key={m} onClick={() => setMode(m)} className={`px-3 py-1 rounded-md border text-[11px] font-mono uppercase ${mode === m ? 'border-cadmium-amber text-cadmium-amber bg-cadmium-amber/10' : 'border-outline text-on-surface-variant'}`}>
            {m === 'draw' ? 'Draw on canvas' : 'Upload a photo'}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] gap-4 items-start">
        {mode === 'draw' ? (
          <div className="space-y-2">
            <KolamCanvas ui={ui} strokes={strokes} onStrokesChange={setStrokes} startRef={startRef} disabled={busy} />
            <div className="flex flex-wrap items-center gap-2">
              <button className={btn.secondary} disabled={busy || !strokes.length} onClick={() => setStrokes(strokes.slice(0, -1))}>
                <Undo2 className="w-3.5 h-3.5" /> Undo stroke
              </button>
              <button className={btn.secondary} disabled={busy || !strokes.length} onClick={() => { setStrokes([]); startRef.current = null; }}>
                <Eraser className="w-3.5 h-3.5" /> Clear
              </button>
              <span className="text-[11px] font-mono text-on-surface-variant">{strokes.length} strokes · {strokes.reduce((s, x) => s + x.length, 0)} points</span>
              <button className={`${btn.primary} ml-auto`} disabled={busy || !strokes.length} onClick={submitTrace}>
                <Send className="w-3.5 h-3.5" /> Submit drawing
              </button>
            </div>
            <p className="text-xs text-on-surface-variant">Draw the line through the dots, ideally without lifting. Undo is allowed before submitting. Timing and stroke order are recorded so the app can see how you drew it, not only the result.</p>
          </div>
        ) : (
          <div className="space-y-2">
            <FilePick accept="image/*" label="Photo of your drawn kolam, taken from above" file={photo} onFile={setPhoto} disabled={busy} />
            {photoUrl && <img src={photoUrl} alt="preview" className="max-h-72 rounded-lg border border-outline" />}
            {photo && photo.size > MAX_UPLOAD_BYTES && (
              <p className="text-[11px] font-mono text-divergence-crimson">
                File is {(photo.size / 1e6).toFixed(1)} MB — limit is 30 MB. Resize the image before uploading.
              </p>
            )}
            <button
              className={btn.primary}
              disabled={busy || !photo || photo.size > MAX_UPLOAD_BYTES}
              onClick={() => photo && onSubmit({ kind: 'image', file: photo, fileName: photo.name }, { kind: 'image', url: photoUrl ?? undefined, fileName: photo.name })}
            >
              <Send className="w-3.5 h-3.5" /> Submit photo
            </button>
            <p className="text-xs text-cadmium-amber">A photo shows only the finished drawing, so we can't tell whether the line was continuous or where it first went off track. Drawing on screen gives fuller feedback.</p>
          </div>
        )}
        <div className="space-y-1.5">
          <div className="flex gap-1" role="tablist" aria-label="Reference">
            {(
              [
                ['teach', 'Show me how'],
                ['target', 'Target image'],
              ] as const
            ).map(([k, label]) => (
              <button
                key={k}
                role="tab"
                aria-selected={aside === k}
                onClick={() => setAside(k)}
                className={`px-3 py-1 rounded-md border text-xs ${aside === k ? 'border-cadmium-amber text-cadmium-amber bg-cadmium-amber/10' : 'border-outline text-on-surface-variant'}`}
              >
                {label}
              </button>
            ))}
          </div>
          {aside === 'teach' ? (
            <KolamTeach ui={ui} />
          ) : (
            <KolamFigure ui={ui} imageUrl={api.mediaUrl(view.case_id, ui.target_source_id ?? view.goal.source_ids[0])} />
          )}
        </div>
      </div>
    </div>
  );
}

function OrigamiCapture({ view, busy, onSubmit }: { view: CaseView; busy: boolean; onSubmit: (u: AttemptUpload, m: LocalAttemptMedia) => void }) {
  const ui = view.goal.ui_view as OrigamiUiView;
  const [file, setFile] = useState<File | null>(null);
  const MAX_UPLOAD_BYTES = 30 * 1024 * 1024;
  return (
    <div className="space-y-3">
      <div className="flex gap-2 overflow-x-auto pb-1">
        {ui.states.map((s) => (
          <div key={s.index} className="shrink-0 w-20">
            {s.keyframe_asset && <img src={api.goalAssetUrl(view.case_id, s.keyframe_asset)} alt={s.name} className="w-full aspect-square object-cover rounded border border-outline bg-surface-dim" />}
            <div className="text-[11px] font-mono text-on-surface-variant mt-0.5 leading-tight">R{s.index} {s.name}</div>
          </div>
        ))}
      </div>
      <FilePick accept="video/*" label="Video of your hands folding" file={file} onFile={setFile} disabled={busy} />
      {file && file.size > MAX_UPLOAD_BYTES && (
        <p className="text-[11px] font-mono text-divergence-crimson">
          File is {(file.size / 1e6).toFixed(1)} MB — limit is 30 MB. Re-encode at a lower bitrate (e.g. ffmpeg -i input.mp4 -crf 28 out.mp4).
        </p>
      )}
      <button
        className={btn.primary}
        disabled={busy || !file || file.size > MAX_UPLOAD_BYTES}
        onClick={() => file && onSubmit({ kind: 'video', file, fileName: file.name }, { kind: 'video', url: URL.createObjectURL(file), fileName: file.name })}
      >
        <Send className="w-3.5 h-3.5" /> Submit video
      </button>
      <p className="text-xs text-on-surface-variant">Film from above with the paper and your hands in view. The app looks at about one frame per second (up to 90).</p>
    </div>
  );
}

function TablaCapture({ view, busy, onSubmit }: { view: CaseView; busy: boolean; onSubmit: (u: AttemptUpload, m: LocalAttemptMedia) => void }) {
  const ui = view.goal.ui_view as TablaUiView;
  const [audio, setAudio] = useState<File | null>(null);
  const [video, setVideo] = useState<File | null>(null);
  const MAX_UPLOAD_BYTES = 30 * 1024 * 1024;
  // Real service: cycle_length_pulses; legacy mock: cycle_length
  const cycleLen = ui.cycle_length_pulses ?? (ui as { cycle_length?: number }).cycle_length;
  return (
    <div className="space-y-3">
      <BeatTimeline ui={ui} />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <FilePick accept="audio/*,video/*" label="Recording of you playing (required)" file={audio} onFile={setAudio} disabled={busy} />
        <FilePick accept="video/*" label="Video (optional — shown, not scored)" file={video} onFile={setVideo} disabled={busy} />
      </div>
      {audio && audio.size > MAX_UPLOAD_BYTES && (
        <p className="text-[11px] font-mono text-divergence-crimson">
          File is {(audio.size / 1e6).toFixed(1)} MB — limit is 30 MB. Re-encode at a lower bitrate (e.g. ffmpeg -i input.wav -b:a 64k out.mp3).
        </p>
      )}
      <button
        className={btn.primary}
        disabled={busy || !audio || audio.size > MAX_UPLOAD_BYTES}
        onClick={() =>
          audio &&
          onSubmit(
            { kind: 'audio', file: audio, fileName: audio.name, video: video ?? undefined },
            { kind: 'audio', url: URL.createObjectURL(audio), fileName: audio.name, extraVideoUrl: video ? URL.createObjectURL(video) : undefined },
          )
        }
      >
        <Send className="w-3.5 h-3.5" /> Submit audio
      </button>
      <p className="text-xs text-on-surface-variant">
        Source: {ui.tempo_bpm ?? '?'} BPM · {cycleLen ?? '?'}-beat cycle · {fmtTime(ui.duration_sec ?? null)}. Stroke timing and bass are measured from the sound; how hard you strike is not.
      </p>
    </div>
  );
}
