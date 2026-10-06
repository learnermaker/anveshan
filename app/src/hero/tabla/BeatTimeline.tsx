/**
 * Tabla beat timeline (SVG). Goal mode: source beats with bass / no-bass markers.
 * Alignment mode: learner strokes against goal beats with late / missing / extra / bass-mismatch.
 */

import React from 'react';
import type { TablaAlignmentRow, TablaUiView } from '../../api/types';

interface Props {
  ui: TablaUiView;
  alignment?: TablaAlignmentRow[];
  playhead?: number | null;
  /** seconds range to highlight */
  highlight?: [number, number] | null;
  /** goal beat index (0-based) to emphasise */
  focusBeat?: number | null;
  onSeek?: (sec: number) => void;
}

export function BeatTimeline({ ui, alignment, playhead, highlight, focusBeat, onSeek }: Props) {
  const beats = ui.beats;
  const end = ui.duration_sec ?? (beats.length ? beats[beats.length - 1].time_sec + 1 : 10);
  const W = 1000;
  const H = alignment ? 128 : 84;
  const x = (t: number) => (t / end) * W;
  const cycle = ui.cycle_length ?? 0;
  const goalY = 30;
  const learnY = 92;

  const handleClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!onSeek) return;
    const r = e.currentTarget.getBoundingClientRect();
    onSeek(((e.clientX - r.left) / r.width) * end);
  };

  return (
    <div className="space-y-1">
      <svg viewBox={`0 0 ${W} ${H}`} className={`w-full h-auto ${onSeek ? 'cursor-pointer' : ''}`} onClick={handleClick} role="img" aria-label="Beat timeline">
        <rect x={0} y={0} width={W} height={H} fill="#0f1214" />
        {highlight && <rect x={x(highlight[0])} y={0} width={Math.max(3, x(highlight[1]) - x(highlight[0]))} height={H} fill="#e67e2222" stroke="#e67e22" strokeDasharray="4 3" />}
        {cycle > 0 &&
          beats
            .filter((b) => b.index % cycle === 0)
            .map((b) => (
              <g key={`c${b.index}`}>
                <line x1={x(b.time_sec)} y1={0} x2={x(b.time_sec)} y2={H} stroke="#2e353b" strokeWidth={1.5} />
                <text x={x(b.time_sec) + 3} y={10} fontSize={9} fill="#9ba1a6" fontFamily="JetBrains Mono, monospace">
                  cycle {b.index / cycle + 1}
                </text>
              </g>
            ))}
        <text x={4} y={goalY + 26} fontSize={8} fill="#9ba1a6" fontFamily="JetBrains Mono, monospace">SOURCE</text>
        {beats.map((b) => {
          const fx = x(b.time_sec);
          const focused = focusBeat === b.index;
          return (
            <g key={b.index}>
              <line x1={fx} y1={goalY - (b.bass ? 14 : 7)} x2={fx} y2={goalY + 14} stroke={focused ? '#f87171' : '#edece8'} strokeWidth={focused ? 3 : 1.5} />
              {b.bass ? <circle cx={fx} cy={goalY + 18} r={4} fill="#e67e22" /> : <circle cx={fx} cy={goalY + 18} r={3.5} fill="none" stroke="#9ba1a6" />}
            </g>
          );
        })}
        {alignment && (
          <>
            <text x={4} y={learnY + 26} fontSize={8} fill="#9ba1a6" fontFamily="JetBrains Mono, monospace">LEARNER</text>
            {alignment.map((r, i) => {
              const t = r.learner_time_sec ?? r.goal_time_sec;
              if (t == null) return null;
              const lx = x(t);
              const bassMismatch = r.bass_expected != null && r.bass_played != null && r.bass_expected !== r.bass_played;
              const color = r.status === 'missing' ? '#f87171' : r.status === 'extra' ? '#f39c12' : r.status === 'late' || r.status === 'early' ? '#f87171' : bassMismatch ? '#f87171' : '#10b981';
              const focused = focusBeat != null && r.goal_index === focusBeat;
              return (
                <g key={`l${i}`}>
                  {r.goal_time_sec != null && r.learner_time_sec != null && (
                    <line x1={x(r.goal_time_sec)} y1={goalY + 22} x2={lx} y2={learnY - 14} stroke={color} strokeWidth={0.8} opacity={0.5} />
                  )}
                  {r.status === 'missing' ? (
                    <text x={lx} y={learnY + 4} fontSize={12} textAnchor="middle" fill={color} fontFamily="JetBrains Mono, monospace">×</text>
                  ) : (
                    <line x1={lx} y1={learnY - (r.bass_played ? 14 : 7)} x2={lx} y2={learnY + 12} stroke={color} strokeWidth={focused ? 3.5 : 1.8} />
                  )}
                  {r.bass_played && <circle cx={lx} cy={learnY + 17} r={4} fill={bassMismatch ? '#f87171' : '#e67e22'} />}
                  {r.bass_played === false && r.status !== 'missing' && <circle cx={lx} cy={learnY + 17} r={3.5} fill="none" stroke={bassMismatch ? '#f87171' : '#9ba1a6'} />}
                  {focused && <rect x={lx - 9} y={learnY - 20} width={18} height={44} fill="none" stroke="#f87171" strokeWidth={1.5} />}
                </g>
              );
            })}
          </>
        )}
        {playhead != null && <line x1={x(playhead)} y1={0} x2={x(playhead)} y2={H} stroke="#00e5ff" strokeWidth={1.5} />}
      </svg>
      <div className="flex flex-wrap gap-3 text-[9px] font-mono text-on-surface-variant">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cadmium-amber" /> bass (bayan)</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full border border-on-surface-variant" /> no bass</span>
        {alignment && (
          <>
            <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-transmission-emerald" /> on grid</span>
            <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-divergence-crimson" /> late / missing / bass mismatch</span>
            <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-[#f39c12]" /> extra</span>
          </>
        )}
      </div>
    </div>
  );
}
