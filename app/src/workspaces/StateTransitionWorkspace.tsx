import React, { useState } from 'react';
import { AlertTriangle, ArrowRight, CheckCircle2, Layers, Repeat, ShieldCheck, Activity } from 'lucide-react';
import type { CapabilityCase } from '../types/workspace';
import { RubricHUD } from '../components/RubricHUD';
import { TransmissionGainHero } from '../components/TransmissionGainHero';

interface StateTransitionWorkspaceProps {
  capCase: CapabilityCase;
  onOpenLineage: () => void;
  onJumpFirstDivergence: () => void;
  onLaunchRetry: () => void;
}

export function StateTransitionWorkspace({
  capCase,
  onOpenLineage,
  onJumpFirstDivergence,
  onLaunchRetry,
}: StateTransitionWorkspaceProps) {
  const telemetry = capCase.telemetry;
  const [activePick, setActivePick] = useState<number>(7); // Pick #7 is divergence locus
  const [selectedCriterionId, setSelectedCriterionId] = useState<string | null>('CRIT-SHED-CHANGE');

  const picks = [
    { pick: 1, treadle: 'T1', shedHeight: 48, status: 'SATISFIED', note: 'Clean open shed' },
    { pick: 2, treadle: 'T2', shedHeight: 46, status: 'SATISFIED', note: 'Crossed interlock verified' },
    { pick: 3, treadle: 'T1', shedHeight: 48, status: 'SATISFIED', note: 'Shuttle passed smoothly' },
    { pick: 4, treadle: 'T2', shedHeight: 47, status: 'SATISFIED', note: 'Even reed compression' },
    { pick: 5, treadle: 'T1', shedHeight: 45, status: 'SATISFIED', note: 'Selvage tension aligned' },
    { pick: 6, treadle: 'T2', shedHeight: 48, status: 'SATISFIED', note: 'Interlocking pick locked' },
    { pick: 7, treadle: 'T2 (STALE)', shedHeight: 46, status: 'DIVERGENT', note: 'Beat on uncrossed shed (FLOAT DEFECT)' },
    { pick: 8, treadle: 'T1', shedHeight: 40, status: 'PARTIAL', note: 'Loose warp recovery' },
  ];

  return (
    <div className="flex flex-col gap-6 w-full animate-fade-in">
      {/* Main Grid: State Matrix on Left (8 cols) + Rubric HUD on Right (4 cols) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left Column: Material State Transition Matrix */}
        <div className="xl:col-span-8 flex flex-col gap-4">
          <div className="bg-surface-elevated border border-outline rounded-xl p-5 shadow-xl relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-outline pb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-caliper-cyan/15 border border-caliper-cyan/30 flex items-center justify-center text-caliper-cyan">
                  <Layers className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-widest text-caliper-cyan font-bold">
                    STATE TRANSITION WORKSPACE // DISCRETE MATERIAL EVOLUTION
                  </div>
                  <h3 className="text-base font-semibold text-on-surface">
                    Two-Shaft Plain Weave Shed Sequence & Pick Interlocking
                  </h3>
                </div>
              </div>

              <div className="px-3 py-1 bg-divergence-crimson/15 border border-divergence-crimson/30 rounded font-mono text-xs text-divergence-crimson font-bold">
                DEFECT: PICK #7
              </div>
            </div>

            {/* Loom State Visualizer */}
            <div className="p-4 bg-surface-dim rounded-lg border border-outline/40 my-4 space-y-4">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-on-surface-variant font-semibold">
                  DISCRETE WEFT PICK SEQUENCE (PICKS 1–8):
                </span>
                <span className="text-cadmium-amber">
                  CLICK ROW TO INSPECT HEDDLE / TREADLE STATE
                </span>
              </div>

              {/* State Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-outline text-[11px] text-on-surface-variant uppercase">
                      <th className="py-2 px-3">Pick #</th>
                      <th className="py-2 px-3">Treadle</th>
                      <th className="py-2 px-3">Shed Aperture</th>
                      <th className="py-2 px-3">Sequence State</th>
                      <th className="py-2 px-3">Finding</th>
                    </tr>
                  </thead>
                  <tbody>
                    {picks.map((p) => (
                      <tr
                        key={p.pick}
                        onClick={() => setActivePick(p.pick)}
                        className={`border-b border-outline/30 cursor-pointer transition-colors ${
                          activePick === p.pick
                            ? p.status === 'DIVERGENT'
                              ? 'bg-divergence-crimson/20 text-on-surface'
                              : 'bg-transmission-emerald/15 text-on-surface'
                            : 'hover:bg-surface-bright text-on-surface-variant'
                        }`}
                      >
                        <td className="py-2.5 px-3 font-bold">
                          {p.pick === 7 && <span className="text-divergence-crimson mr-1">●</span>}
                          Pick 0{p.pick}
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[11px] ${
                              p.pick === 7
                                ? 'bg-divergence-crimson/30 text-divergence-crimson font-bold'
                                : 'bg-surface-elevated border border-outline text-on-surface'
                            }`}
                          >
                            {p.treadle}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">{p.shedHeight} mm</td>
                        <td className="py-2.5 px-3 font-semibold">
                          <span
                            className={
                              p.status === 'SATISFIED'
                                ? 'text-transmission-emerald'
                                : p.status === 'DIVERGENT'
                                ? 'text-divergence-crimson'
                                : 'text-cadmium-amber'
                            }
                          >
                            {p.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-[11px] text-on-surface-variant">
                          {p.note}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Physical Loom Diagram */}
              <div className="p-3.5 bg-surface-elevated rounded border border-outline/40 flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="text-[11px] font-mono uppercase text-on-surface-variant">
                    ACTIVE PICK #07 RECONSTRUCTION
                  </div>
                  <div className="text-sm font-semibold text-divergence-crimson flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4" />
                    Reed Struck on Stale Shed (Treadle Foot Switch Omitted)
                  </div>
                  <p className="text-xs text-on-surface-variant">
                    Weft thread was not bound by crossed warp yarns, creating an 8-thread horizontal float defect.
                  </p>
                </div>
                <div className="text-right font-mono">
                  <div className="text-[11px] text-on-surface-variant">SELVAGE DEFLECTION</div>
                  <div className="text-sm font-bold text-divergence-crimson">+5.8 mm (WAISTING)</div>
                </div>
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-outline/50 mt-4">
              <button
                onClick={onJumpFirstDivergence}
                className="px-4 py-2 rounded-lg bg-divergence-crimson/20 border border-divergence-crimson/40 text-divergence-crimson hover:bg-divergence-crimson/30 text-xs font-mono font-bold flex items-center gap-2 transition-colors"
              >
                <AlertTriangle className="w-4 h-4" />
                <span>INSPECT DIVERGENT PICK #7</span>
              </button>

              <button
                onClick={onLaunchRetry}
                className="px-5 py-2 rounded-lg bg-transmission-emerald hover:bg-transmission-emerald/90 text-background text-xs font-mono font-bold flex items-center gap-2 shadow-lg shadow-transmission-emerald/20 transition-all hover:scale-[1.02]"
              >
                <span>RETRY INTERLOCK CYCLE</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Rubric HUD (4 cols) */}
        <div className="xl:col-span-4 h-full">
          <RubricHUD
            telemetry={telemetry}
            currentTime={16.5}
            onTimeChange={() => {}}
            selectedCriterionId={selectedCriterionId}
            onSelectCriterion={setSelectedCriterionId}
          />
        </div>
      </div>

      {/* Bottom Transmission Gain Card */}
      <TransmissionGainHero
        telemetry={telemetry}
        onOpenLineage={onOpenLineage}
      />
    </div>
  );
}
