/** First-time-user guide: the loop in plain words, what the AI does, and what the labels mean. */

import React from 'react';
import { Award, Compass, FileUp, Play, RotateCcw, X } from 'lucide-react';
import { useEscape } from '../hero/useEscape';

const STEPS: { icon: React.ReactNode; title: string; text: string }[] = [
  {
    icon: <FileUp className="w-5 h-5 text-cadmium-amber" aria-hidden="true" />,
    title: 'Pick a skill',
    text: 'Start with the Kolam drawing: you draw in the browser, no files needed. Or upload your own source to share a new skill.',
  },
  {
    icon: <Compass className="w-5 h-5 text-caliper-cyan" aria-hidden="true" />,
    title: '1 · Learn',
    text: 'See what the source teaches. Every step links back to the source, so you can see where it came from.',
  },
  {
    icon: <Play className="w-5 h-5 text-transmission-emerald" aria-hidden="true" />,
    title: '2 · Practise',
    text: 'Do the task once. Anveshan shows where you first went off track and suggests one focused exercise.',
  },
  {
    icon: <RotateCcw className="w-5 h-5 text-cadmium-amber" aria-hidden="true" />,
    title: 'Retry once',
    text: 'Do the whole task again, using the feedback.',
  },
  {
    icon: <Award className="w-5 h-5 text-transmission-emerald" aria-hidden="true" />,
    title: '3 · Results',
    text: 'See what changed between your two tries, check by check, saved as a record.',
  },
];

const LABELS: [string, string][] = [
  ['Checked by an expert', 'A person reviewed the steps and confirmed or corrected them.'],
  ['Not yet checked by an expert', 'The steps come from an openly licensed source and the AI. No expert has reviewed them yet.'],
  ["AI's reading", 'The AI perceived this from the source. Useful, but it may be wrong.'],
  ['Synthetic example (made up for the demo)', 'Made-up data used to demonstrate the interface. Nothing is evaluated.'],
  ['Advice worded by AI', 'The advice text was written by the AI from the measured findings. Scores are never set by AI.'],
  ['Not scored', 'This exercise is for practice only. Only your second full try is checked.'],
  ['Met / Partly met / Not met / Couldn\'t tell', 'Result of each check. "Couldn\'t tell" means there wasn\'t enough evidence to decide; it scores zero.'],
  ['From an openly licensed internet source', 'The source is openly licensed media from the internet, not a verified expert.'],
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
      <strong className="text-on-surface">What the AI does:</strong> reads the source and your attempt, describes what it sees, and words the coaching.{' '}
      <strong className="text-on-surface">What it never does:</strong> decide your score. Scores come from fixed rules over measurements, and every piece of feedback cites the source step it is based on.
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

          {/* Three ways to use Anveshan */}
          <div>
            <h3 className="text-sm font-semibold text-on-surface mb-2">Three ways to use Anveshan</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex gap-3">
                <span className="font-semibold text-cadmium-amber shrink-0 w-16">Learn:</span>
                <span className="text-on-surface-variant">Practise a skill and get feedback.</span>
              </li>
              <li className="flex gap-3">
                <span className="font-semibold text-caliper-cyan shrink-0 w-16">Share:</span>
                <span className="text-on-surface-variant">Turn something you know into a practice task.</span>
              </li>
              <li className="flex gap-3">
                <span className="font-semibold text-transmission-emerald shrink-0 w-16">Steward:</span>
                <span className="text-on-surface-variant">Look after a library of skills, with an access code.</span>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-on-surface mb-2">What the labels mean</h3>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-sm">
              {LABELS.map(([k, v]) => (
                <div key={k} className="flex gap-3">
                  <dt className="shrink-0 w-48 font-semibold text-xs text-cadmium-amber pt-0.5">{k}</dt>
                  <dd className="text-on-surface-variant">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="border-t border-outline pt-4">
            <button
              type="button"
              className="text-sm text-caliper-cyan hover:underline"
              onClick={() => {
                onClose();
                window.dispatchEvent(new CustomEvent('anveshan:go-evidence'));
              }}
            >
              How we check results →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
