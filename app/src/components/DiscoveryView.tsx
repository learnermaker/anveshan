import React, { useState } from 'react';
import { Activity, ArrowRight, Compass, Eye, HelpCircle, Layers, Music, PlusCircle, RefreshCw, Scissors, Shield, Sparkles, Wrench } from 'lucide-react';
import { CAPABILITY_CASES, SHOWCASE_CASE_IDS } from '../data/cases/registry';
import type { CaseSummary } from '../api/types';
import { api } from '../api/client';
import { IS_MOCK, API_BASE } from '../api/runtime';
import { Badge, ErrorNote, Panel, ReviewBadge, SourceLabelBadge, Spinner } from '../hero/ui';
import { AiRoleNote, HowItWorksSteps } from './HowItWorks';
import { MODALITY_PHRASE, PITCH, SOURCE_LABEL } from '../copy/plain';

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

const MODALITY_ICON: Record<string, React.ReactNode> = {
  kolam_image: <Compass className="w-5 h-5 text-transmission-emerald" />,
  origami_video: <Scissors className="w-5 h-5 text-cadmium-amber" />,
  tabla_audio: <Music className="w-5 h-5 text-caliper-cyan" />,
  universal: <Sparkles className="w-5 h-5 text-caliper-cyan" />,
};

const SHOWCASE_ICON: Record<string, React.ReactNode> = {
  micrometer: <Activity className="w-5 h-5 text-caliper-cyan" />,
  bicycle_repair: <Wrench className="w-5 h-5 text-cadmium-amber" />,
  weaving: <Layers className="w-5 h-5 text-caliper-cyan" />,
  square_knot: <Shield className="w-5 h-5 text-divergence-crimson" />,
};

