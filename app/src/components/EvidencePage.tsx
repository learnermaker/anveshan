/**
 * "How we check results" page — explains the checking process in plain words.
 * Route: ?view=evidence
 * Entry: footer link "How we check results", WhyThisFeedback link, HowItWorks guide.
 */
import React, { useEffect, useState } from 'react';
import { ArrowLeft, BookOpen, Compass, ListChecks, RotateCcw, Search } from 'lucide-react';
import { Spinner } from '../hero/ui';

// ---- Schema for /evidence.json (written by K9-B2) --------------------------

interface EvidenceSkill {
  case_id: string;
  title: string;
  runs_per_sample: number;
  consistency: number;
  samples: {
    good: SampleValue;
    flawed: SampleValue;
    unrelated: SampleValue;
  };
  notes?: string;
}

type SampleValue = 'passed' | 'caught' | 'refused' | 'missed' | 'failed';

interface EvidenceJson {
  generated_at: string;
  tests: { count: number; date: string };
  skills: EvidenceSkill[];
  not_yet: string[];
}

// ---- Sample result display ------------------------------------------------

const SAMPLE_DISPLAY: Record<SampleValue, { label: string; className: string }> = {
  passed:  { label: 'Good attempt passed',         className: 'text-transmission-emerald' },
  caught:  { label: 'Mistake caught',               className: 'text-transmission-emerald' },
  refused: { label: 'Unrelated attempt refused',    className: 'text-transmission-emerald' },
  missed:  { label: 'Mistake missed',               className: 'text-cadmium-amber' },
  failed:  { label: 'Good attempt failed',          className: 'text-cadmium-amber' },
};

// ---- Five steps (what happens to your attempt) ----------------------------

const HOW_STEPS: { icon: React.ReactNode; text: string }[] = [
  {
    icon: <Compass className="w-5 h-5 text-caliper-cyan shrink-0" aria-hidden="true" />,
    text: 'We compare it with what the source shows (the goal).',
  },
  {
    icon: <ListChecks className="w-5 h-5 text-caliper-cyan shrink-0" aria-hidden="true" />,
    text: 'Each check is measured: met, partly met, not met, or "couldn\'t tell".',
  },
  {
    icon: <Search className="w-5 h-5 text-cadmium-amber shrink-0" aria-hidden="true" />,
    text: 'We find where it first went off track.',
  },
  {
    icon: <BookOpen className="w-5 h-5 text-caliper-cyan shrink-0" aria-hidden="true" />,
    text: 'Feedback points to the step in the source it comes from.',
  },
  {
    icon: <RotateCcw className="w-5 h-5 text-transmission-emerald shrink-0" aria-hidden="true" />,
    text: 'Your second try shows what changed.',
  },
];

// ---- Component ------------------------------------------------------------

