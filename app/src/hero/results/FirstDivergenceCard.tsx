/** First-divergence card: learner evidence vs expert evidence, side by side, grounded in claims. */

import React, { useEffect, useRef } from 'react';
import { Crosshair } from 'lucide-react';
import type { EvidenceRef } from '../../types/contracts';
import type { AttemptResult, CaseView, KolamUiView, OrigamiUiView, TablaUiView } from '../../api/types';
import { api } from '../../api/client';
import type { LocalAttemptMedia } from '../session';
import { KolamFigure } from '../kolam/KolamFigure';
import { BeatTimeline } from '../tabla/BeatTimeline';
import { evidenceTime, fmtPosition, fmtTime, parseLocator } from '../locators';
import { Badge, Panel, StatusBadge } from '../ui';
import { DEBUG } from '../../api/debug';
import { WhyThisFeedback } from '../WhyThisFeedback';
import { plainRefs } from '../Guidance';

interface Props {
  view: CaseView;
  result: AttemptResult;
  media: LocalAttemptMedia;
}

function Side({ label, tone, children, caption }: { label: string; tone: 'crimson' | 'emerald'; children: React.ReactNode; caption?: React.ReactNode }) {
  return (
    <div className="space-y-1.5 min-w-0">
      <div className="flex items-center gap-2">
        <Badge tone={tone}>{label}</Badge>
      </div>
      {children}
      {caption && <div className="text-[11px] text-on-surface-variant">{caption}</div>}
    </div>
  );
}

function SeekVideo({ url, time, className = '' }: { url?: string; time: number | null; className?: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || time == null) return;
    const go = () => {
      try {
        el.currentTime = time;
      } catch {
        /* ignore */
      }
    };
    if (el.readyState >= 1) go();
    else el.addEventListener('loadedmetadata', go, { once: true });
  }, [url, time]);
  if (!url) return <div className={`aspect-video rounded-lg border border-outline bg-surface-dim flex items-center justify-center text-[11px] font-mono text-on-surface-variant ${className}`}>media not available</div>;
  return <video ref={ref} src={url} controls muted className={`w-full rounded-lg border border-outline bg-black ${className}`} preload="metadata" />;
}

function regionOf(ev: EvidenceRef | null | undefined) {
  return ev ? parseLocator(ev.source_id).region ?? null : null;
}

