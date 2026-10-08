/** "How this result was made": the four stages behind one attempt, from what this result actually carries. */

import React from 'react';
import type { AttemptResult, CaseView } from '../../api/types';
import type { LocalAttemptMedia } from '../session';
import { Panel } from '../ui';
import { fmtPosition } from '../locators';
import { isUniversalView } from '../universal/ResultExtras';

const CAPTURE: Record<string, string> = { video: 'video', image: 'photo', audio: 'recording', trace: 'drawing' };

export function HowChecked({ view, result, media }: { view: CaseView; result: AttemptResult; media: LocalAttemptMedia }) {
  // sample attempts arrive with media.kind 'image'; the evidence modality is what was actually checked
  const kind = media.kind === 'trace' ? 'trace' : result.attempt.evidence?.modality ?? media.kind;
  const capture = CAPTURE[kind] ?? 'attempt';
  const universal = isUniversalView(view);
  const checks = result.evaluation.criterion_results;
  const example = checks.find((c) => c.status !== 'satisfied' && c.deviation_analysis) ?? checks.find((c) => c.deviation_analysis);
  const exampleName = example && view.rubric.criteria.find((c) => c.criterion_id === example.criterion_id)?.name;
  const fd = result.first_divergence;
  const coach = result.coaching;
  const model = coach?.model_id ? `Gemini (${coach.model_id})` : 'Gemini';

  const stages: [string, React.ReactNode][] = [
    [
      universal ? 'Gemini looked at your ' + capture : 'Measured from your ' + capture,
      universal
        ? kind === 'image'
          ? `Gemini described what your ${capture} shows and compared it with the finished result in the demonstration. That is what it saw, not a grade.`
          : `Gemini picked out the key moments of your ${capture} and matched each one to a step of the demonstration. That is what it saw, not a grade.`
        : `Your ${capture} was measured directly against the goal with fixed ${kind === 'audio' ? 'audio' : 'geometry'} rules. No AI is needed to measure this skill.`,
    ],
    [
      `${checks.length} checks, scored by fixed rules`,
      <>
        Each check compares a measurement with a pass mark set before you started.
        {example && exampleName && <> For example, <b>{exampleName}</b>: <span data-plain-exempt>{example.deviation_analysis}</span></>}
        {' '}The AI cannot change a score.
      </>,
    ],
    [
      'Where you first went off track',
      fd
        ? <>The earliest check that wasn't met, in the order of the task: <b>{fd.criterion_name}</b>{fd.position != null && <> at {fmtPosition(fd.position, fd.position_kind)}</>}, linked to the matching moment in the source.</>
        : 'Every check was met, so there is no point where you went off track.',
    ],
    [
      'The advice, in plain words',
      coach?.status === 'ai_worded'
        ? `${model} rewrote the advice in plain words. A guard checked that it kept every number and source reference, or you would see the plain version.`
        : coach?.reason?.includes('guard')
          ? `${model} offered a wording, but the guard rejected it because it changed a number or a source reference, so you see the plain version.`
          : 'Plain advice from fixed templates, each one citing the source step it comes from.',
    ],
  ];

  return (
    <Panel kicker="How this result was made" title="What the AI did, and what fixed rules did">
      <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {stages.map(([title, body], i) => (
          <li key={title} className="p-3 rounded-lg bg-surface-dim border border-outline/60 text-xs space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-5 h-5 shrink-0 rounded-full border border-cadmium-amber text-cadmium-amber text-[11px] font-mono flex items-center justify-center" aria-hidden="true">{i + 1}</span>
              <span className="font-semibold text-on-surface">{title}</span>
            </div>
            <p className="text-on-surface-variant leading-relaxed">{body}</p>
          </li>
        ))}
      </ol>
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1">
        <button type="button" className="text-xs text-caliper-cyan hover:underline" onClick={() => window.dispatchEvent(new CustomEvent('anveshan:go-evidence'))}>
          How we check results →
        </button>
        {result.warnings.length > 0 && (
          <details className="text-xs">
            <summary className="text-on-surface-variant cursor-pointer select-none hover:underline">Technical notes ({result.warnings.length})</summary>
            <ul className="mt-1 text-[11px] font-mono text-on-surface-variant space-y-0.5" data-plain-exempt>
              {result.warnings.map((w, i) => <li key={i}>{w.length > 160 ? w.slice(0, 160) + '…' : w}</li>)}
            </ul>
          </details>
        )}
      </div>
    </Panel>
  );
}
