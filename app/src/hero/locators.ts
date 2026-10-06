/**
 * Read-only parser for the evidence locator convention (tracks/common/locators.py):
 *   <source id>[#xywh=percent:x,y,w,h | #stroke=i[-j] | #onset=i[-j] | #step=i | #frame=t]
 */

import type { EvidenceRef, KnowledgeClaim, VerificationState } from '../types/contracts';

export interface ParsedLocator {
  source: string;
  key: 'xywh' | 'stroke' | 'onset' | 'step' | 'frame' | null;
  region?: { x: number; y: number; w: number; h: number }; // percent
  range?: [number, number];
  time?: number;
}

export function parseLocator(sourceId: string): ParsedLocator {
  const i = sourceId.indexOf('#');
  if (i < 0) return { source: sourceId, key: null };
  const source = sourceId.slice(0, i);
  const frag = sourceId.slice(i + 1);
  const eq = frag.indexOf('=');
  if (eq < 0) return { source, key: null };
  const key = frag.slice(0, eq);
  const value = frag.slice(eq + 1);
  if (key === 'xywh' && value.startsWith('percent:')) {
    const [x, y, w, h] = value.slice(8).split(',').map(Number);
    if ([x, y, w, h].every((n) => Number.isFinite(n))) return { source, key: 'xywh', region: { x, y, w, h } };
  }
  if (key === 'stroke' || key === 'onset' || key === 'step') {
    const [a, b] = value.split('-').map(Number);
    if (Number.isFinite(a)) return { source, key, range: [a, Number.isFinite(b) ? b : a] };
  }
  if (key === 'frame') {
    const t = Number(value);
    if (Number.isFinite(t)) return { source, key: 'frame', time: t };
  }
  return { source, key: null };
}

/** Claim-level verification label: the weakest state among its evidence; no evidence → unverified. */
export function claimVerification(claim: KnowledgeClaim): VerificationState {
  if (!claim.evidence_refs.length) return 'unverified';
  const states = claim.evidence_refs.map((e) => e.verification_state);
  if (states.includes('unverified')) return 'unverified';
  if (states.includes('inferred')) return 'inferred';
  return 'observed';
}

export function evidenceTime(ev: EvidenceRef | null | undefined): number | null {
  if (!ev) return null;
  if (typeof ev.start_sec === 'number') return ev.start_sec;
  const loc = parseLocator(ev.source_id);
  return loc.time ?? null;
}

export function fmtTime(sec: number | null | undefined): string {
  if (sec == null || !Number.isFinite(sec)) return '--:--';
  const m = Math.floor(sec / 60);
  const s = sec - m * 60;
  return `${String(m).padStart(2, '0')}:${s.toFixed(1).padStart(4, '0')}`;
}

export function fmtPosition(pos: number | null | undefined, kind: string): string {
  if (pos == null) return '—';
  if (kind === 'time' || kind === 'frame') return fmtTime(pos);
  if (kind === 'stroke') return `stroke ${pos}`;
  if (kind === 'beat') return `beat ${pos}`;
  return String(pos);
}
