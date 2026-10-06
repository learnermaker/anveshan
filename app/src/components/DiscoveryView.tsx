import React, { useState } from 'react';
import { Activity, ChevronRight, Compass, FileUp, Layers, Music, RefreshCw, Scissors, Shield, Wrench } from 'lucide-react';
import { CAPABILITY_CASES, SHOWCASE_CASE_IDS } from '../data/cases/registry';
import type { CaseSummary } from '../api/types';
import { api } from '../api/client';
import { IS_MOCK, API_BASE } from '../api/runtime';
import { Badge, ErrorNote, MockBadge, ProgressBar, ReviewBadge, SourceLabelBadge, Spinner } from '../hero/ui';

export type CaseKey = { kind: 'hero'; id: string } | { kind: 'showcase'; id: string };

interface DiscoveryViewProps {
  heroCases: CaseSummary[] | null;
  heroError: unknown;
  heroLoading: boolean;
  onRefreshHero: () => void;
  onSelect: (key: CaseKey) => void;
  selected: CaseKey;
}

const MODALITY_META: Record<string, { icon: React.ReactNode; accept: string; uploadLabel: string; input: string }> = {
  kolam_image: { icon: <Compass className="w-5 h-5 text-transmission-emerald" />, accept: 'image/*', uploadLabel: 'Upload your own finished kolam image', input: 'Draw on canvas or upload a photo' },
  origami_video: { icon: <Scissors className="w-5 h-5 text-cadmium-amber" />, accept: 'video/*', uploadLabel: 'Upload your own demonstration video', input: 'Upload a video of your attempt' },
  tabla_audio: { icon: <Music className="w-5 h-5 text-caliper-cyan" />, accept: 'audio/*,video/*', uploadLabel: 'Upload your own tabla recording', input: 'Upload audio (video optional, not scored)' },
};

const SHOWCASE_ICON: Record<string, React.ReactNode> = {
  micrometer: <Activity className="w-5 h-5 text-caliper-cyan" />,
  bicycle_repair: <Wrench className="w-5 h-5 text-cadmium-amber" />,
  weaving: <Layers className="w-5 h-5 text-caliper-cyan" />,
  square_knot: <Shield className="w-5 h-5 text-divergence-crimson" />,
};

