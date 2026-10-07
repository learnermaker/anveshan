/** Adapter: skill_model.specialists.line_art (KolamGoal-shaped payload) -> KolamUiView for KolamCanvas. */
import type { KolamCurveObj, KolamDot, KolamUiView } from '../../api/types';

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const num = (v: unknown, d: number): number => (typeof v === 'number' && Number.isFinite(v) ? v : d);

/** Returns null when the payload lacks a usable canvas (renders no canvas). */
export function lineArtToKolamUi(payload: unknown): KolamUiView | null {
  if (!isObj(payload) || !isObj(payload.canvas)) return null;
  const width = num(payload.canvas.width, 0);
  const height = num(payload.canvas.height, 0);
  if (width <= 0 || height <= 0) return null;

  const dots: KolamDot[] = (Array.isArray(payload.dots) ? payload.dots : []).filter(isObj).map((d) => ({
    id: typeof d.id === 'string' ? d.id : undefined,
    x: num(d.x, 0),
    y: num(d.y, 0),
    r: num(d.r, 3),
    relation: typeof d.relation === 'string' ? d.relation : undefined,
  }));

  const curves: KolamCurveObj[] = (Array.isArray(payload.curves) ? payload.curves : []).filter(isObj).map((c, i) => ({
    id: typeof c.id === 'string' ? c.id : `c${i}`,
    closed: c.closed === true,
    points: (Array.isArray(c.points) ? c.points : []).filter((p): p is number[] => Array.isArray(p) && p.length >= 2),
    stages: (Array.isArray(c.stages) ? c.stages : []).filter(isObj).map((s) => ({ id: String(s.id ?? ''), start: num(s.start, 0), end: num(s.end, 0) })),
  }));
  if (curves.length === 0) return null;

  return {
    canvas: { width, height },
    dots,
    curves,
    stroke_width: num(payload.stroke_width, 4),
    tau: typeof payload.tau === 'number' ? payload.tau : undefined,
    rotation_order: isObj(payload.symmetry) && typeof payload.symmetry.rotation_order === 'number' ? payload.symmetry.rotation_order : undefined,
    curve_count: curves.length,
    kind: 'kolam',
  };
}