export function FirstDivergenceCard({ view, result, media }: Props) {
  const fd = result.first_divergence;
  if (!fd) {
    return (
      <Panel kicker="Where you first went off track" title="No clear point off track">
        <p className="text-xs text-on-surface-variant">
          {result.evaluation.criterion_results.some((r) => r.status === 'uncertain')
            ? "No clear point where you went off track, but some checks couldn't be judged — the evidence was unclear."
            : "You stayed on track for every scored check."}
        </p>
      </Panel>
    );
  }

  let comparison: React.ReactNode = null;
  if (view.modality === 'kolam_image') {
    const ui = view.goal.ui_view as KolamUiView;
    const lloc = fd.learner_evidence ? parseLocator(fd.learner_evidence.source_id) : null;
    const hl = lloc?.key === 'stroke' && lloc.range ? Array.from({ length: lloc.range[1] - lloc.range[0] + 1 }, (_, i) => lloc.range![0] + i) : [];
    comparison = (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Side label="Learner" tone="crimson" caption={hl.length ? `stroke ${hl.map((s) => s + 1).join(', ')} highlighted` : media.kind === 'image' ? 'uploaded photo' : undefined}>
          {media.kind === 'trace' && media.strokes ? (
            <KolamFigure ui={ui} showImage={false} showDots strokes={media.strokes.map((s) => s.map((p) => [p[0], p[1]]))} highlightStrokes={hl} region={regionOf(fd.expert_evidence)} regionTone="cyan" />
          ) : media.url ? (
            <div className="relative">
              <img src={media.url} alt="Learner attempt" className="w-full rounded-lg border border-outline" />
              {regionOf(fd.learner_evidence) && (
                <div
                  className="absolute border-2 border-dashed border-divergence-crimson bg-divergence-crimson/10"
                  style={{ left: `${regionOf(fd.learner_evidence)!.x}%`, top: `${regionOf(fd.learner_evidence)!.y}%`, width: `${regionOf(fd.learner_evidence)!.w}%`, height: `${regionOf(fd.learner_evidence)!.h}%` }}
                />
              )}
            </div>
          ) : (
            <div className="text-[11px] font-mono text-on-surface-variant">learner media not kept locally</div>
          )}
        </Side>
        <Side label="Target (goal)" tone="emerald" caption={fd.expert_evidence?.cue_excerpt}>
          <KolamFigure ui={ui} imageUrl={api.mediaUrl(view.case_id, ui.target_source_id ?? view.goal.source_ids[0])} region={regionOf(fd.expert_evidence)} />
        </Side>
      </div>
    );
  } else if (view.modality === 'origami_video') {
    const ui = view.goal.ui_view as OrigamiUiView;
    const t = fd.position ?? evidenceTime(fd.learner_evidence);
    const eloc = fd.expert_evidence ? parseLocator(fd.expert_evidence.source_id) : null;
    const step = eloc?.key === 'step' ? eloc.range?.[0] : undefined;
    const state = step != null ? ui.states.find((s) => s.index === step) : undefined;
    comparison = (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Side label="Learner" tone="crimson" caption={`learner video at ${fmtTime(t)}`}>
          <SeekVideo url={media.url} time={t} />
        </Side>
        <Side label="Expert keyframe" tone="emerald" caption={state ? `R${state.index} "${state.name}" · source ${fmtTime(state.start_sec)}–${fmtTime(state.end_sec)}` : fd.expert_evidence?.cue_excerpt}>
          {state?.keyframe_asset ? (
            <img src={api.goalAssetUrl(view.case_id, state.keyframe_asset)} alt={state.name} className="w-full max-h-64 object-contain rounded-lg border border-outline bg-surface-dim" />
          ) : (
            <div className="aspect-video rounded-lg border border-outline bg-surface-dim" />
          )}
          {state?.properties && (
            <ul className="text-xs text-on-surface-variant list-disc pl-4">
              {state.properties.map((p) => <li key={p}>{p}</li>)}
            </ul>
          )}
        </Side>
      </div>
    );
  } else if (view.modality === 'tabla_audio') {
    const ui = view.goal.ui_view as TablaUiView;
    const beat = fd.position_kind === 'beat' && fd.position != null ? fd.position - 1 : null;
    comparison = (
      <div className="space-y-3">
        <BeatTimeline ui={ui} alignment={result.trajectory.artifacts.alignment} focusBeat={beat} highlight={fd.expert_evidence && typeof fd.expert_evidence.start_sec === 'number' ? [fd.expert_evidence.start_sec, fd.expert_evidence.end_sec ?? fd.expert_evidence.start_sec + 0.3] : null} />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Side label="Learner audio" tone="crimson" caption={`stroke at ${fmtTime(evidenceTime(fd.learner_evidence))}`}>
            {media.url ? <audio src={media.url} controls className="w-full" /> : <div className="text-[11px] font-mono text-on-surface-variant">not kept locally</div>}
          </Side>
          <Side label="Source audio" tone="emerald" caption={fd.expert_evidence?.cue_excerpt}>
            <audio src={api.mediaUrl(view.case_id, (view.goal.ui_view as TablaUiView).source_id ?? view.goal.source_ids[0])} controls className="w-full" />
          </Side>
        </div>
        {media.extraVideoUrl && (
          <Side label="Optional video — shown, not scored" tone="emerald">
            <video src={media.extraVideoUrl} controls className="w-full max-h-56 rounded-lg border border-outline bg-black" />
          </Side>
        )}
      </div>
    );
  }

  return (
    <Panel
      kicker="Where you first went off track"
      title={<span className="flex items-center gap-2"><Crosshair className="w-4 h-4 text-divergence-crimson" />{fd.criterion_name}</span>}
      right={
        <>
          {DEBUG && <code className="text-[11px] font-mono text-caliper-cyan">{fd.criterion_id}</code>}
          <StatusBadge status={fd.status} />
          <Badge tone="crimson">{fmtPosition(fd.position, fd.position_kind)}</Badge>
        </>
      }
      className="border-divergence-crimson/40"
    >
      <div className="space-y-4">
        {comparison}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="p-3 rounded-lg bg-surface-dim border border-outline/60">
            <div className="text-[11px] font-mono uppercase text-divergence-crimson font-bold mb-1">What we saw</div>
            <p className="text-on-surface leading-relaxed" data-plain-exempt>{fd.observed_finding}</p>
          </div>
          <div className="p-3 rounded-lg bg-surface-dim border border-outline/60">
            <div className="text-[11px] font-mono uppercase text-transmission-emerald font-bold mb-1">Why it matters</div>
            <p className="text-on-surface leading-relaxed">{plainRefs(fd.why_it_matters) || '—'}</p>
            {DEBUG && fd.source_claim_ids.length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-1">
                {fd.source_claim_ids.map((id) => {
                  const c = view.package.claims.find((x) => x.claim_id === id);
                  return (
                    <span key={id} title={c?.statement} className="text-[11px] font-mono text-caliper-cyan">
                      {id}
                    </span>
                  );
                })}
              </div>
            )}
          </div>
        </div>
        <WhyThisFeedback view={view} claimIds={fd.source_claim_ids} measured={fd.observed_finding} />
      </div>
    </Panel>
  );
}
