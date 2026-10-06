/**
 * Kolam drawing canvas. The canvas has the goal image's pixel size (ui_view.canvas) and is scaled
 * with CSS, so recorded points are already in goal pixels: [x, y, t_ms] (t from the first touch).
 * Trace JSON follows docs/plans/service-api.md §4.
 */

import React, { useEffect, useRef } from 'react';
import type { KolamUiView } from '../../api/types';

export type Stroke = number[][]; // [[x, y, t_ms], ...]

interface Props {
  ui: KolamUiView;
  strokes: Stroke[];
  onStrokesChange: (s: Stroke[]) => void;
  startRef: React.MutableRefObject<number | null>;
  disabled?: boolean;
  showGuide?: boolean;
}

function drawScene(ctx: CanvasRenderingContext2D, ui: KolamUiView, strokes: Stroke[], opts: { guide?: boolean; background?: string; dotsStyle?: 'ui' | 'raster' }) {
  const { width: W, height: H } = ui.canvas;
  ctx.fillStyle = opts.background ?? '#050607';
  ctx.fillRect(0, 0, W, H);
  if (opts.guide) {
    ctx.strokeStyle = 'rgba(155,161,166,0.18)';
    ctx.lineWidth = 2;
    for (const c of ui.curves) {
      ctx.beginPath();
      c.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
      ctx.stroke();
    }
  }
  for (const d of ui.dots) {
    ctx.beginPath();
    ctx.arc(d.x, d.y, Math.max(3, d.r ?? 3), 0, Math.PI * 2);
    ctx.fillStyle = opts.dotsStyle === 'raster' ? '#ffffff' : '#9ba1a6';
    ctx.fill();
  }
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = Math.max(2, ui.stroke_width ?? 3);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  for (const s of strokes) {
    if (!s.length) continue;
    ctx.beginPath();
    s.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
    if (s.length === 1) ctx.lineTo(s[0][0] + 0.1, s[0][1]);
    ctx.stroke();
  }
}

export function KolamCanvas({ ui, strokes, onStrokesChange, startRef, disabled, showGuide }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  const current = useRef<Stroke | null>(null);
  const strokesRef = useRef(strokes);
  strokesRef.current = strokes;

  const redraw = () => {
    const ctx = ref.current?.getContext('2d');
    if (!ctx) return;
    drawScene(ctx, ui, current.current ? [...strokesRef.current, current.current] : strokesRef.current, { guide: showGuide });
  };

  useEffect(redraw, [strokes, ui, showGuide]);

  const toGoal = (e: React.PointerEvent<HTMLCanvasElement>): number[] => {
    const r = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * ui.canvas.width;
    const y = ((e.clientY - r.top) / r.height) * ui.canvas.height;
    if (startRef.current == null) startRef.current = performance.now();
    return [Math.round(x * 10) / 10, Math.round(y * 10) / 10, Math.round(performance.now() - startRef.current)];
  };

  return (
    <canvas
      ref={ref}
      width={ui.canvas.width}
      height={ui.canvas.height}
      className={`w-full h-auto rounded-lg border border-outline touch-none ${disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-crosshair'}`}
      style={{ aspectRatio: `${ui.canvas.width} / ${ui.canvas.height}` }}
      onPointerDown={(e) => {
        if (disabled) return;
        e.currentTarget.setPointerCapture(e.pointerId);
        current.current = [toGoal(e)];
        redraw();
      }}
      onPointerMove={(e) => {
        if (!current.current) return;
        const p = toGoal(e);
        const last = current.current[current.current.length - 1];
        if (Math.hypot(p[0] - last[0], p[1] - last[1]) < 1.5) return;
        current.current.push(p);
        redraw();
      }}
      onPointerUp={() => {
        if (!current.current) return;
        const s = current.current;
        current.current = null;
        onStrokesChange([...strokesRef.current, s]);
      }}
      onPointerCancel={() => {
        current.current = null;
        redraw();
      }}
      aria-label="Kolam drawing canvas"
    />
  );
}

export function buildTraceJson(ui: KolamUiView, caseId: string, goalVersion: number, strokes: Stroke[], startedAt: number | null): string {
  const last = strokes.flat().reduce((m, p) => Math.max(m, p[2] ?? 0), 0);
  return JSON.stringify({
    canvas: { width: ui.canvas.width, height: ui.canvas.height },
    goal_case_id: caseId,
    goal_version: goalVersion,
    strokes: strokes.map((s) => ({ points: s })),
    duration_ms: startedAt == null ? 0 : last,
  });
}

export function buildRasterPng(ui: KolamUiView, strokes: Stroke[]): Promise<Blob> {
  const c = document.createElement('canvas');
  c.width = ui.canvas.width;
  c.height = ui.canvas.height;
  const ctx = c.getContext('2d');
  if (!ctx) return Promise.reject(new Error('canvas 2d unavailable'));
  drawScene(ctx, ui, strokes, { background: '#000000', dotsStyle: 'raster' });
  return new Promise((resolve, reject) => c.toBlob((b) => (b ? resolve(b) : reject(new Error('PNG encode failed'))), 'image/png'));
}
