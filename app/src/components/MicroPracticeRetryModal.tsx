import React, { useState } from 'react';
import { CheckCircle2, RotateCcw, Sparkles, TrendingUp, X, ArrowRight, ShieldCheck } from 'lucide-react';
import type { CapabilityCase } from '../types/workspace';

interface MicroPracticeRetryModalProps {
  capCase: CapabilityCase;
  isOpen: boolean;
  onClose: () => void;
  onCompleteRetry: () => void;
}

export function MicroPracticeRetryModal({
  capCase,
  isOpen,
  onClose,
  onCompleteRetry,
}: MicroPracticeRetryModalProps) {
  if (!isOpen) return null;

  const challenge = capCase.microPractice;
  const [interactiveState, setInteractiveState] = useState<number>(0);
  const [isCompleted, setIsCompleted] = useState<boolean>(false);


  // Reset state when challenge opens
  const handleReset = () => {
    setInteractiveState(0);
    setIsCompleted(false);
  };

  const renderInteractiveChallenge = () => {
    switch (challenge.interactionType) {
      case 'slider_torque':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-on-surface-variant">RATCHET TORQUE CLUTCH SPEEDER:</span>
              <span className="text-cadmium-amber font-bold">
                {interactiveState === 0 ? 'DISENGAGED (0 CLICKS)' : `${interactiveState} CLICKS (${(interactiveState * 1.67).toFixed(1)} N)`}
              </span>
            </div>
            <div className="flex items-center gap-3">
              {[1, 2, 3, 4, 5].map((clickNum) => (
                <button
                  key={clickNum}
                  onClick={() => {
                    setInteractiveState(clickNum);
                    if (clickNum === 3) {
                      setIsCompleted(true);

                    } else {
                      setIsCompleted(false);
                    }
                  }}
                  className={`flex-1 py-3 px-2 rounded-lg border font-mono text-xs text-center transition-all ${
                    interactiveState === clickNum
                      ? clickNum === 3
                        ? 'bg-transmission-emerald/20 border-transmission-emerald text-transmission-emerald font-bold'
                        : 'bg-divergence-crimson/20 border-divergence-crimson text-divergence-crimson'
                      : 'bg-surface-dim border-outline hover:border-outline-variant text-on-surface-variant'
                  }`}
                >
                  Click #{clickNum}
                  {clickNum === 3 && <div className="text-[9px] uppercase mt-0.5 text-transmission-emerald">TARGET (5.0 N)</div>}
                  {clickNum > 3 && <div className="text-[9px] uppercase mt-0.5 text-divergence-crimson">OVER-TORQUE</div>}
                </button>
              ))}
            </div>
            {interactiveState === 3 && (
              <p className="text-xs text-transmission-emerald font-mono bg-transmission-emerald/10 p-2.5 rounded border border-transmission-emerald/30">
                MATCHES THE SOURCE CUE: Exactly 3 clicks reached in the replay simulation. Physical torque is not measured by this fixture.
              </p>
            )}
            {interactiveState > 3 && (
              <p className="text-xs text-divergence-crimson font-mono bg-divergence-crimson/10 p-2.5 rounded border border-divergence-crimson/30">
                DIFFERS FROM THE CUE: {interactiveState} clicks exceeds 5.0 N limit. Spindle anvil deflected.
              </p>
            )}
          </div>
        );

      case 'canvas_loop':
        return (
          <div className="space-y-4">
            <div className="text-xs font-mono text-on-surface-variant">
              SELECT LOOP TRAJECTORY AROUND DOT (3, 4):
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => {
                  setInteractiveState(1);
                  setIsCompleted(false);
                }}
                className={`p-3 rounded-lg border text-left text-xs font-mono transition-all ${
                  interactiveState === 1
                    ? 'border-divergence-crimson bg-divergence-crimson/15 text-divergence-crimson'
                    : 'border-outline bg-surface-dim hover:border-outline-variant text-on-surface'
                }`}
              >
                <div className="font-bold">Option A: Acute Diagonal Squeeze</div>
                <div className="text-[11px] text-on-surface-variant mt-1">Crosses dot coordinate directly (Baseline error)</div>
              </button>

              <button
                onClick={() => {
                  setInteractiveState(2);
                  setIsCompleted(true);

                }}
                className={`p-3 rounded-lg border text-left text-xs font-mono transition-all ${
                  interactiveState === 2
                    ? 'border-transmission-emerald bg-transmission-emerald/15 text-transmission-emerald'
                    : 'border-outline bg-surface-dim hover:border-outline-variant text-on-surface'
                }`}
              >
                <div className="font-bold">Option B: Continuous Orbital Convex Arc</div>
                <div className="text-[11px] text-on-surface-variant mt-1">8mm clearance around dot (Target loop)</div>
              </button>
            </div>
            {interactiveState === 2 && (
              <p className="text-xs text-transmission-emerald font-mono bg-transmission-emerald/10 p-2.5 rounded border border-transmission-emerald/30">
                MATCHES THE SOURCE CUE: 8mm clearance maintained. Closed single-stroke topology and 4-fold rotational symmetry preserved.
              </p>
            )}
          </div>
        );

      case 'diagnosis_tree':
        return (
          <div className="space-y-4">
            <div className="text-xs font-mono text-on-surface-variant">
              SURFACE PREPARATION ABRASION LEVEL:
            </div>
            <div className="flex items-center gap-3">
              {[
                { label: 'Unbuffed (Glazed)', valid: false },
                { label: 'Light Buff (10mm)', valid: false },
                { label: 'Matte Cross-Hatch (30mm)', valid: true },
              ].map((lvl, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setInteractiveState(idx + 1);
                    if (lvl.valid) {
                      setIsCompleted(true);

                    } else {
                      setIsCompleted(false);
                    }
                  }}
                  className={`flex-1 p-3 rounded-lg border text-xs font-mono text-center transition-all ${
                    interactiveState === idx + 1
                      ? lvl.valid
                        ? 'border-transmission-emerald bg-transmission-emerald/15 text-transmission-emerald font-bold'
                        : 'border-cadmium-amber bg-cadmium-amber/15 text-cadmium-amber'
                      : 'border-outline bg-surface-dim hover:border-outline-variant text-on-surface-variant'
                  }`}
                >
                  {lvl.label}
                </button>
              ))}
            </div>
            {interactiveState === 3 && (
              <p className="text-xs text-transmission-emerald font-mono bg-transmission-emerald/10 p-2.5 rounded border border-transmission-emerald/30">
                MATCHES THE SOURCE CUE: 30mm matte zone creates polymer bond with vulcanizing solvent. Zero factory glaze remains.
              </p>
            )}
          </div>
        );

      case 'shuttle_pass':
        return (
          <div className="space-y-4">
            <div className="text-xs font-mono text-on-surface-variant">
              SELECT LOOM MECHANICAL SEQUENCE:
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => {
                  setInteractiveState(1);
                  setIsCompleted(false);
                }}
                className={`p-3 rounded-lg border text-left text-xs font-mono transition-all ${
                  interactiveState === 1
                    ? 'border-divergence-crimson bg-divergence-crimson/15 text-divergence-crimson'
                    : 'border-outline bg-surface-dim text-on-surface'
                }`}
              >
                <div className="font-bold">Sequence A: Throw → Beat → Switch Foot</div>
                <div className="text-[11px] text-on-surface-variant mt-1">Strikes reed on open shed (Float defect)</div>
              </button>

              <button
                onClick={() => {
                  setInteractiveState(2);
                  setIsCompleted(true);

                }}
                className={`p-3 rounded-lg border text-left text-xs font-mono transition-all ${
                  interactiveState === 2
                    ? 'border-transmission-emerald bg-transmission-emerald/15 text-transmission-emerald'
                    : 'border-outline bg-surface-dim text-on-surface'
                }`}
              >
                <div className="font-bold">Sequence B: Throw → Switch Foot → Beat</div>
                <div className="text-[11px] text-on-surface-variant mt-1">Crosses treadle to lock weft before reed strike</div>
              </button>
            </div>
            {interactiveState === 2 && (
              <p className="text-xs text-transmission-emerald font-mono bg-transmission-emerald/10 p-2.5 rounded border border-transmission-emerald/30">
                MATCHES THE SOURCE CUE: Foot treadle switch binds weft pick in crossed warp shed before beater impact.
              </p>
            )}
          </div>
        );

      case 'rhythm_tap':
        return (
          <div className="space-y-4">
            <div className="text-xs font-mono text-on-surface-variant">
              BIMANUAL "DHA" TIMING OFFSET:
            </div>
            <div className="flex items-center gap-3">
              {[
                { label: 'Dayan Leads (-48ms)', valid: false },
                { label: 'Synchronized (+6ms Delta T)', valid: true },
                { label: 'Bayan Leads (+35ms)', valid: false },
              ].map((timing, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setInteractiveState(idx + 1);
                    if (timing.valid) {
                      setIsCompleted(true);

                    } else {
                      setIsCompleted(false);
                    }
                  }}
                  className={`flex-1 p-3 rounded-lg border text-xs font-mono text-center transition-all ${
                    interactiveState === idx + 1
                      ? timing.valid
                        ? 'border-transmission-emerald bg-transmission-emerald/15 text-transmission-emerald font-bold'
                        : 'border-divergence-crimson bg-divergence-crimson/15 text-divergence-crimson'
                      : 'border-outline bg-surface-dim text-on-surface-variant'
                  }`}
                >
                  {timing.label}
                </button>
              ))}
            </div>
            {interactiveState === 2 && (
              <p className="text-xs text-transmission-emerald font-mono bg-transmission-emerald/10 p-2.5 rounded border border-transmission-emerald/30">
                MATCHES THE SOURCE CUE: Delta T = 6ms (within 15ms window). Resonant composite Dha timbre confirmed on acoustic envelope.
              </p>
            )}
          </div>
        );

      case 'fold_angle':
        return (
          <div className="space-y-4">
            <div className="text-xs font-mono text-on-surface-variant">
              LATERAL CREASE INVERSION POLARITY:
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => {
                  setInteractiveState(1);
                  setIsCompleted(false);
                }}
                className={`p-3 rounded-lg border text-left text-xs font-mono transition-all ${
                  interactiveState === 1
                    ? 'border-divergence-crimson bg-divergence-crimson/15 text-divergence-crimson'
                    : 'border-outline bg-surface-dim text-on-surface'
                }`}
              >
                <div className="font-bold">Retain Mountain Fold (+180°)</div>
                <div className="text-[11px] text-on-surface-variant mt-1">Crushes paper along spine (Baseline error)</div>
              </button>

              <button
                onClick={() => {
                  setInteractiveState(2);
                  setIsCompleted(true);

                }}
                className={`p-3 rounded-lg border text-left text-xs font-mono transition-all ${
                  interactiveState === 2
                    ? 'border-transmission-emerald bg-transmission-emerald/15 text-transmission-emerald'
                    : 'border-outline bg-surface-dim text-on-surface'
                }`}
              >
                <div className="font-bold">Invert to Valley Fold (-180°)</div>
                <div className="text-[11px] text-on-surface-variant mt-1">Pops concave fold inward into flat bird base</div>
              </button>
            </div>
            {interactiveState === 2 && (
              <p className="text-xs text-transmission-emerald font-mono bg-transmission-emerald/10 p-2.5 rounded border border-transmission-emerald/30">
                MATCHES THE SOURCE CUE: Paper collapsed cleanly into diamond bird base without fiber crushing.
              </p>
            )}
          </div>
        );

      default: // knot_cross
        return (
          <div className="space-y-4">
            <div className="text-xs font-mono text-on-surface-variant">
              THROW #2 CHIRALITY SELECTION:
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => {
                  setInteractiveState(1);
                  setIsCompleted(false);
                }}
                className={`p-3 rounded-lg border text-left text-xs font-mono transition-all ${
                  interactiveState === 1
                    ? 'border-divergence-crimson bg-divergence-crimson/15 text-divergence-crimson'
                    : 'border-outline bg-surface-dim text-on-surface'
                }`}
              >
                <div className="font-bold">Throw Right-Over-Left Again</div>
                <div className="text-[11px] text-on-surface-variant mt-1">Creates Granny Knot (Capsizes at 12N)</div>
              </button>

              <button
                onClick={() => {
                  setInteractiveState(2);
                  setIsCompleted(true);

                }}
                className={`p-3 rounded-lg border text-left text-xs font-mono transition-all ${
                  interactiveState === 2
                    ? 'border-transmission-emerald bg-transmission-emerald/15 text-transmission-emerald'
                    : 'border-outline bg-surface-dim text-on-surface'
                }`}
              >
                <div className="font-bold">Reverse to Left-Over-Right</div>
                <div className="text-[11px] text-on-surface-variant mt-1">Creates True Square Knot (Locks under load)</div>
              </button>
            </div>
            {interactiveState === 2 && (
              <p className="text-xs text-transmission-emerald font-mono bg-transmission-emerald/10 p-2.5 rounded border border-transmission-emerald/30">
                MATCHES THE SOURCE CUE: Square-knot topology achieved in the replay simulation. Tensile force is not measured by this fixture.
              </p>
            )}
          </div>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md animate-fade-in">
      <div className="bg-surface-elevated border border-transmission-emerald/50 rounded-xl shadow-2xl max-w-xl w-full overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 bg-transmission-emerald/10 border-b border-transmission-emerald/30 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-transmission-emerald/20 flex items-center justify-center text-transmission-emerald">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] font-mono uppercase tracking-widest text-transmission-emerald font-bold">
                UNSCORED MICRO-DRILL // GUIDANCE ONLY
              </div>
              <h2 className="text-base font-semibold text-on-surface">
                {challenge.title}
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-bright transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Challenge Instructions */}
        <div className="p-6 space-y-5">
          <div className="p-3.5 bg-surface-dim rounded-lg border border-outline/40">
            <div className="text-[10px] font-mono uppercase text-on-surface-variant font-semibold">
              TASK INSTRUCTION
            </div>
            <p className="text-xs text-on-surface mt-1 leading-relaxed">
              {challenge.instructions}
            </p>
            <div className="text-[11px] font-mono text-cadmium-amber mt-2">
              CORRECTIVE CUE: {challenge.correctiveCue}
            </div>
          </div>

          {/* Interactive Challenge Primitive */}
          <div className="p-4 bg-surface-dim/60 rounded-xl border border-outline/30">
            {renderInteractiveChallenge()}
          </div>

          {/* The drill is guidance only: it awards nothing and changes no score. */}
          <div className="p-3 bg-surface-dim rounded-lg border border-outline/40 flex items-center gap-2 text-[11px] font-mono text-on-surface-variant">
            <ShieldCheck className="w-4 h-4 text-caliper-cyan shrink-0" />
            <span>UNSCORED. This drill changes no rubric score. Only the full retry (shown next, as a replay fixture) is evaluated.</span>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-surface-dim border-t border-outline flex items-center justify-between gap-4">
          <button
            onClick={handleReset}
            className="px-3 py-1.5 text-xs font-mono text-on-surface-variant hover:text-on-surface flex items-center gap-1.5 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>RESET CHALLENGE</span>
          </button>

          <button
            onClick={() => {
              onClose();
              onCompleteRetry();
            }}
            className="px-5 py-2.5 rounded-lg font-mono font-bold text-xs uppercase tracking-wider flex items-center gap-2 transition-all bg-cadmium-amber text-background hover:bg-cadmium-amber/90"
          >
            <span>CONTINUE TO RETRY REPLAY</span>
            <TrendingUp className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
