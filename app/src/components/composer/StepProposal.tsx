/**
 * Step 3c: Proposal — three-column review + editable SkillModel (K8 §5).
 *
 * Column 1: OBSERVED — probe facts, structures/specialists availability, intake safety.
 * Column 2: INFERRED — property regions (image), step strip (video), transcript (audio).
 * Column 3: Editable SkillModel — title, summary, domain, structures, properties,
 *   steps, constraints, checks table, learner input kinds.
 *
 * Validation: at least one enabled check, at least one learner kind, no empty names.
 * All AI-perceived elements are labelled INFERRED.
 */

import React, { useState } from 'react';
import type { CaseProfile, DraftView, SkillCheck, SkillConstraint, SkillModel, SkillStep, TargetProperty } from '../../api/types';
import { Badge, ErrorNote, Panel } from '../../hero/ui';
import { API_BASE } from '../../api/runtime';
import { DEBUG } from '../../api/debug';

interface Props {
  draft: DraftView;
  sourceUrl?: string | null;
  onCreate: (draft: DraftView, skillModel: SkillModel) => void;
  onStartOver: () => void;
  error: unknown;
}

// ---------- helpers ----------

function AvailabilityRow({ label, available, reason }: { label: string; available: boolean; reason?: string }) {
  return (
    <li className="flex items-start gap-2 text-[11px]">
      <span className={`font-mono font-bold shrink-0 ${available ? 'text-transmission-emerald' : 'text-on-surface-variant'}`}>{available ? '✓' : '✗'}</span>
      <span className={available ? 'text-on-surface' : 'text-on-surface-variant'}>{label}</span>
      {DEBUG && reason && <span className="text-on-surface-variant ml-1">— {reason}</span>}
    </li>
  );
}

function InferredBadge() {
  return <span className="inline-flex items-center px-1 py-0 rounded text-[11px] font-mono font-bold uppercase bg-cadmium-amber/10 text-cadmium-amber border border-cadmium-amber/30">AI's reading</span>;
}

function ObservedBadge() {
  return <span className="inline-flex items-center px-1 py-0 rounded text-[11px] font-mono font-bold uppercase bg-transmission-emerald/10 text-transmission-emerald border border-transmission-emerald/30">Measured</span>;
}

function MethodBadge({ method }: { method: string }) {
  if (method === 'deterministic') return <Badge tone="emerald">MEASURED</Badge>;
  if (method === 'specialist') return <Badge tone="cyan">SPECIALIST</Badge>;
  return <Badge tone="amber">AI-JUDGED</Badge>;
}

// ---------- column 1: observed ----------

