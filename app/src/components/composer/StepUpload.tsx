/**
 * Step 1: Upload — drop zone + optional title/description + rights checkbox.
 * Client-side guards: ≤ 30 MB; video 8–600 s; audio 3–60 s; image short side ≥ 64 px.
 */

import React, { useEffect, useRef, useState } from 'react';
import { FileUp, Upload } from 'lucide-react';
import type { SampleSource } from '../../api/types';
import { api } from '../../api/client';
import { ErrorNote, KeyHint, Spinner } from '../../hero/ui';

export interface UploadPayload {
  file: File;
  title: string;
  description: string;
  rightsConfirmed: boolean;
}

interface Props {
  onSubmit: (payload: UploadPayload) => void;
  onAnalyzeSample: (sampleId: string) => void;
  onCancel: () => void;
  error: unknown;
}

const MAX_BYTES = 30 * 1024 * 1024;

function humanSize(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1e6) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1e6).toFixed(1)} MB`;
}

function fileIcon(mime: string) {
  if (mime.startsWith('video/')) return '🎬';
  if (mime.startsWith('audio/')) return '🎵';
  return '🖼';
}

export function StepUpload({ onSubmit, onAnalyzeSample, onCancel, error }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [rights, setRights] = useState(false);
  const [guardError, setGuardError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Sample sources
  const [samples, setSamples] = useState<SampleSource[] | null>(null);
  const [samplesError, setSamplesError] = useState<unknown>(null);
  const [sampleBusy, setSampleBusy] = useState<string | null>(null);

  useEffect(() => {
    api.listSampleSources()
      .then(setSamples)
      .catch(setSamplesError);
  }, []);

  const validateAndSet = async (f: File) => {
    setGuardError(null);
    // Size
    if (f.size > MAX_BYTES) {
      setGuardError(`File is ${humanSize(f.size)} — limit is 30 MB.`);
      return;
    }
    // Duration / dimensions for audio and video
    if (f.type.startsWith('video/') || f.type.startsWith('audio/')) {
      const url = URL.createObjectURL(f);
      const el: HTMLVideoElement | HTMLAudioElement = f.type.startsWith('video/') ? document.createElement('video') : document.createElement('audio');
      el.src = url;
      const result = await new Promise<string | null>((resolve) => {
        const t = setTimeout(() => resolve(null), 5000); // timeout
        el.addEventListener('loadedmetadata', () => {
          clearTimeout(t);
          const d = el.duration;
          if (f.type.startsWith('video/') && (d < 8 || d > 600)) {
            resolve(`Video duration is ${d.toFixed(0)} s — required range: 8–600 s.`);
          } else if (f.type.startsWith('audio/') && (d < 3 || d > 60)) {
            resolve(`Audio duration is ${d.toFixed(0)} s — required range: 3–60 s.`);
          } else {
            resolve(null);
          }
        });
        el.addEventListener('error', () => { clearTimeout(t); resolve(null); });
        el.load();
      });
      URL.revokeObjectURL(url);
      if (result) { setGuardError(result); return; }
    }
    // Image short-side check
    if (f.type.startsWith('image/')) {
      const url = URL.createObjectURL(f);
      const result = await new Promise<string | null>((resolve) => {
        const img = new Image();
        img.onload = () => {
          const short = Math.min(img.naturalWidth, img.naturalHeight);
          resolve(short < 64 ? `Image short side is ${short} px — minimum is 64 px.` : null);
          URL.revokeObjectURL(url);
        };
        img.onerror = () => { URL.revokeObjectURL(url); resolve(null); };
        img.src = url;
      });
      if (result) { setGuardError(result); return; }
      setPreview(URL.createObjectURL(f));
    } else {
      setPreview(null);
    }
    setFile(f);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) void validateAndSet(f);
  };

  const canSubmit = file && rights && !guardError;

  return (
    <div className="flex flex-col gap-6 max-w-2xl mx-auto animate-fade-in">
      <div className="space-y-1">
        <div className="text-[11px] font-mono uppercase tracking-widest text-cadmium-amber font-bold">Composer · Step 1</div>
        <h2 className="text-2xl font-serif text-on-surface">Show how you do it</h2>
        <p className="text-sm text-on-surface-variant">Add a photo of something you made, a short video of your hands at work, or a recording of you playing. The AI looks at it and proposes a practice task. You check everything before anyone else sees it.</p>
        <KeyHint />
      </div>

      <div
        role="button"
        tabIndex={0}
        aria-label="Drop zone: drag and drop a file here, or click to browse"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        className={`flex flex-col items-center gap-3 p-8 rounded-xl border-2 border-dashed cursor-pointer transition-colors ${file ? 'border-transmission-emerald bg-transmission-emerald/5' : 'border-outline bg-surface-dim hover:border-cadmium-amber'}`}
      >
        {file ? (
          <>
            <span className="text-3xl" aria-hidden="true">{fileIcon(file.type)}</span>
            <div className="text-sm font-semibold text-on-surface">{file.name}</div>
            <div className="text-[11px] font-mono text-on-surface-variant">{file.type || 'unknown type'} · {humanSize(file.size)}</div>
            {preview && <img src={preview} alt="preview" className="max-h-40 rounded-lg border border-outline mt-1" />}
          </>
        ) : (
          <>
            <Upload className="w-8 h-8 text-outline" />
            <span className="text-sm text-on-surface-variant">Drag and drop here, or click to browse</span>
            <span className="text-[11px] font-mono text-outline">image / video / audio · max 30 MB</span>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/*,video/*,audio/*"
          className="hidden"
          aria-label="Choose a file"
          onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) void validateAndSet(f); }}
        />
      </div>

      {guardError && <p className="text-[11px] font-mono text-divergence-crimson">{guardError}</p>}

      {/* No file to hand? Try with an example (§4a) */}
      {samples === null && !samplesError && <Spinner label="Loading examples…" />}
      {samplesError != null && <ErrorNote error={samplesError} />}
      {samples && samples.length > 0 && (
        <div className="space-y-3">
          <div className="text-[11px] font-mono uppercase tracking-widest text-on-surface-variant font-bold">
            No file to hand? Try with an example
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {samples.map((s) => (
              <div key={s.sample_id} className="rounded-lg border border-outline bg-surface-dim p-3 space-y-2">
                <div className="font-semibold text-sm text-on-surface">{s.label}</div>
                <p className="text-[11px] text-on-surface-variant">{s.description}</p>
                <p data-plain-exempt className="text-[11px] font-mono text-on-surface-variant">
                  {s.credit} ({s.licence})
                </p>
                <button
                  onClick={() => {
                    setSampleBusy(s.sample_id);
                    onAnalyzeSample(s.sample_id);
                  }}
                  disabled={sampleBusy !== null}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-outline bg-surface-container hover:border-cadmium-amber text-on-surface font-mono text-[11px] uppercase tracking-wider transition-colors disabled:opacity-40"
                >
                  {sampleBusy === s.sample_id ? 'Loading…' : 'Use this example'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-3">
        <div>
          <label htmlFor="composer-title" className="block text-[11px] font-mono uppercase text-on-surface-variant mb-1">
            What is this skill? (optional · ≤ 60 chars)
          </label>
          <input
            id="composer-title"
            value={title}
            maxLength={60}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Kolam line drawing · tabla 16-beat cycle"
            className="w-full bg-surface-dim border border-outline rounded-lg px-3 py-2 text-sm outline-none focus:border-caliper-cyan"
          />
        </div>
        <div>
          <label htmlFor="composer-desc" className="block text-[11px] font-mono uppercase text-on-surface-variant mb-1">
            What should a learner achieve? (optional · ≤ 300 chars)
          </label>
          <textarea
            id="composer-desc"
            value={description}
            maxLength={300}
            rows={3}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. Reproduce the pattern with matching stroke continuity and layout"
            className="w-full bg-surface-dim border border-outline rounded-lg px-3 py-2 text-sm outline-none focus:border-caliper-cyan resize-none"
          />
        </div>
      </div>

      <label className="flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={rights}
          onChange={(e) => setRights(e.target.checked)}
          className="mt-0.5 accent-cadmium-amber"
          aria-required="true"
        />
        <span className="text-xs text-on-surface-variant leading-relaxed">
          I confirm this file is my own work, is in the public domain, or is licensed for reuse (CC0, CC BY, CC BY-SA). I have the right to upload and teach from it.
        </span>
      </label>

      <ErrorNote error={error} />

      <div className="flex items-center gap-3">
        <button
          onClick={() => canSubmit && onSubmit({ file: file!, title, description, rightsConfirmed: rights })}
          disabled={!canSubmit}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-mono font-bold text-[11px] uppercase tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <FileUp className="w-3.5 h-3.5" /> Analyse source
        </button>
        <button onClick={onCancel} className="text-[11px] font-mono text-on-surface-variant hover:text-on-surface">
          Cancel
        </button>
      </div>
      <p className="text-[11px] text-on-surface-variant">This usually takes 10–30 seconds for photos and audio, and up to about 90 seconds for videos.</p>
    </div>
  );
}
