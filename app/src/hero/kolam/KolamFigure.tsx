/**
 * Kolam goal figure: target image + SVG overlays in goal-image pixel coordinates.
 * Curves are the INFERRED suggested decomposition; dots/symmetry are computed (OBSERVED).
 */

import React from 'react';
import type { KolamCurveObj, KolamUiView } from '../../api/types';

export interface KolamFigureProps {
  ui: KolamUiView;
  imageUrl?: string;
  showImage?: boolean;
  showDots?: boolean;
  showCurves?: boolean;
  animateCurves?: boolean;
  showSymmetry?: boolean;
  /** percent region to highlight (from #xywh=percent:) */
  region?: { x: number; y: number; w: number; h: number } | null;
  regionTone?: 'amber' | 'crimson' | 'cyan';
  /** learner strokes in goal pixels */
  strokes?: number[][][];
  highlightStrokes?: number[];
  className?: string;
}

const pathOf = (pts: number[][]) => pts.map((p, i) => `${i ? 'L' : 'M'}${p[0]} ${p[1]}`).join(' ');

const CURVE_COLORS = ['#e67e22', '#00e5ff', '#10b981', '#f8b878', '#80f2ff', '#6ee7b7', '#f39c12', '#9ba1a6'];

export function KolamFigure({
  ui,
  imageUrl,
  showImage = true,
  showDots = false,
  showCurves = false,
  animateCurves = false,
  showSymmetry = false,
  region,
  regionTone = 'amber',
  strokes,
  highlightStrokes = [],
  className = '',
}: KolamFigureProps) {
  const { width: W, height: H } = ui.canvas;
  const sym = ui.symmetry;
  const center = sym?.center ?? [W / 2, H / 2];
  // Real service: rotation_order at top level; legacy mock: symmetry.rotational_order
  const order = ui.rotation_order ?? sym?.rotational_order ?? 0;
  const regionColor = regionTone === 'crimson' ? '#f87171' : regionTone === 'cyan' ? '#00e5ff' : '#e67e22';

  return (
    <div className={`relative bg-black rounded-lg overflow-hidden border border-outline ${className}`} style={{ aspectRatio: `${W} / ${H}` }}>
      {showImage && imageUrl && <img src={imageUrl} alt="Kolam target" className="absolute inset-0 w-full h-full object-fill" draggable={false} />}
      {showImage && !imageUrl && (
        <div className="absolute inset-0 flex items-center justify-center text-[11px] font-mono text-on-surface-variant">target image unavailable</div>
      )}
      <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
        <style>{`@keyframes kolamDraw { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }`}</style>
        {showSymmetry && order > 1 &&
          Array.from({ length: order }, (_, i) => {
            const a = (i / order) * Math.PI * 2 - Math.PI / 2;
            const r = Math.max(W, H);
            return <line key={i} x1={center[0]} y1={center[1]} x2={center[0] + r * Math.cos(a)} y2={center[1] + r * Math.sin(a)} stroke="#00e5ff" strokeWidth={0.8} strokeDasharray="4 4" opacity={0.6} />;
          })}
        {showSymmetry && sym?.mirror_axes?.map((deg, i) => {
          const a = (deg * Math.PI) / 180;
          const r = Math.max(W, H);
          return <line key={`m${i}`} x1={center[0] - r * Math.cos(a)} y1={center[1] - r * Math.sin(a)} x2={center[0] + r * Math.cos(a)} y2={center[1] + r * Math.sin(a)} stroke="#10b981" strokeWidth={1} opacity={0.7} />;
        })}
        {showCurves &&
          ui.curves.map((c, k) => {
            // Support both real-service KolamCurveObj (with .points) and legacy number[][] arrays
            const pts = (c as KolamCurveObj).points ?? (c as unknown as number[][]);
            return (
              <path
                key={k}
                d={pathOf(pts)}
                fill="none"
                stroke={CURVE_COLORS[k % CURVE_COLORS.length]}
                strokeWidth={2.5}
                strokeLinejoin="round"
                pathLength={1}
                strokeDasharray={animateCurves ? 1 : undefined}
                style={animateCurves ? { animation: `kolamDraw 2.4s ease-in-out ${k * 0.9}s both` } : undefined}
                opacity={0.9}
              />
            );
          })}
        {strokes?.map((s, k) => (
          <path
            key={`s${k}`}
            d={pathOf(s)}
            fill="none"
            stroke={highlightStrokes.includes(k) ? '#f87171' : '#edece8'}
            strokeWidth={highlightStrokes.includes(k) ? 4 : 2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}
        {showDots &&
          ui.dots.map((d, i) => (
            <circle key={i} cx={d.x} cy={d.y} r={Math.max(4, (d.r ?? 3) + 2)} fill={d.relation === 'on_line' ? '#e67e22' : '#00e5ff'} stroke="#08090a" strokeWidth={1} />
          ))}
        {region && (
          <rect
            x={(region.x / 100) * W}
            y={(region.y / 100) * H}
            width={(region.w / 100) * W}
            height={(region.h / 100) * H}
            fill={`${regionColor}22`}
            stroke={regionColor}
            strokeWidth={2}
            strokeDasharray="6 3"
          />
        )}
      </svg>
    </div>
  );
}
