/**
 * Progress-to-goal curve (evaluation-core §2): coverage(t) with divergence markers.
 * Pure SVG, no chart dependency. Supports overlaying several series (baseline vs retry).
 */

import React, { useState } from 'react';
import type { DivergenceEvent } from '../../api/types';
import { fmtPosition } from '../locators';

export interface CurveSeries {
  id: string;
  label: string;
  points: number[][];
  color: string;
  dashed?: boolean;
  events?: DivergenceEvent[];
}

interface Props {
  series: CurveSeries[];
  kind: string;
  /** position of the first divergence on the first series */
  firstDivergence?: number | null;
  height?: number;
  onSelectEvent?: (e: DivergenceEvent) => void;
}

const kindLabel = (k: string) => (k === 'time' ? 'time (s)' : k === 'stroke' ? 'strokes drawn' : k === 'beat' ? 'goal beats' : k === 'frame' ? 'frame' : k);

export function ProgressCurve({ series, kind, firstDivergence, height = 220, onSelectEvent }: Props) {
  const [hover, setHover] = useState<{ x: number; label: string } | null>(null);
  const W = 640;
  const H = height;
  const m = { l: 40, r: 14, t: 14, b: 30 };
  const all = series.flatMap((s) => s.points);
  const xMax = Math.max(1, ...all.map((p) => p[0]), ...series.flatMap((s) => (s.events ?? []).map((e) => e.position)));
  const xMin = Math.min(0, ...all.map((p) => p[0]));
  const sx = (x: number) => m.l + ((x - xMin) / (xMax - xMin || 1)) * (W - m.l - m.r);
  const sy = (y: number) => m.t + (1 - Math.max(0, Math.min(1, y))) * (H - m.t - m.b);
  const path = (pts: number[][]) => pts.map((p, i) => `${i ? 'L' : 'M'}${sx(p[0]).toFixed(1)} ${sy(p[1]).toFixed(1)}`).join(' ');
  const xticks = Array.from({ length: 6 }, (_, i) => xMin + ((xMax - xMin) * i) / 5);

  if (!all.length) {
    return <div className="text-[11px] font-mono text-on-surface-variant p-4 border border-outline rounded-lg">No progress points to show for this try.</div>;
  }

  return (
    <div className="space-y-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Progress toward the goal">
        <rect x={0} y={0} width={W} height={H} fill="#0b0d0e" rx={6} />
        {[0, 0.25, 0.5, 0.75, 1].map((y) => (
          <g key={y}>
            <line x1={m.l} x2={W - m.r} y1={sy(y)} y2={sy(y)} stroke="#1a1e22" strokeWidth={1} />
            <text x={m.l - 6} y={sy(y) + 3} fontSize={9} textAnchor="end" fill="#9ba1a6" fontFamily="JetBrains Mono, monospace">
              {Math.round(y * 100)}%
            </text>
          </g>
        ))}
        {xticks.map((x, i) => (
          <text key={i} x={sx(x)} y={H - m.b + 14} fontSize={9} textAnchor="middle" fill="#9ba1a6" fontFamily="JetBrains Mono, monospace">
            {kind === 'time' ? Math.round(x) : Math.round(x * 10) / 10}
          </text>
        ))}
        <text x={W - m.r} y={H - 4} fontSize={9} textAnchor="end" fill="#9ba1a6" fontFamily="JetBrains Mono, monospace">
          {kindLabel(kind)} →
        </text>
        <line x1={m.l} x2={W - m.r} y1={sy(1)} y2={sy(1)} stroke="#10b981" strokeWidth={1} strokeDasharray="3 3" opacity={0.6} />
        <text x={W - m.r - 2} y={sy(1) - 3} fontSize={8} textAnchor="end" fill="#10b981" fontFamily="JetBrains Mono, monospace">GOAL</text>

        {firstDivergence != null && (
          <g>
            <line x1={sx(firstDivergence)} x2={sx(firstDivergence)} y1={m.t} y2={H - m.b} stroke="#f87171" strokeWidth={2} />
            <text
              x={sx(firstDivergence) > W * 0.7 ? sx(firstDivergence) - 4 : sx(firstDivergence) + 4}
              textAnchor={sx(firstDivergence) > W * 0.7 ? 'end' : 'start'}
              y={m.t + 9}
              fontSize={9}
              fill="#f87171"
              fontFamily="JetBrains Mono, monospace"
              fontWeight={700}
            >
              WENT OFF TRACK
            </text>
          </g>
        )}

        {/* later series drawn first so the first (e.g. dashed baseline) stays visible on top */}
        {[...series].reverse().map((s) => (
          <g key={s.id}>
            <path d={path(s.points)} fill="none" stroke={s.color} strokeWidth={2.2} strokeDasharray={s.dashed ? '5 4' : undefined} strokeLinejoin="round" />
            {(s.events ?? []).map((e, i) => {
              const ex = sx(e.position);
              const y = H - m.b;
              const color = e.severity === 'material' ? '#f87171' : '#f39c12';
              return (
                <g
                  key={i}
                  className={onSelectEvent ? 'cursor-pointer' : ''}
                  onClick={() => onSelectEvent?.(e)}
                  onMouseEnter={() => setHover({ x: ex, label: `${e.kind} · ${fmtPosition(e.position, e.position_kind)} — ${e.detail}` })}
                  onMouseLeave={() => setHover(null)}
                >
                  <line x1={ex} x2={ex} y1={m.t + 14} y2={y} stroke={color} strokeWidth={1} strokeDasharray="2 3" opacity={0.7} />
                  <path d={`M${ex} ${y - 2} l5 -8 l-10 0 z`} fill={color} />
                  <rect x={ex - 7} y={m.t} width={14} height={H - m.t - m.b} fill="transparent" />
                </g>
              );
            })}
          </g>
        ))}
        {hover && (
          <g pointerEvents="none">
            <rect x={Math.min(hover.x + 6, W - 330)} y={H - m.b - 42} width={320} height={20} rx={3} fill="#1c2124" stroke="#2e353b" />
            <text x={Math.min(hover.x + 12, W - 324)} y={H - m.b - 28} fontSize={9} fill="#edece8" fontFamily="JetBrains Mono, monospace">
              {hover.label.length > 58 ? `${hover.label.slice(0, 57)}…` : hover.label}
            </text>
          </g>
        )}
      </svg>
      <div className="flex flex-wrap gap-3 text-[10px] font-mono text-on-surface-variant">
        {series.map((s) => (
          <span key={s.id} className="flex items-center gap-1.5">
            <svg width="18" height="6">
              <line x1="0" y1="3" x2="18" y2="3" stroke={s.color} strokeWidth="2.2" strokeDasharray={s.dashed ? '4 3' : undefined} />
            </svg>
            {s.label}
          </span>
        ))}
        <span className="flex items-center gap-1"><span className="text-divergence-crimson">▼</span> went off track</span>
        <span className="flex items-center gap-1"><span className="text-[#f39c12]">▼</span> minor</span>
      </div>
    </div>
  );
}
