import React, { useState } from 'react';
import { Activity, ArrowRight, Compass, FileUp, HelpCircle, Layers, Music, PlusCircle, RefreshCw, Scissors, Shield, Sparkles, Wrench } from 'lucide-react';
import { CAPABILITY_CASES, SHOWCASE_CASE_IDS } from '../data/cases/registry';
import type { CaseSummary } from '../api/types';
import { api } from '../api/client';
import { IS_MOCK, API_BASE } from '../api/runtime';
import { Badge, ErrorNote, MockBadge, ProgressBar, ReviewBadge, SourceLabelBadge, Spinner } from '../hero/ui';
import { AiRoleNote, HowItWorksSteps } from './HowItWorks';

export type CaseKey = { kind: 'hero'; id: string } | { kind: 'showcase'; id: string } | { kind: 'composer' };

interface DiscoveryViewProps {
  heroCases: CaseSummary[] | null;
  heroError: unknown;
  heroLoading: boolean;
  onRefreshHero: () => void;
  onSelect: (key: CaseKey) => void;
  selected: CaseKey;
  onOpenGuide?: () => void;
  /** K9: open My skills (App.tsx, P3) */
  onOpenMine?: () => void;
}

interface ModalityMeta {
  icon: React.ReactNode;
  accept: string;
  /** label of the "build from your own source" action ('' = not offered) */
  uploadLabel: string;
  /** what the learner does, in plain words */
  doText: string;
  /** what the learner needs */
  need: string;
}

const MODALITY_META: Record<string, ModalityMeta> = {
  kolam_image: {
    icon: <Compass className="w-5 h-5 text-transmission-emerald" />,
    accept: 'image/*',
    uploadLabel: 'Use your own kolam photo as the source',
    doText:
      'Redraw a traditional South Indian line drawing on its dot grid. Checks that every line is drawn, nothing strays, each dot keeps its place and the line stays continuous.',
    need: 'Nothing: draw with a mouse, finger or stylus',
  },
  origami_video: {
    icon: <Scissors className="w-5 h-5 text-cadmium-amber" />,
    accept: 'video/*',
    uploadLabel: 'Use your own folding video as the source',
    doText: 'Fold paper through the states shown in a real demonstration video. Checks that each paper state is reached, in order.',
    need: 'A short video of your folding, or a sample attempt',
  },
  tabla_audio: {
    icon: <Music className="w-5 h-5 text-caliper-cyan" />,
    accept: 'audio/*,video/*',
    uploadLabel: 'Use your own tabla recording as the source',
    doText: 'Play the Dha stroke pattern from a real tabla recording. Checks tempo, timing against the beat and the bass stroke.',
    need: 'A short audio recording, or a sample attempt',
  },
  universal: {
    icon: <Sparkles className="w-5 h-5 text-caliper-cyan" />,
    accept: '*/*',
    uploadLabel: '',
    doText: 'A skill built from a real source video by the universal pipeline. Checks each step, the order and the final result.',
    need: 'A video of your attempt, or a sample attempt',
  },
};

const SHOWCASE_ICON: Record<string, React.ReactNode> = {
  micrometer: <Activity className="w-5 h-5 text-caliper-cyan" />,
  bicycle_repair: <Wrench className="w-5 h-5 text-cadmium-amber" />,
  weaving: <Layers className="w-5 h-5 text-caliper-cyan" />,
  square_knot: <Shield className="w-5 h-5 text-divergence-crimson" />,
};

