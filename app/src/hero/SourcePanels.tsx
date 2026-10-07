/** Per-modality source views rendered from CaseView.goal.ui_view. */

import React, { useEffect, useRef, useState } from 'react';
import { Film, Music } from 'lucide-react';
import type { EvidenceRef } from '../types/contracts';
import type { CaseView, KolamUiView, OrigamiUiView, TablaUiView } from '../api/types';
import { api } from '../api/client';
import { KolamFigure } from './kolam/KolamFigure';
import { BeatTimeline } from './tabla/BeatTimeline';
import { Badge } from './ui';
import { fmtTime, parseLocator } from './locators';

export interface SourcePanelProps {
  view: CaseView;
  focus: EvidenceRef | null;
}

function Toggle({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      className={`px-2 py-1 rounded border text-[11px] font-mono uppercase transition-colors ${on ? 'border-caliper-cyan text-caliper-cyan bg-caliper-cyan/10' : 'border-outline text-on-surface-variant hover:text-on-surface'}`}
    >
      {children}
    </button>
  );
}

export function KolamSourcePanel({ view, focus }: SourcePanelProps) {
  const ui = view.goal.ui_view as KolamUiView;
  const [dots, setDots] = useState(true);
  const [curves, setCurves] = useState(false);
  const [sym, setSym] = useState(false);
  const [animKey, setAnimKey] = useState(0);
  const src = ui.target_source_id ?? view.goal.source_ids[0];
  const loc = focus ? parseLocator(focus.source_id) : null;
  // Real service: rotation_order at top level; legacy mock: symmetry.rotational_order
  const order = ui.rotation_order ?? ui.symmetry?.rotational_order;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Toggle on={dots} onClick={() => setDots(!dots)}>Detected dots ({ui.dots.length})</Toggle>
        <Toggle
          on={curves}
          onClick={() => {
            setCurves(!curves);
            setAnimKey((k) => k + 1);
          }}
        >
          Continuous curves ({ui.curves.length})
        </Toggle>
        <Toggle on={sym} onClick={() => setSym(!sym)}>Symmetry{order ? ` (${order}-fold)` : ''}</Toggle>
      </div>
      <div className="relative max-w-[560px] mx-auto">
        <KolamFigure
          key={animKey}
          ui={ui}
          imageUrl={src ? api.mediaUrl(view.case_id, src) : undefined}
          showDots={dots}
          showCurves={curves}
          animateCurves={curves}
          showSymmetry={sym}
          region={loc?.region ?? null}
        />
        {curves && (
          <div className="absolute top-2 left-2 flex gap-1">
            <Badge tone="amber">One suggested way — INFERRED</Badge>
          </div>
        )}
      </div>
      <div className="flex flex-wrap gap-3 text-[11px] font-mono text-on-surface-variant justify-center">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cadmium-amber" /> dot on the line</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-caliper-cyan" /> dot enclosed</span>
        <span>τ = {ui.tau ?? '?'} px · canvas {ui.canvas.width}×{ui.canvas.height}</span>
        <span>direction and start point of curves are arbitrary</span>
      </div>
    </div>
  );
}

function useSeek(ref: React.RefObject<HTMLMediaElement>, focus: EvidenceRef | null) {
  useEffect(() => {
    const el = ref.current;
    if (!el || !focus) return;
    const t = typeof focus.start_sec === 'number' ? focus.start_sec : parseLocator(focus.source_id).time;
    if (t == null) return;
    try {
      el.currentTime = t;
      void el.play().catch(() => undefined);
    } catch {
      /* media not ready */
    }
  }, [ref, focus]);
}

