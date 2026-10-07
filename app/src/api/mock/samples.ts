/**
 * MOCK sample attempts and sample sources (VITE_API_BASE=mock). SYNTHETIC canned data only.
 * The real service serves committed sample files (docs/kiro/specs/K9-P4-SAMPLES.md).
 */

import type { AttemptUpload } from '../client';
import type { CaseView } from '../types';
import type { SampleAttempt, SampleSource } from '../types-product';

const KIND_BY_BASE: Record<string, string> = { kolam: 'image', tabla: 'audio', origami: 'video', 'origami-crane': 'video' };

function kindFor(v: CaseView): string {
  if (v.modality === 'universal') return v.profile?.learner_input_kinds?.[0] ?? 'image';
  return KIND_BY_BASE[v.case_id.split('~')[0]] ?? 'image';
}

export function mockSamplesFor(v: CaseView): SampleAttempt[] {
  const kind = kindFor(v);
  return [
    { sample_id: 'good', label: 'A careful attempt', quality: 'good', attempt_kind: kind, description: 'Close to the source. Expect most checks to be met.', preview_url: null, synthetic: true, credit: null },
    { sample_id: 'flawed', label: 'An attempt with a mistake', quality: 'flawed', attempt_kind: kind, description: 'One clear mistake. See where the feedback says it first went off track.', preview_url: null, synthetic: true, credit: null },
    { sample_id: 'unrelated', label: 'Something unrelated', quality: 'unrelated', attempt_kind: kind, description: 'Not this skill at all. Anveshan should say so instead of scoring it.', preview_url: null, synthetic: true, credit: null },
  ];
}

const MIME: Record<string, string> = { image: 'image/png', audio: 'audio/wav', video: 'video/mp4', trace: 'application/json' };

export function mockSampleUpload(v: CaseView, sampleId: string): AttemptUpload {
  // trace samples would need real stroke JSON; the mock evaluates kolam samples as photos
  const kind = kindFor(v) === 'trace' ? 'image' : kindFor(v);
  const file = new Blob([`synthetic sample ${sampleId}`], { type: MIME[kind] ?? 'application/octet-stream' });
  return { kind: kind as AttemptUpload['kind'], file, fileName: `sample-${sampleId}.${kind === 'image' ? 'png' : kind === 'audio' ? 'wav' : 'mp4'}` };
}

export function mockSampleSources(): SampleSource[] {
  return [
    { sample_id: 'kolam-photo', label: 'A kolam drawing (photo)', description: 'A finished line drawing around dots.', mime_type: 'image/png', preview_url: '', credit: 'Synthetic (mock)', licence: 'CC0-1.0' },
    { sample_id: 'tabla-clip', label: 'A short tabla rhythm (audio)', description: 'A steady rhythm pattern.', mime_type: 'audio/wav', preview_url: '', credit: 'Synthetic (mock)', licence: 'CC0-1.0' },
  ];
}

export function mockAnalyzeSampleFile(sampleId: string): File {
  const audio = sampleId.includes('tabla');
  return new File([`synthetic sample source ${sampleId}`], audio ? `${sampleId}.wav` : `${sampleId}.png`, { type: audio ? 'audio/wav' : 'image/png' });
}