export function DiscoveryView({ heroCases, heroError, heroLoading, onRefreshHero, onSelect, selected }: DiscoveryViewProps) {
  const heroes = (heroCases ?? []).filter((c) => c.hero);
  const derived = (heroCases ?? []).filter((c) => !c.hero && c.derived_from);

  return (
    <div className="flex flex-col gap-10 max-w-6xl w-full mx-auto p-2 lg:p-6 animate-fade-in text-on-surface">
      <section className="text-center max-w-3xl mx-auto space-y-4 pt-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cadmium-amber/10 border border-cadmium-amber/30 text-cadmium-amber font-mono text-[10px] font-semibold uppercase tracking-widest">
          Google Cloud AI Builder Cup 2026 // Prototype
        </div>
        <h1 className="font-serif text-4xl sm:text-5xl font-normal tracking-tight leading-[1.15]">Transmit what matters.</h1>
        <p className="text-sm sm:text-base text-on-surface-variant max-w-2xl mx-auto leading-relaxed">
          A source defines the goal. The learner’s attempt is checked against it step by step: where progress stalled, where it first left the path, and whether that changed after one targeted retry.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-1 sm:gap-2 text-[11px] font-mono text-on-surface-variant">
          {['SOURCE', 'GOAL MODEL', 'PRACTICE', 'FIRST DIVERGENCE', 'RETRY', 'TRANSMISSION'].map((s, i, a) => (
            <React.Fragment key={s}>
              <span className={i === a.length - 1 ? 'text-transmission-emerald font-bold' : 'text-on-surface font-semibold'}>{s}</span>
              {i < a.length - 1 && <ChevronRight className="w-3.5 h-3.5 text-outline" />}
            </React.Fragment>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-outline pb-3">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-widest text-cadmium-amber font-bold flex items-center gap-2">
              Live hero cases <MockBadge />
            </div>
            <h2 className="text-xl font-semibold font-serif">Practise against a real source</h2>
          </div>
          <button onClick={onRefreshHero} className="text-[11px] font-mono text-on-surface-variant hover:text-on-surface flex items-center gap-1">
            <RefreshCw className="w-3 h-3" /> refresh
          </button>
        </div>
        {heroLoading && <Spinner label="Loading cases from the service…" />}
        {Boolean(heroError) && (
          <div className="space-y-2">
            <ErrorNote error={heroError} />
            <p className="text-[11px] font-mono text-on-surface-variant">
              Service: {IS_MOCK ? 'mock' : API_BASE || 'same origin'}. Start it (see app/README.md) or run the app with VITE_API_BASE=mock for canned SYNTHETIC data.
            </p>
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {heroes.map((c) => (
            <HeroCard key={c.case_id} c={c} active={selected.kind === 'hero' && selected.id === c.case_id} onOpen={(id) => onSelect({ kind: 'hero', id })} />
          ))}
        </div>
        {derived.length > 0 && (
          <div className="space-y-2">
            <div className="text-[10px] font-mono uppercase text-on-surface-variant">Your uploaded sources</div>
            <div className="flex flex-wrap gap-2">
              {derived.map((c) => (
                <button key={c.case_id} onClick={() => onSelect({ kind: 'hero', id: c.case_id })} className="flex items-center gap-2 px-3 py-2 rounded-lg border border-outline bg-surface-container-low hover:border-cadmium-amber text-left">
                  <span className="text-xs">{c.title}</span>
                  <SourceLabelBadge label={c.runtime_label} />
                  <ReviewBadge status={c.review_status} />
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-outline pb-3">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant font-bold">Showcase</div>
            <h2 className="text-xl font-semibold font-serif">Other archetypes (synthetic replay)</h2>
          </div>
          <p className="text-[11px] font-mono text-on-surface-variant max-w-md sm:text-right">Fixed SYNTHETIC fixtures that show how the workspace adapts. No learner input; nothing is evaluated live.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {SHOWCASE_CASE_IDS.map((id) => {
            const c = CAPABILITY_CASES[id];
            if (!c) return null;
            const active = selected.kind === 'showcase' && selected.id === id;
            return (
              <button
                key={id}
                onClick={() => onSelect({ kind: 'showcase', id })}
                className={`p-4 rounded-xl border text-left transition-colors flex flex-col gap-2 ${active ? 'border-cadmium-amber bg-surface-container' : 'border-outline bg-surface-container-low hover:border-on-surface-variant'}`}
              >
                <div className="flex items-center justify-between">
                  <div className="w-9 h-9 rounded-lg bg-surface-dim border border-outline flex items-center justify-center">{SHOWCASE_ICON[id]}</div>
                  <Badge tone="crimson">SYNTHETIC REPLAY</Badge>
                </div>
                <div className="font-semibold text-sm">{c.title}</div>
                <div className="text-[10px] font-mono text-on-surface-variant">{c.archetype}</div>
                <p className="text-[11px] text-on-surface-variant line-clamp-2">{c.shortDescription}</p>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function HeroCard({ c, active, onOpen }: { c: CaseSummary; active: boolean; onOpen: (id: string) => void }) {
  const meta = MODALITY_META[c.modality] ?? { icon: <Compass className="w-5 h-5" />, accept: '*/*', uploadLabel: 'Upload your own source', input: '' };
  const [stage, setStage] = useState<'idle' | 'uploading' | 'building'>('idle');
  const [progress, setProgress] = useState(0);
  const [err, setErr] = useState<unknown>(null);

  const upload = async (file: File) => {
    setErr(null);
    setStage('uploading');
    setProgress(0);
    try {
      const { case_id } = await api.uploadSource(c.case_id, file, setProgress);
      setStage('building');
      await api.buildCase(case_id);
      onOpen(case_id);
    } catch (e) {
      setErr(e);
    } finally {
      setStage('idle');
    }
  };

  return (
    <div className={`p-5 rounded-xl border flex flex-col gap-3 transition-colors ${active ? 'border-cadmium-amber bg-surface-container shadow-lg shadow-cadmium-amber/10' : 'border-outline bg-surface-container-low'}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="w-10 h-10 rounded-lg bg-surface-dim border border-outline flex items-center justify-center">{meta.icon}</div>
        <div className="flex flex-wrap gap-1 justify-end">
          <SourceLabelBadge label={c.runtime_label} />
          <ReviewBadge status={c.review_status} />
        </div>
      </div>
      <div>
        <h3 className="font-semibold text-base">{c.title}</h3>
        <div className="text-[10px] font-mono text-on-surface-variant mt-0.5">{c.modality} · {meta.input}</div>
      </div>
      <button onClick={() => onOpen(c.case_id)} className="mt-auto inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-mono font-bold text-[11px] uppercase tracking-wider">
        Open case →
      </button>
      <label className={`flex items-center gap-2 text-[11px] font-mono text-on-surface-variant ${stage === 'idle' ? 'hover:text-on-surface cursor-pointer' : 'opacity-60'}`}>
        <FileUp className="w-3.5 h-3.5" /> {meta.uploadLabel}
        <input
          type="file"
          accept={meta.accept}
          className="hidden"
          disabled={stage !== 'idle'}
          onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = '';
            if (f) void upload(f);
          }}
        />
      </label>
      {stage === 'uploading' && <ProgressBar value={progress} label="Uploading source" />}
      {stage === 'building' && <Spinner label="Building goal model from your source…" />}
      <ErrorNote error={err} />
    </div>
  );
}
