/** First-time-user guide: the loop in plain words, what the AI does, and what the labels mean. */

import React from 'react';
import { Award, Compass, FileUp, Play, RotateCcw, X } from 'lucide-react';
import { useEscape } from '../hero/useEscape';

const STEPS: { icon: React.ReactNode; title: string; text: string }[] = [
  {
    icon: <FileUp className="w-5 h-5 text-cadmium-amber" aria-hidden="true" />,
    title: 'Pick a skill',
    text: 'Start with the Kolam drawing: you draw in the browser, no files needed. Or upload your own source (an image, a video or a recording) to create a new skill.',
  },
  {
    icon: <Compass className="w-5 h-5 text-caliper-cyan" aria-hidden="true" />,
    title: '1 · Learn',
    text: 'See what the source teaches. Every step and check is a claim linked to evidence in the source, so you can see where it came from.',
  },
  {
    icon: <Play className="w-5 h-5 text-transmission-emerald" aria-hidden="true" />,
    title: '2 · Practise',
    text: 'Do the task once. Anveshan compares your attempt with the goal, shows where you first went off track, and suggests one focused drill.',
  },
  {
    icon: <RotateCcw className="w-5 h-5 text-cadmium-amber" aria-hidden="true" />,
    title: 'Retry once',
    text: 'Do the whole task again, using the feedback.',
  },
  {
    icon: <Award className="w-5 h-5 text-transmission-emerald" aria-hidden="true" />,
    title: '3 · Results',
    text: 'See what changed between your two attempts, criterion by criterion, saved as a record you can check later.',
  },
];

const LABELS: [string, string][] = [
  ['OBSERVED', 'Measured or seen directly in the source.'],
  ['INFERRED', "The AI's reading of the source. Useful, but it may be wrong."],
  ['MEASURED', 'Your attempt was checked with fixed geometry, timing or audio measurements.'],
  ['AI-JUDGED', 'An AI model looked at your attempt and answered a yes/no check. Fixed rules then turn the answers into a score.'],
  ['UNCERTAIN', 'Not enough evidence to decide. It scores zero and is shown, not hidden.'],
  ['INTERNET REFERENCE', 'The source is openly licensed media from the internet, not a verified expert.'],
  ['REVIEW: PENDING', 'No expert has reviewed this skill yet. Results are engineering evidence, not certification.'],
  ['SYNTHETIC', 'Made-up data used to demonstrate the interface. Nothing is evaluated.'],
];

export function HowItWorksSteps({ compact = false }: { compact?: boolean }) {
  return (
    <ol className={`grid grid-cols-1 sm:grid-cols-2 ${compact ? 'lg:grid-cols-5' : 'lg:grid-cols-5'} gap-3`}>
      {STEPS.map((s) => (
        <li key={s.title} className="p-4 rounded-xl border border-outline bg-surface-container-low flex flex-col gap-2">
          <div className="flex items-center gap-2">
            {s.icon}
            <span className="font-semibold text-sm text-on-surface">{s.title}</span>
          </div>
          <p className="text-sm text-on-surface-variant leading-relaxed">{s.text}</p>
        </li>
      ))}
    </ol>
  );
}

export function AiRoleNote() {
  return (
    <p className="text-sm text-on-surface-variant leading-relaxed">
      <strong className="text-on-surface">What the AI does:</strong> Google Gemini reads the source and your attempt, describes what it sees, and words the
      coaching. <strong className="text-on-surface">What it never does:</strong> decide your score. Scores come from fixed rules over measurements, and every
      piece of feedback cites the source claim it is based on.
    </p>
  );
}

export function GuideModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  useEscape(isOpen, onClose);
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-4 bg-background/80 backdrop-blur-md overflow-y-auto" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-title"
        className="w-full max-w-5xl rounded-xl border border-outline bg-surface-container shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-outline">
          <h2 id="guide-title" className="font-serif text-xl text-on-surface">How Anveshan works</h2>
          <button onClick={onClose} aria-label="Close" title="Close (Esc)" className="flex items-center gap-1 px-2 py-1 rounded text-on-surface-variant hover:text-on-surface">
            <X className="w-5 h-5" aria-hidden="true" />
            <span className="text-xs font-mono">Close</span>
          </button>
        </div>
        <div className="p-5 space-y-5">
          <HowItWorksSteps />
          <AiRoleNote />
          <div>
            <h3 className="text-sm font-semibold text-on-surface mb-2">What the labels mean</h3>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-sm">
              {LABELS.map(([k, v]) => (
                <div key={k} className="flex gap-3">
                  <dt className="shrink-0 w-40 font-mono text-xs font-bold text-cadmium-amber pt-0.5">{k}</dt>
                  <dd className="text-on-surface-variant">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