function ColObserved({ draft }: { draft: DraftView }) {
  const probe = draft.probe;
  const intake = draft.intake;
  const safety = intake.safety as { decision?: string; categories?: string[]; flags?: string[] };

  return (
    <div className="space-y-4">
      <div>
        <div className="text-[11px] font-mono uppercase tracking-wider text-transmission-emerald font-bold mb-2">What we measured</div>        <table className="w-full text-[11px] border-collapse">
          <tbody>
            <tr className="border-b border-outline/30"><td className="py-1 text-on-surface-variant pr-2">Type</td><td className="py-1 font-mono text-on-surface">{probe.mime_type}</td></tr>
            <tr className="border-b border-outline/30"><td className="py-1 text-on-surface-variant pr-2">Size</td><td className="py-1 font-mono text-on-surface">{(probe.bytes / 1e6).toFixed(2)} MB</td></tr>
            {probe.width != null && <tr className="border-b border-outline/30"><td className="py-1 text-on-surface-variant pr-2">Dimensions</td><td className="py-1 font-mono text-on-surface">{probe.width}×{probe.height}</td></tr>}
            {probe.duration_sec != null && <tr className="border-b border-outline/30"><td className="py-1 text-on-surface-variant pr-2">Duration</td><td className="py-1 font-mono text-on-surface">{probe.duration_sec.toFixed(1)} s</td></tr>}
            {probe.metrics && Object.entries(probe.metrics).slice(0, 4).map(([k, v]) => (
              <tr key={k} className="border-b border-outline/30"><td className="py-1 text-on-surface-variant pr-2 capitalize">{k.replace(/_/g, ' ')}</td><td className="py-1 font-mono text-on-surface">{typeof v === 'number' ? v.toFixed(3) : String(v)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      <div>
        <div className="text-[11px] font-mono uppercase tracking-wider text-on-surface-variant font-bold mb-2">Structures available</div>
        <ul className="space-y-1">
          {(['final_state', 'procedure', 'temporal_pattern', 'utterance'] as const).map((s) => (
            <AvailabilityRow key={s} label={draft.structure_labels[s] ?? s} available={probe.structures_available.includes(s)} reason={probe.reasons?.[s]} />
          ))}
        </ul>
      </div>

      {probe.specialists_available != null && probe.specialists_available.length > 0 && (
        <div>
          <div className="text-[11px] font-mono uppercase tracking-wider text-on-surface-variant font-bold mb-2">Specialists available</div>
          <ul className="space-y-1">
            {Object.keys(draft.specialist_labels).map((sp) => (
              <AvailabilityRow key={sp} label={draft.specialist_labels[sp] ?? sp} available={(probe.specialists_available ?? []).includes(sp)} reason={probe.reasons?.[sp]} />
            ))}
          </ul>
        </div>
      )}

      <div>
        <div className="text-[11px] font-mono uppercase tracking-wider text-on-surface-variant font-bold mb-2">Safety decision</div>
        <div className="text-[11px] space-y-0.5">
          <div className={safety.decision === 'refuse' ? 'text-divergence-crimson font-mono font-bold' : 'text-transmission-emerald font-mono'}>{safety.decision?.toUpperCase() ?? 'SAFE'}</div>
          {safety.categories && !safety.categories.includes('none') && <div className="text-on-surface-variant">Categories: {safety.categories.join(', ')}</div>}
          {safety.flags && safety.flags.length > 0 && <div className="text-cadmium-amber">Flags: {safety.flags.join(', ')}</div>}
          {intake.teachable !== 'yes' && <div className="text-cadmium-amber">Teachable: {intake.teachable} — {intake.teachable_reason}</div>}
        </div>
      </div>
    </div>
  );
}

// ---------- column 2: inferred (perceptual) ----------

function ColInferred({ draft, sourceUrl }: { draft: DraftView; sourceUrl?: string | null }) {
  const probe = draft.probe;
  const proposal = draft.proposal;
  const obs = draft.perception.observations;

  if (probe.modality === 'image' && proposal) {
    const sm = proposal.skill_model;
    const props = sm.goal_state ?? [];
    return (
      <div className="space-y-4">
        <div className="text-[11px] font-mono uppercase tracking-wider text-cadmium-amber font-bold mb-2">What the AI understood <InferredBadge /></div>
        <div className="relative border border-outline rounded-lg overflow-hidden bg-surface-dim" style={{ minHeight: '140px' }}>
          {sourceUrl ? (
            <img src={sourceUrl} alt="Uploaded source" className="block w-full h-auto" />
          ) : (
            <div className="p-4 text-[11px] font-mono text-on-surface-variant text-center">[Source image preview unavailable]</div>
          )}
          {/* Overlay property region boxes */}
          {props.filter((p) => p.region).map((p) => (
            <div key={p.prop_id} className="absolute border-2 border-cadmium-amber/70 rounded" style={{ left: `${p.region![0]}%`, top: `${p.region![1]}%`, width: `${p.region![2]}%`, height: `${p.region![3]}%` }} title={p.statement} />
          ))}
        </div>
        <ul className="space-y-1.5">
          {props.slice(0, 6).map((p) => (
            <li key={p.prop_id} className="flex items-start gap-2 text-[11px]">
              {p.certainty === 'observed' ? <ObservedBadge /> : <InferredBadge />}
              <span className="text-on-surface">{p.statement}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  if (probe.modality === 'video' && proposal) {
    const sm = proposal.skill_model;
    const steps = sm.steps ?? [];
    return (
      <div className="space-y-4">
        <div className="text-[11px] font-mono uppercase tracking-wider text-cadmium-amber font-bold mb-2">What the AI understood <InferredBadge /></div>
        <p className="text-xs text-on-surface-variant">Gemini watched your video and picked one moment for each step it saw.</p>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {steps.filter((s) => s.keyframe_asset).map((s) => (
            <figure key={s.step_id} className="shrink-0 w-28">
              <img
                src={`${API_BASE}/api/compose/${draft.draft_id}/assets/${s.keyframe_asset}`}
                alt={`Step ${s.index + 1}: ${s.name}`}
                className="w-full aspect-video object-cover rounded border border-outline bg-surface-dim"
                loading="lazy"
              />
              <figcaption className="text-[11px] text-on-surface-variant mt-0.5 leading-tight">
                <span className="font-mono">{s.start_sec != null ? `${s.start_sec.toFixed(0)} s` : ''}</span> {s.name}
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    );
  }

  if (probe.modality === 'audio') {
    const utterance = proposal?.skill_model.utterance as { transcript?: string } | null | undefined;
    const transcript = utterance?.transcript;
    const onsetObs = obs.find((o) => o.kind === 'measurement' && o.label.includes('onset'));
    const speechObs = obs.find((o) => o.kind === 'speech');
    return (
      <div className="space-y-4">
        <div className="text-[11px] font-mono uppercase tracking-wider text-cadmium-amber font-bold mb-2">What the AI understood <InferredBadge /></div>
        {transcript && (
          <div className="p-3 rounded-lg border border-outline bg-surface-dim">
            <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-1">What was said (AI transcript)</div>
            <p className="text-sm text-on-surface font-mono">"{transcript}"</p>
          </div>
        )}
        {speechObs && !transcript && (
          <div className="text-[11px] font-mono text-on-surface-variant"><InferredBadge /> {speechObs.label}</div>
        )}
        {onsetObs && <div className="text-[11px] font-mono"><ObservedBadge /> Onsets: {onsetObs.value} (rate {obs.find((o) => o.unit === '/s')?.value ?? '—'}/s)</div>}
        <ul className="space-y-1">
          {obs.filter((o) => o.certainty === 'inferred').slice(0, 5).map((o) => (
            <li key={o.obs_id} className="flex items-start gap-2 text-[11px]"><InferredBadge /><span className="text-on-surface">{o.label}</span></li>
          ))}
        </ul>
      </div>
    );
  }

  return <div className="text-[11px] font-mono text-on-surface-variant">No perception data available.</div>;
}

// ---------- column 3: editable SkillModel ----------

interface SkillModelEditorProps {
  proposal: CaseProfile;
  model: SkillModel;
  onChange: (m: SkillModel) => void;
  validationError: string | null;
}

function SkillModelEditor({ proposal: _proposal, model, onChange, validationError }: SkillModelEditorProps) {
  const setField = <K extends keyof SkillModel>(key: K, val: SkillModel[K]) => onChange({ ...model, [key]: val });

  const updateProp = (idx: number, patch: Partial<TargetProperty>) => {
    const goal_state = model.goal_state ? [...model.goal_state] : [];
    goal_state[idx] = { ...goal_state[idx], ...patch };
    onChange({ ...model, goal_state });
  };

  const updateStep = (idx: number, patch: Partial<SkillStep>) => {
    const steps = model.steps ? [...model.steps] : [];
    steps[idx] = { ...steps[idx], ...patch };
    onChange({ ...model, steps });
  };

  const updateConstraint = (idx: number, patch: Partial<SkillConstraint>) => {
    const constraints = model.constraints ? [...model.constraints] : [];
    constraints[idx] = { ...constraints[idx], ...patch };
    onChange({ ...model, constraints });
  };

  const updateCheck = (idx: number, patch: Partial<SkillCheck>) => {
    const checks = [...model.checks];
    checks[idx] = { ...checks[idx], ...patch };
    onChange({ ...model, checks });
  };

  const allKinds = ['image', 'trace', 'audio', 'video'];
  // Allowed kinds: union of structure attempt kinds
  const allowedKinds = allKinds.filter((k) => {
    if (k === 'trace' && !((model.specialists ?? {})['line_art'] !== undefined)) return false;
    return true;
  });

  const toggleKind = (kind: string) => {
    const current = model.relevance?.expected_kinds ?? [];
    const next = current.includes(kind) ? current.filter((k) => k !== kind) : [...current, kind];
    if (next.length > 0) onChange({ ...model, relevance: { ...model.relevance, expected_kinds: next } });
  };

  const enabledKinds = model.relevance?.expected_kinds ?? [];

  return (
    <div className="space-y-5">
      <div className="text-[11px] font-mono uppercase tracking-wider text-on-surface-variant font-bold">How we'll teach and check it</div>

      {/* Basic fields */}
      <div className="space-y-2">
        <label className="block">
          <span className="text-[11px] font-mono uppercase text-on-surface-variant">Title</span>
          <input
            value={model.skill_title ?? ''}
            onChange={(e) => setField('skill_title', e.target.value)}
            className="mt-0.5 w-full bg-surface-dim border border-outline rounded px-2.5 py-1.5 text-xs outline-none focus:border-caliper-cyan"
            aria-label="Skill title"
          />
        </label>
        <label className="block">
          <span className="text-[11px] font-mono uppercase text-on-surface-variant">Summary</span>
          <textarea
            value={model.summary ?? ''}
            rows={2}
            onChange={(e) => setField('summary', e.target.value)}
            className="mt-0.5 w-full bg-surface-dim border border-outline rounded px-2.5 py-1.5 text-xs outline-none focus:border-caliper-cyan resize-none"
            aria-label="Skill summary"
          />
        </label>
      </div>

      {/* Structures (read-only chips) */}
      <div>
        <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-1">Structures</div>
        <div className="flex flex-wrap gap-1">
          {model.structures.map((s) => (
            <span key={s} className="px-2 py-0.5 rounded-full bg-surface-container border border-outline text-[11px] font-mono">{s}</span>
          ))}
        </div>
      </div>

      {/* Goal properties */}
      {(model.goal_state ?? []).length > 0 && (
        <div>
          <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-1">Goal properties</div>
          <ul className="space-y-1.5">
            {(model.goal_state ?? []).map((p, i) => (
              <li key={p.prop_id} className="flex items-start gap-2">
                <input type="checkbox" checked={p.keep !== false} onChange={(e) => updateProp(i, { keep: e.target.checked })} className="mt-1 accent-cadmium-amber" aria-label={`Keep property ${i + 1}`} />
                <input
                  value={p.statement}
                  onChange={(e) => updateProp(i, { statement: e.target.value })}
                  className="flex-1 bg-surface-dim border border-outline rounded px-2 py-1 text-[11px] outline-none focus:border-caliper-cyan"
                  aria-label={`Property ${i + 1} statement`}
                />
                <InferredBadge />
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Steps */}
      {(model.steps ?? []).length > 0 && (
        <div>
          <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-1">Steps</div>
          <ul className="space-y-1.5">
            {(model.steps ?? []).map((s, i) => (
              <li key={s.step_id} className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-on-surface-variant w-4">{s.index + 1}</span>
                <input
                  value={s.name}
                  onChange={(e) => updateStep(i, { name: e.target.value })}
                  className="flex-1 bg-surface-dim border border-outline rounded px-2 py-1 text-[11px] outline-none focus:border-caliper-cyan"
                  aria-label={`Step ${i + 1} name`}
                />
                <label className="flex items-center gap-1 text-[11px] font-mono text-on-surface-variant shrink-0">
                  <input type="checkbox" checked={s.critical === true} onChange={(e) => updateStep(i, { critical: e.target.checked })} className="accent-divergence-crimson" aria-label={`Step ${i + 1} critical`} />
                  critical
                </label>
                <span className="text-[11px] font-mono text-on-surface-variant">{s.source_established ? 'DEMONSTRATED' : 'SUGGESTED'}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Constraints */}
      {(model.constraints ?? []).length > 0 && (
        <div>
          <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-1">Constraints</div>
          <ul className="space-y-1">
            {(model.constraints ?? []).map((c, i) => (
              <li key={c.constraint_id} className="flex items-center gap-2 text-[11px]">
                <input type="checkbox" checked={c.keep !== false} onChange={(e) => updateConstraint(i, { keep: e.target.checked })} className="accent-cadmium-amber" aria-label={`Keep constraint ${i + 1}`} />
                <span className="text-on-surface-variant">{c.statement}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Checks table */}
      <div>
        <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-1">Checks</div>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] border-collapse">
            <thead>
              <tr className="border-b border-outline text-on-surface-variant">
                <th className="text-left py-1 pr-2 font-mono font-normal">On</th>
                <th className="text-left py-1 pr-2 font-mono font-normal">Name</th>
                <th className="text-left py-1 pr-2 font-mono font-normal">Weight</th>
                <th className="text-left py-1 pr-2 font-mono font-normal">Required</th>
                <th className="text-left py-1 font-mono font-normal">How it is checked</th>
              </tr>
            </thead>
            <tbody>
              {model.checks.map((c, i) => (
                <tr key={c.check_id} className="border-b border-outline/30">
                  <td className="py-1 pr-2">
                    <input type="checkbox" checked={c.enabled !== false} onChange={(e) => updateCheck(i, { enabled: e.target.checked })} className="accent-cadmium-amber" aria-label={`Enable check ${c.check_id}`} />
                  </td>
                  <td className="py-1 pr-2 text-on-surface leading-snug">{c.name}</td>
                  <td className="py-1 pr-2">
                    <select
                      value={c.weight ?? 2}
                      onChange={(e) => updateCheck(i, { weight: Number(e.target.value) })}
                      className="bg-surface-dim border border-outline rounded px-1 py-0.5 font-mono text-[11px] outline-none"
                      aria-label={`Weight for ${c.check_id}`}
                    >
                      {[1, 2, 3, 4, 5].map((w) => <option key={w} value={w}>{w}</option>)}
                    </select>
                  </td>
                  <td className="py-1 pr-2">
                    <input type="checkbox" checked={c.required === true} onChange={(e) => updateCheck(i, { required: e.target.checked })} className="accent-divergence-crimson" aria-label={`Required: ${c.check_id}`} />
                  </td>
                  <td className="py-1"><MethodBadge method={c.method} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Learner input kinds */}
      <div>
        <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-1">Learner input kinds</div>
        <div className="flex flex-wrap gap-2">
          {allKinds.map((kind) => {
            const allowed = allowedKinds.includes(kind);
            const enabled = enabledKinds.includes(kind);
            return (
              <label key={kind} className={`flex items-center gap-1.5 text-[11px] font-mono ${!allowed ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}>
                <input type="checkbox" checked={enabled} disabled={!allowed} onChange={() => toggleKind(kind)} className="accent-cadmium-amber" aria-label={`Allow ${kind} attempts`} />
                {kind}
              </label>
            );
          })}
        </div>
      </div>

      {validationError && <p className="text-[11px] font-mono text-divergence-crimson">{validationError}</p>}
    </div>
  );
}

// ---------- main component ----------

export function StepProposal({ draft, sourceUrl, onCreate, onStartOver, error }: Props) {
  const proposal = draft.proposal!;
  const [model, setModel] = useState<SkillModel>({ ...proposal.skill_model });
  const [validErr, setValidErr] = useState<string | null>(null);

  const validate = (): string | null => {
    if (!model.checks.some((c) => c.enabled !== false)) return 'At least one check must be enabled.';
    if ((model.relevance?.expected_kinds ?? []).length === 0) return 'At least one learner input kind must be selected.';
    const emptyProp = (model.goal_state ?? []).find((p) => p.keep !== false && !p.statement.trim());
    if (emptyProp) return 'Goal property statements cannot be empty.';
    const emptyStep = (model.steps ?? []).find((s) => !s.name.trim());
    if (emptyStep) return `Step ${emptyStep.index + 1} name cannot be empty.`;
    return null;
  };

  const handleCreate = () => {
    const err = validate();
    if (err) { setValidErr(err); return; }
    setValidErr(null);
    onCreate(draft, model);
  };

  return (
    <div className="flex flex-col gap-4 w-full animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="text-[11px] font-mono uppercase tracking-widest text-cadmium-amber font-bold">Composer · Step 3 — Review proposal</div>
          <h2 className="text-2xl font-serif text-on-surface">{proposal.title}</h2>
          <div className="flex flex-wrap gap-1 text-[11px] font-mono text-on-surface-variant">
            <span>{proposal.domain}</span>
            <span>·</span>
            <span>{proposal.transmission_mode}</span>
            {proposal.skill_model.structures.map((s) => <span key={s} className="text-caliper-cyan">· {s}</span>)}
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={onStartOver} className="text-[11px] font-mono text-on-surface-variant hover:text-on-surface">Start over</button>
        </div>
      </div>

      {draft.warnings.map((w, i) => <p key={i} className="text-[11px] font-mono text-cadmium-amber">⚠ {w}</p>)}
      <p className="text-[11px] font-mono text-cadmium-amber">Next you'll check these steps. Nothing is shared until you publish.</p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Panel kicker="What we measured" className="min-w-0">
          <ColObserved draft={draft} />
        </Panel>
        <Panel kicker="What the AI understood" className="min-w-0">
          <ColInferred draft={draft} sourceUrl={sourceUrl} />
        </Panel>
        <Panel kicker="How we'll teach and check it" className="min-w-0">
          <SkillModelEditor proposal={proposal} model={model} onChange={setModel} validationError={validErr} />
        </Panel>
      </div>

      <ErrorNote error={error} />

      <div className="flex items-center gap-3 pt-2">
        <button
          onClick={handleCreate}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-mono font-bold text-[11px] uppercase tracking-wider transition-colors"
        >
          Create skill
        </button>
        <button onClick={onStartOver} className="text-[11px] font-mono text-on-surface-variant hover:text-on-surface">Start over</button>
      </div>
    </div>
  );
}