export function EvidencePage({ onBack }: { onBack: () => void }) {
  const [evidence, setEvidence] = useState<EvidenceJson | null>(null);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    fetch('/evidence.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<EvidenceJson>;
      })
      .then(setEvidence)
      .catch(() => setFetchError(true));
  }, []);

  const notYet: string[] =
    evidence?.not_yet?.length
      ? evidence.not_yet
      : [
          'No study with real learners or experts has been run yet.',
          'Internet sources are not verified experts.',
        ];

  return (
    <article className="max-w-3xl w-full mx-auto flex flex-col gap-8 animate-fade-in">

      {/* Page heading */}
      <div>
        <h1 className="font-serif text-3xl text-on-surface mb-2">How we check results</h1>
        <p className="text-sm text-on-surface-variant leading-relaxed">
          Every check is scored by fixed rules from what was measured. The AI helps perceive and
          word things; it never sets a score.
        </p>
      </div>

      {/* 1 — What happens to your attempt */}
      <section aria-labelledby="ev-steps-heading">
        <h2 id="ev-steps-heading" className="font-serif text-xl text-on-surface mb-4">
          What happens to your attempt
        </h2>
        <ol className="flex flex-col gap-3">
          {HOW_STEPS.map((step, i) => (
            <li
              key={i}
              className="flex items-start gap-3 p-4 rounded-xl border border-outline bg-surface-container"
            >
              {step.icon}
              <span className="text-sm text-on-surface leading-relaxed">{step.text}</span>
            </li>
          ))}
        </ol>
      </section>

      {/* 2 — What the AI does / does not do */}
      <section aria-labelledby="ev-ai-heading">
        <h2 id="ev-ai-heading" className="font-serif text-xl text-on-surface mb-4">
          What the AI does and does not do
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl border border-outline bg-surface-container">
            <h3 className="text-sm font-semibold text-transmission-emerald mb-3">Does</h3>
            <ul className="space-y-2 text-sm text-on-surface-variant">
              <li>Perceives uploads</li>
              <li>Suggests the steps of a new skill</li>
              <li>Words advice</li>
              <li>Answers questions from the source</li>
            </ul>
          </div>
          <div className="p-4 rounded-xl border border-outline bg-surface-container">
            <h3 className="text-sm font-semibold text-divergence-crimson mb-3">Does not</h3>
            <ul className="space-y-2 text-sm text-on-surface-variant">
              <li>Score, pass or fail</li>
              <li>Decide what is published</li>
              <li>See names in insights</li>
            </ul>
          </div>
        </div>
      </section>

      {/* 3 — How reliable has it been? */}
      <section aria-labelledby="ev-reliability-heading">
        <h2 id="ev-reliability-heading" className="font-serif text-xl text-on-surface mb-4">
          How reliable has it been?
        </h2>
        {fetchError ? (
          <p className="text-sm text-on-surface-variant">
            Reliability numbers are not available on this server.
          </p>
        ) : !evidence ? (
          <Spinner label="Loading reliability data…" />
        ) : (
          <div className="flex flex-col gap-4">
            <p className="text-xs text-on-surface-variant">
              {evidence.tests.count} tests · last run {evidence.tests.date}
            </p>
            {evidence.skills.map((skill) => {
              const consistencyPct = Math.round(skill.consistency * 100);
              return (
                <div
                  key={skill.case_id}
                  className="p-4 rounded-xl border border-outline bg-surface-container"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                    <h3
                      className="text-sm font-semibold text-on-surface"
                      data-plain-exempt="true"
                    >
                      {skill.title}
                    </h3>
                    <span className="text-xs text-on-surface-variant">
                      {skill.runs_per_sample} runs per sample ·{' '}
                      <span
                        className={
                          consistencyPct === 100
                            ? 'text-transmission-emerald font-semibold'
                            : 'text-cadmium-amber font-semibold'
                        }
                      >
                        {consistencyPct === 100
                          ? 'same result every time'
                          : `${consistencyPct}% consistent`}
                      </span>
                    </span>
                  </div>
                  <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                    <div>
                      <dt className="text-on-surface-variant mb-1">Good attempt</dt>
                      <dd
                        className={`font-semibold ${SAMPLE_DISPLAY[skill.samples.good]?.className ?? ''}`}
                      >
                        {SAMPLE_DISPLAY[skill.samples.good]?.label ?? skill.samples.good}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-on-surface-variant mb-1">Mistake attempt</dt>
                      <dd
                        className={`font-semibold ${SAMPLE_DISPLAY[skill.samples.flawed]?.className ?? ''}`}
                      >
                        {SAMPLE_DISPLAY[skill.samples.flawed]?.label ?? skill.samples.flawed}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-on-surface-variant mb-1">Unrelated attempt</dt>
                      <dd
                        className={`font-semibold ${SAMPLE_DISPLAY[skill.samples.unrelated]?.className ?? ''}`}
                      >
                        {SAMPLE_DISPLAY[skill.samples.unrelated]?.label ?? skill.samples.unrelated}
                      </dd>
                    </div>
                  </dl>
                  {skill.notes && (
                    <p className="text-xs text-on-surface-variant mt-3 pt-2 border-t border-outline">
                      {skill.notes}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* 4 — What we have not tested yet */}
      <section aria-labelledby="ev-not-yet-heading">
        <h2 id="ev-not-yet-heading" className="font-serif text-xl text-on-surface mb-4">
          What we have not tested yet
        </h2>
        <ul className="space-y-2">
          {notYet.map((item, i) => (
            <li key={i} className="text-sm text-on-surface-variant">
              {item}
            </li>
          ))}
        </ul>
      </section>

      {/* Back link */}
      <div className="pb-4">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-caliper-cyan hover:text-caliper-cyan/80 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          Back to the library
        </button>
      </div>
    </article>
  );
}