export function OrigamiSourcePanel({ view, focus }: SourcePanelProps) {
  const ui = view.goal.ui_view as OrigamiUiView;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [now, setNow] = useState(0);
  const src = ui.source_id ?? view.goal.source_ids[0];
  const url = src ? api.mediaUrl(view.case_id, src) : '';
  useSeek(videoRef, focus);
  const loc = focus ? parseLocator(focus.source_id) : null;
  const focusStep = loc?.key === 'step' ? loc.range?.[0] : null;
  const active = ui.states.findIndex((s) => now >= s.start_sec && now < s.end_sec);

  const seek = (t: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = t;
      setNow(t);
    }
  };

  return (
    <div className="space-y-3">
      <div className="relative rounded-lg overflow-hidden border border-outline bg-black aspect-video">
        {url ? (
          <video ref={videoRef} src={url} controls className="w-full h-full" onTimeUpdate={(e) => setNow(e.currentTarget.currentTime)} preload="metadata" />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center p-4">
            <img src="/assets/origami-tavin-poster.jpg" alt="" className="absolute inset-0 w-full h-full object-cover opacity-30" />
            <Film className="w-6 h-6 text-on-surface-variant relative" />
            <div className="relative text-[11px] font-mono text-on-surface-variant">Expert video is not bundled in MOCK mode. Run the service to stream it.</div>
          </div>
        )}
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {ui.states.map((s) => {
          const isFocus = focusStep === s.index;
          const isActive = active === s.index;
          return (
            <button
              key={s.index}
              type="button"
              onClick={() => seek(s.keyframe_sec ?? s.start_sec)}
              className={`shrink-0 w-28 rounded-lg border text-left overflow-hidden transition-colors ${isFocus ? 'border-cadmium-amber ring-1 ring-cadmium-amber' : isActive ? 'border-caliper-cyan' : 'border-outline hover:border-on-surface-variant'}`}
            >
              {s.keyframe_asset ? (
                <img src={api.goalAssetUrl(view.case_id, s.keyframe_asset)} alt={s.name} className="w-full aspect-square object-cover bg-surface-dim" />
              ) : (
                <div className="w-full aspect-square bg-surface-dim" />
              )}
              <div className="p-1.5 space-y-0.5">
                <div className="text-[11px] font-mono text-cadmium-amber">R{s.index} · {fmtTime(s.start_sec)}–{fmtTime(s.end_sec)}</div>
                <div className="text-[11px] text-on-surface leading-tight line-clamp-2">{s.name}</div>
              </div>
            </button>
          );
        })}
      </div>
      <div className="text-[11px] font-mono text-on-surface-variant">
        Goal states R0–R{ui.states.length - 1}; order is source-established (the expert performed it). Click a state to seek.
      </div>
    </div>
  );
}

export function TablaSourcePanel({ view, focus }: SourcePanelProps) {
  const ui = view.goal.ui_view as TablaUiView;
  const audioRef = useRef<HTMLAudioElement>(null);
  const [now, setNow] = useState<number | null>(null);
  // Real service: no source_id in ui_view; fall back to goal.source_ids[0]
  const src = (ui as { source_id?: string }).source_id ?? view.goal.source_ids[0];
  const url = src ? api.mediaUrl(view.case_id, src) : '';
  useSeek(audioRef, focus);
  const loc = focus ? parseLocator(focus.source_id) : null;
  const highlight: [number, number] | null =
    focus && typeof focus.start_sec === 'number' ? [focus.start_sec, focus.end_sec ?? focus.start_sec + 0.3] : null;
  // Real service: stroke_pulse_sec; legacy mock: period_sec
  const pulseSec = ui.stroke_pulse_sec ?? (ui as { period_sec?: number }).period_sec;
  // Real service: cycle_length_pulses; legacy mock: cycle_length
  const cycleLen = ui.cycle_length_pulses ?? (ui as { cycle_length?: number }).cycle_length;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono">
        <Music className="w-4 h-4 text-cadmium-amber" />
        {ui.tempo_bpm && <span>tempo <b className="text-on-surface">{ui.tempo_bpm} BPM</b></span>}
        {pulseSec && <span>stroke pulse <b className="text-on-surface">{Math.round(pulseSec * 1000)} ms</b></span>}
        {cycleLen && <span>cycle <b className="text-on-surface">{cycleLen} pulses</b></span>}
        <span>{ui.beats.length} beats · {ui.beats.filter((b) => b.bass).length} with bass</span>
      </div>
      {url ? (
        <audio ref={audioRef} src={url} controls className="w-full" onTimeUpdate={(e) => setNow(e.currentTarget.currentTime)} />
      ) : (
        <div className="text-[11px] font-mono text-on-surface-variant">Source audio unavailable.</div>
      )}
      <BeatTimeline
        ui={ui}
        playhead={now}
        highlight={highlight}
        focusBeat={loc?.key === 'onset' ? loc.range?.[0] ?? null : null}
        onSeek={(t) => {
          if (audioRef.current) audioRef.current.currentTime = t;
          setNow(t);
        }}
      />
    </div>
  );
}

export function SourcePanel(props: SourcePanelProps) {
  switch (props.view.modality) {
    case 'kolam_image':
      return <KolamSourcePanel {...props} />;
    case 'origami_video':
      return <OrigamiSourcePanel {...props} />;
    case 'tabla_audio':
      return <TablaSourcePanel {...props} />;
    default:
      return <div className="text-xs font-mono text-on-surface-variant">Unsupported modality {String(props.view.modality)}</div>;
  }
}