export function DiscoveryView({ heroCases, heroError, heroLoading, onRefreshHero, onSelect, selected, onOpenGuide }: DiscoveryViewProps) {
  const heroes = (heroCases ?? []).filter((c) => c.hero);
  const derived = (heroCases ?? []).filter((c) => !c.hero && c.derived_from && !c.composed);
  const composed = (heroCases ?? []).filter((c) => c.composed === true);

  return (
    <div className="flex flex-col gap-10 max-w-6xl w-full mx-auto p-2 lg:p-6 animate-fade-in text-on-surface">
      <section className="text-center max-w-3xl mx-auto space-y-4 pt-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cadmium-amber/10 border border-cadmium-amber/30 text-cadmium-amber font-mono text-[11px] font-semibold uppercase tracking-widest">
          Google Cloud AI Builder Cup 2026 · Prototype
        </div>
        <h1 className="font-serif text-4xl sm:text-5xl font-normal tracking-tight leading-[1.15]">Learn a hands-on skill from a real source, and see whether it transferred.</h1>
        <p className="text-base text-on-surface-variant max-w-2xl mx-auto leading-relaxed">
          Anveshan turns a demonstration (a photo, a video or a recording) into steps and checks you can trust, because each one points back to the source. You try the
          skill, it shows exactly where you first went off track, you retry once, and it records what changed.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3 pt-1">
          <button
            onClick={() => onSelect({ kind: 'hero', id: 'kolam' })}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-semibold text-sm"
          >
            New here? Start with the Kolam drawing <ArrowRight className="w-4 h-4" aria-hidden="true" />
          </button>
          {onOpenGuide && (
            <button onClick={onOpenGuide} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-outline hover:border-cadmium-amber text-sm text-on-surface">
              <HelpCircle className="w-4 h-4 text-cadmium-amber" aria-hidden="true" /> What the labels mean
            </button>
          )}
        </div>
        <p className="text-sm text-on-surface-variant">No sign-in. The Kolam drawing needs no files: you draw in the browser. About 3 minutes.</p>
      </section>

      <section aria-labelledby="how-title" className="space-y-3">
        <h2 id="how-title" className="text-xs font-mono uppercase tracking-widest text-on-surface-variant font-bold">
          How it works
        </h2>
        <HowItWorksSteps compact />
        <AiRoleNote />
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-outline pb-3">
          <div>
            <div className="text-xs font-mono uppercase tracking-widest text-cadmium-amber font-bold flex items-center gap-2">
              Ready-made skills <MockBadge />
            </div>
            <h2 className="text-xl font-semibold font-serif">Practise a skill built from a real source</h2>
          </div>
          <button onClick={onRefreshHero} className="text-xs font-mono text-on-surface-variant hover:text-on-surface flex items-center gap-1">
            <RefreshCw className="w-3 h-3" aria-hidden="true" /> refresh
          </button>
        </div>
        {heroLoading && <Spinner label="Loading skills…" />}
        {Boolean(heroError) && (
          <div className="space-y-2">
            <ErrorNote error={heroError} />
            <p className="text-xs font-mono text-on-surface-variant">
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
            <div className="text-xs font-mono uppercase text-on-surface-variant">Your uploaded sources (only you can see these)</div>
            <div className="flex flex-wrap gap-2">
              {derived.map((c) => (
                <button
                  key={c.case_id}
                  onClick={() => onSelect({ kind: 'hero', id: c.case_id })}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg border border-outline bg-surface-container-low hover:border-cadmium-amber text-left"
                >
                  <span className="text-sm">{c.title}</span>
                  <SourceLabelBadge label={c.runtime_label} />
                  <ReviewBadge status={c.review_status} />
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="space-y-4">
        <div className="border-b border-outline pb-3">
          <div className="text-xs font-mono uppercase tracking-widest text-caliper-cyan font-bold flex items-center gap-2">
            Your own skill <MockBadge />
          </div>
          <h2 className="text-xl font-semibold font-serif">Create a new skill from any demonstration</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <button
            onClick={() => onSelect({ kind: 'composer' })}
            className={`p-5 rounded-xl border flex flex-col gap-3 text-left transition-colors ${
              selected.kind === 'composer' ? 'border-caliper-cyan bg-surface-container shadow-lg shadow-caliper-cyan/10' : 'border-outline bg-surface-container-low hover:border-caliper-cyan'
            }`}
            aria-label="Open the skill composer"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="w-10 h-10 rounded-lg bg-surface-dim border border-outline flex items-center justify-center">
                <PlusCircle className="w-5 h-5 text-caliper-cyan" aria-hidden="true" />
              </div>
              <Badge tone="cyan">IMAGE · VIDEO · AUDIO</Badge>
            </div>
            <div>
              <h3 className="font-semibold text-base">Upload a demonstration, get a practice task</h3>
            </div>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Upload something you have the right to use: a photo of a finished piece, a short video of a process, or an audio recording. The AI proposes the steps and
              checks, and you review them before the skill is created. Anything the AI read rather than measured is labelled INFERRED. There is a sample video if you have
              nothing to hand.
            </p>
            <div className="mt-auto inline-flex items-center gap-1.5 text-sm font-semibold text-caliper-cyan">
              <Sparkles className="w-4 h-4" aria-hidden="true" /> Open the composer
            </div>
          </button>

          {composed.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-mono uppercase text-on-surface-variant">Your skills (only you can see these)</div>
              <div className="flex flex-col gap-2">
                {composed.map((c) => (
                  <button
                    key={c.case_id}
                    onClick={() => onSelect({ kind: 'hero', id: c.case_id })}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg border border-outline bg-surface-container-low hover:border-caliper-cyan text-left"
                  >
                    <Badge tone="cyan">UPLOAD</Badge>
                    {(c.structures ?? []).map((s) => (
                      <Badge key={s} tone="muted">
                        {s}
                      </Badge>
                    ))}
                    <span className="text-sm flex-1 truncate">{c.title}</span>
                    <ReviewBadge status={c.review_status} />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      <details className="group space-y-4 border-t border-outline pt-4">
        <summary className="cursor-pointer list-none flex flex-wrap items-center justify-between gap-3">
          <span>
            <span className="block text-xs font-mono uppercase tracking-widest text-on-surface-variant font-bold">Design archetypes · synthetic, not evaluated</span>
            <span className="block text-base font-semibold font-serif text-on-surface">
              How the workspace could adapt to other kinds of skill <span className="text-sm font-sans text-caliper-cyan group-open:hidden">(show)</span>
            </span>
          </span>
          <span className="text-sm text-on-surface-variant max-w-md sm:text-right">Fixed made-up examples. There is no learner input and nothing is scored.</span>
        </summary>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {SHOWCASE_CASE_IDS.map((id) => {
            const c = CAPABILITY_CASES[id];
            if (!c) return null;
            const active = selected.kind === 'showcase' && selected.id === id;
            return (
              <button
                key={id}
                onClick={() => onSelect({ kind: 'showcase', id })}
                className={`p-4 rounded-xl border text-left transition-colors flex flex-col gap-2 ${
                  active ? 'border-cadmium-amber bg-surface-container' : 'border-outline bg-surface-container-low hover:border-on-surface-variant'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="w-9 h-9 rounded-lg bg-surface-dim border border-outline flex items-center justify-center">{SHOWCASE_ICON[id]}</div>
                  <Badge tone="crimson">SYNTHETIC</Badge>
                </div>
                <div className="font-semibold text-sm">{c.title}</div>
                <div className="text-xs font-mono text-on-surface-variant">{c.archetype}</div>
              </button>
            );
          })}
        </div>
      </details>
    </div>
  );
}

function HeroCard({ c, active, onOpen }: { c: CaseSummary; active: boolean; onOpen: (id: string) => void }) {
  const meta: ModalityMeta = MODALITY_META[c.modality] ?? MODALITY_META.universal;
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
        <p className="text-sm text-on-surface-variant mt-1 leading-relaxed">{meta.doText}</p>
        <p className="text-sm text-on-surface mt-2">
          <span className="text-on-surface-variant">You need: </span>
          {meta.need}
        </p>
      </div>
      <button
        onClick={() => onOpen(c.case_id)}
        className="mt-auto inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-semibold text-sm"
      >
        Open this skill <ArrowRight className="w-4 h-4" aria-hidden="true" />
      </button>
      {meta.uploadLabel && (
        <label
          className={`inline-flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg border border-outline text-xs text-on-surface ${
            stage === 'idle' ? 'hover:border-cadmium-amber cursor-pointer' : 'opacity-60'
          }`}
          title="Builds a new, private version of this skill from your own image, video or recording"
        >
          <FileUp className="w-3.5 h-3.5" aria-hidden="true" /> {meta.uploadLabel}
          <input
            type="file"
            accept={meta.accept}
            className="sr-only"
            disabled={stage !== 'idle'}
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = '';
              if (f) void upload(f);
            }}
          />
        </label>
      )}
      {stage === 'uploading' && <ProgressBar value={progress} label="Uploading source" />}
      {stage === 'building' && <Spinner label="Building the skill from your source…" />}
      <ErrorNote error={err} />
    </div>
  );
}