export function DiscoveryView({ heroCases, heroError, heroLoading, onRefreshHero, onSelect, selected, onOpenGuide, onOpenMine }: DiscoveryViewProps) {
  const allCases = heroCases ?? [];

  // Featured skills: curated, published (or no access field = legacy)
  const featured = allCases.filter((c) => c.hero && ((c.access?.library_status ?? 'published') === 'published'));

  // Shared by community: composed, published, not featured, not owned by the visitor
  const community = allCases.filter((c) => c.composed && !c.hero && c.access?.library_status === 'published' && !c.access?.owner);

  // Owned skills count
  const ownedSkills = allCases.filter((c) => c.access?.owner);

  return (
    <div className="flex flex-col gap-10 max-w-6xl w-full mx-auto p-2 lg:p-6 animate-fade-in text-on-surface">
      {/* Hero */}
      <section className="text-center max-w-3xl mx-auto space-y-4 pt-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cadmium-amber/10 border border-cadmium-amber/30 text-cadmium-amber font-mono text-[11px] font-semibold uppercase tracking-widest">
          Google Cloud AI Builder Cup 2026 · Prototype
        </div>
        <h1 className="font-serif text-4xl sm:text-5xl font-normal tracking-tight leading-[1.15]">{PITCH.headline}</h1>
        <p className="text-base text-on-surface-variant max-w-2xl mx-auto leading-relaxed">{PITCH.lead}</p>
        <div className="flex flex-wrap items-center justify-center gap-3 pt-1">
          <button
            onClick={() => onSelect({ kind: 'hero', id: 'kolam' })}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-semibold text-sm"
          >
            Start with the Kolam drawing (about 2 minutes) <ArrowRight className="w-4 h-4" aria-hidden="true" />
          </button>
          <button
            onClick={() => onSelect({ kind: 'composer' })}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-outline hover:border-caliper-cyan text-sm text-on-surface"
          >
            Share a skill you know
          </button>
        </div>
        {onOpenGuide && (
          <button onClick={onOpenGuide} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-outline hover:border-cadmium-amber text-sm text-on-surface">
            <HelpCircle className="w-4 h-4 text-cadmium-amber" aria-hidden="true" /> What the labels mean
          </button>
        )}
      </section>

      {/* Why it is different: skills of the physical world */}
      <section aria-label="What makes Anveshan different" className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {PITCH.points.map((p, i) => (
          <div key={p.title} className="p-4 rounded-xl border border-outline bg-surface-container-low space-y-1.5">
            <div className="flex items-center gap-2">
              {[<Eye key="e" className="w-4 h-4 text-cadmium-amber" aria-hidden="true" />, <Compass key="c" className="w-4 h-4 text-caliper-cyan" aria-hidden="true" />, <Shield key="s" className="w-4 h-4 text-transmission-emerald" aria-hidden="true" />][i]}
              <h2 className="text-sm font-semibold text-on-surface">{p.title}</h2>
            </div>
            <p className="text-sm text-on-surface-variant leading-relaxed">{p.text}</p>
          </div>
        ))}
      </section>

      {/* How it works */}
      <section aria-labelledby="how-title" className="space-y-3">
        <h2 id="how-title" className="text-xs font-mono uppercase tracking-widest text-on-surface-variant font-bold">
          How it works
        </h2>
        <HowItWorksSteps compact />
        <AiRoleNote />
      </section>

      {/* Featured skills */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-outline pb-3">
          <div>
            <div className="text-xs font-mono uppercase tracking-widest text-cadmium-amber font-bold">Featured skills</div>
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
          {featured.map((c) => (
            <HeroCard key={c.case_id} c={c} active={selected.kind === 'hero' && selected.id === c.case_id} onOpen={(id) => onSelect({ kind: 'hero', id })} />
          ))}
        </div>
      </section>

      {/* Shared by the community */}
      <section className="space-y-4">
        <div className="border-b border-outline pb-3">
          <div className="text-xs font-mono uppercase tracking-widest text-caliper-cyan font-bold">Shared by the community</div>
          <h2 className="text-xl font-semibold font-serif">Skills shared by other learners</h2>
        </div>
        {community.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {community.map((c) => (
              <div key={c.case_id} className="p-5 rounded-xl border border-outline bg-surface-container-low flex flex-col gap-3">
                <div>
                  <h3 className="font-semibold text-base" data-plain-exempt>{c.title}</h3>
                  <p className="text-sm text-on-surface-variant mt-0.5">
                    Shared by {c.access?.credit_name ?? 'a creator'}
                  </p>
                </div>
                <ReviewBadge status={c.review_status} />
                <button
                  onClick={() => onSelect({ kind: 'hero', id: c.case_id })}
                  className="mt-auto inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-semibold text-sm"
                >
                  Start <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-5 rounded-xl border border-dashed border-outline bg-surface-container-low text-center space-y-3">
            <p className="text-sm text-on-surface-variant">No community skills yet. Share one you know.</p>
            <button
              onClick={() => onSelect({ kind: 'composer' })}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-semibold text-sm"
            >
              Share a skill you know
            </button>
          </div>
        )}
      </section>

      {/* Your skills + composer teaser */}
      <section className="space-y-4">
        <div className="border-b border-outline pb-3">
          <div className="text-xs font-mono uppercase tracking-widest text-caliper-cyan font-bold">Share a skill</div>
          <h2 className="text-xl font-semibold font-serif">{PITCH.shareHeading}</h2>
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
            </div>
            <div>
              <h3 className="font-semibold text-base">Share a skill you know</h3>
            </div>
            <p className="text-sm text-on-surface-variant leading-relaxed">{PITCH.shareText}</p>
            <div className="mt-auto inline-flex items-center gap-1.5 text-sm font-semibold text-caliper-cyan">
              <Sparkles className="w-4 h-4" aria-hidden="true" /> Open the composer
            </div>
          </button>

          {ownedSkills.length > 0 && onOpenMine && (
            <div className="p-5 rounded-xl border border-outline bg-surface-container-low flex flex-col justify-center gap-3">
              <p className="text-sm text-on-surface">
                You have {ownedSkills.length} skill{ownedSkills.length !== 1 ? 's' : ''} in{' '}
                <button onClick={onOpenMine} className="text-caliper-cyan underline font-semibold">
                  My skills
                </button>.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Synthetic examples (collapsed) */}
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
                <div className="font-semibold text-sm" data-plain-exempt>{c.title}</div>
                <div className="text-xs font-mono text-on-surface-variant" data-plain-exempt>{c.archetype}</div>
              </button>
            );
          })}
        </div>
      </details>
    </div>
  );
}

function HeroCard({ c, active, onOpen }: { c: CaseSummary; active: boolean; onOpen: (id: string) => void }) {
  const icon = MODALITY_ICON[c.modality] ?? <Sparkles className="w-5 h-5 text-caliper-cyan" />;
  const modalityPhrase = MODALITY_PHRASE[c.modality] ?? 'Practise and upload your attempt';
  const sourceLabel = SOURCE_LABEL[c.runtime_label] ?? c.runtime_label;

  return (
    <div className={`p-5 rounded-xl border flex flex-col gap-3 transition-colors ${active ? 'border-cadmium-amber bg-surface-container shadow-lg shadow-cadmium-amber/10' : 'border-outline bg-surface-container-low'}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="w-10 h-10 rounded-lg bg-surface-dim border border-outline flex items-center justify-center">{icon}</div>
        <ReviewBadge status={c.review_status} />
      </div>
      <div>
        <h3 className="font-semibold text-base" data-plain-exempt>{c.title}</h3>
        <p className="text-sm text-on-surface-variant mt-1 leading-relaxed">
          What you'll do: {modalityPhrase}
        </p>
        <p className="text-xs text-on-surface-variant mt-1">{sourceLabel}</p>
      </div>
      <button
        onClick={() => onOpen(c.case_id)}
        className="mt-auto inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-semibold text-sm"
      >
        Start <ArrowRight className="w-4 h-4" aria-hidden="true" />
      </button>
    </div>
  );
}
