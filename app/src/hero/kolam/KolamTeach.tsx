/**
 * "Show me" teaching for a kolam: replays the goal line stage by stage on the dot grid.
 * Geometry comes from the goal model (ui_view.curves[].points / stages), so nothing here is
 * model-generated. The stage order is one suggested way (INFERRED), not the original drawing order.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Pause, Play, RotateCcw } from 'lucide-react';
import type { KolamCurveObj, KolamUiView } from '../../api/types';
import { btn } from '../ui';

interface Stage {
  label: string;
  points: number[][];
}

function stagesOf(ui: KolamUiView): Stage[] {
  const out: Stage[] = [];
  (ui.curves as KolamCurveObj[]).forEach((c, ci) => {
    if (!c || !Array.isArray(c.points)) return;
    // Stage bounds are arc lengths along the curve (goal pixels), not point indices.
    const cum: number[] = [0];
    for (let i = 1; i < c.points.length; i++) {
      cum.push(cum[i - 1] + Math.hypot(c.points[i][0] - c.points[i - 1][0], c.points[i][1] - c.points[i - 1][1]));
    }
    const total = cum[cum.length - 1];
    const stages = c.stages?.length ? c.stages : [{ id: `${c.id ?? `C${ci + 1}`}.S1`, start: 0, end: total }];
    stages.forEach((s, si) => {
      const pts = c.points.filter((_, i) => cum[i] >= s.start - 1e-6 && cum[i] <= s.end + 1e-6);
      if (pts.length > 1) out.push({ label: `${(ui.curves as KolamCurveObj[]).length > 1 ? `Line ${ci + 1}, ` : ''}stage ${si + 1}`, points: pts });
    });
  });
  return out;
}

const STAGE_MS = 1800;

export function KolamTeach({ ui }: { ui: KolamUiView }) {
  const stages = useMemo(() => stagesOf(ui), [ui]);
  const ref = useRef<HTMLCanvasElement>(null);
  // progress = stages completed + fraction of the current stage, in [0, stages.length]
  const [progress, setProgress] = useState(0);
  const [playing, setPlaying] = useState(false);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    if (!playing) return;
    let last: number | null = null;
    const step = (now: number) => {
      if (last !== null) {
        setProgress((p) => {
          const next = p + (now - last!) / STAGE_MS;
          if (next >= stages.length) {
            setPlaying(false);
            return stages.length;
          }
          return next;
        });
      }
      last = now;
      raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [playing, stages.length]);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    const { width: W, height: H } = ui.canvas;
    ctx.fillStyle = '#050607';
    ctx.fillRect(0, 0, W, H);
    const lw = Math.max(2, ui.stroke_width ?? 3);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    // faint full target for orientation
    ctx.strokeStyle = 'rgba(155,161,166,0.16)';
    ctx.lineWidth = lw;
    for (const s of stages) {
      ctx.beginPath();
      s.points.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
      ctx.stroke();
    }
    for (const d of ui.dots) {
      ctx.beginPath();
      ctx.arc(d.x, d.y, Math.max(3, d.r ?? 3), 0, Math.PI * 2);
      ctx.fillStyle = '#9ba1a6';
      ctx.fill();
    }
    const full = Math.floor(progress);
    stages.forEach((s, i) => {
      if (i > full) return;
      const frac = i < full ? 1 : progress - full;
      const n = Math.max(2, Math.round(s.points.length * frac));
      if (frac <= 0) return;
      ctx.strokeStyle = i < full ? '#edece8' : '#f39c12';
      ctx.lineWidth = i < full ? lw : lw + 1.5;
      ctx.beginPath();
      s.points.slice(0, n).forEach((p, k) => (k ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
      ctx.stroke();
      if (i === full) {
        const head = s.points[Math.min(n, s.points.length) - 1];
        ctx.beginPath();
        ctx.arc(head[0], head[1], lw + 4, 0, Math.PI * 2);
        ctx.fillStyle = '#f39c12';
        ctx.fill();
      }
      if (i === full || (i === stages.length - 1 && progress >= stages.length)) {
        const start = s.points[0];
        ctx.beginPath();
        ctx.arc(start[0], start[1], lw + 3, 0, Math.PI * 2);
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });
  }, [progress, stages, ui]);

  if (!stages.length) return null;
  const current = Math.min(Math.floor(progress), stages.length - 1);
  const done = progress >= stages.length;

  return (
    <div className="space-y-2">
      <canvas
        ref={ref}
        width={ui.canvas.width}
        height={ui.canvas.height}
        className="w-full h-auto rounded-lg border border-outline"
        style={{ aspectRatio: `${ui.canvas.width} / ${ui.canvas.height}` }}
        role="img"
        aria-label={`Animated guide: ${done ? 'all stages drawn' : `drawing ${stages[current].label} of ${stages.length}`}`}
      />
      <div className="flex flex-wrap items-center gap-2">
        <button
          className={btn.primary}
          onClick={() => {
            if (done) setProgress(0);
            setPlaying((p) => !p);
          }}
        >
          {playing ? <Pause className="w-3.5 h-3.5" aria-hidden="true" /> : <Play className="w-3.5 h-3.5" aria-hidden="true" />}
          {playing ? 'Pause' : done ? 'Replay' : progress > 0 ? 'Continue' : 'Show me how'}
        </button>
        <button
          className={btn.secondary}
          onClick={() => {
            setPlaying(false);
            setProgress(0);
          }}
          aria-label="Reset the guide"
        >
          <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
        </button>
        <span className="text-sm text-on-surface-variant" aria-live="polite">
          {done
            ? `All ${stages.length} stages drawn`
            : !playing && progress > 0 && Number.isInteger(progress)
              ? `${progress} of ${stages.length} stages drawn`
              : progress > 0
                ? `Drawing ${stages[current].label} of ${stages.length}`
                : `${stages.length} stages`}
        </span>
      </div>
      <div className="flex flex-wrap gap-1" role="group" aria-label="Jump to a stage">
        {stages.map((s, i) => (
          <button
            key={i}
            onClick={() => {
              setPlaying(false);
              setProgress(i + 1);
            }}
            className={`px-2 py-0.5 rounded border text-xs font-mono ${i < Math.ceil(progress) ? 'border-cadmium-amber text-cadmium-amber' : 'border-outline text-on-surface-variant'}`}
            title={`Show stages 1 to ${i + 1}`}
          >
            {i + 1}
          </button>
        ))}
      </div>
      <p className="text-xs text-on-surface-variant">
        Orange is the stage being drawn, the green ring marks where it starts. This order is one suggested way, inferred from the finished image (INFERRED), not
        the artist's original order. Watch it, then draw from the target on your own.
      </p>
    </div>
  );
}
