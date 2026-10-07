import React, { useEffect, useState } from 'react';
import { Cpu, RefreshCw, X } from 'lucide-react';
import { api } from '../api/client';
import { API_BASE, IS_MOCK, getRequestedMode, setRequestedMode, type RequestedMode } from '../api/runtime';
import type { HealthResponse } from '../api/types';
import { Badge, ErrorNote, MockBadge, Spinner } from '../hero/ui';
import { useEscape } from '../hero/useEscape';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Read-only Runtime panel. Shows what the service reports at /api/health and lets the viewer
 * request a mode (?mode=live|recorded). No keys or model calls live in the browser.
 */
export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<RequestedMode>(getRequestedMode());

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      setHealth(await api.health());
    } catch (e) {
      setErr(e);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) void load();
  }, [isOpen]);

  useEscape(isOpen, onClose);
  if (!isOpen) return null;

  const choose = (m: RequestedMode) => {
    setMode(m);
    setRequestedMode(m);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md animate-fade-in" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-runtime-title"
        className="bg-surface-container border border-outline rounded-xl shadow-2xl max-w-lg w-full overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 bg-surface-dim border-b border-outline flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Cpu className="w-5 h-5 text-cadmium-amber" aria-hidden="true" />
            <h2 id="settings-runtime-title" className="text-sm font-semibold font-mono text-on-surface">RUNTIME</h2>
            <MockBadge />
          </div>
          <button onClick={onClose} className="flex items-center gap-1 px-2 py-1 rounded text-on-surface-variant hover:text-on-surface transition-colors" aria-label="Close" title="Close (Esc)">
            <X className="w-5 h-5" aria-hidden="true" /><span className="text-xs font-mono">Close</span>
          </button>
        </div>

        <div className="p-6 space-y-5 text-xs font-mono">
          <div className="space-y-1">
            <div className="text-on-surface-variant uppercase font-semibold">Service</div>
            <div className="text-on-surface break-all">{IS_MOCK ? 'in-browser mock (VITE_API_BASE=mock)' : API_BASE || `${window.location.origin} (same origin)`}</div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-on-surface-variant uppercase font-semibold">/api/health</span>
              <button onClick={load} className="text-on-surface-variant hover:text-on-surface flex items-center gap-1">
                <RefreshCw className="w-3 h-3" /> refresh
              </button>
            </div>
            {loading && <Spinner label="Checking service…" />}
            <ErrorNote error={err} />
            {health && (
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 p-3 rounded-lg bg-surface-dim border border-outline/60">
                <dt className="text-on-surface-variant">status</dt>
                <dd>{health.ok ? <Badge tone="emerald">OK</Badge> : <Badge tone="crimson">NOT OK</Badge>}</dd>
                <dt className="text-on-surface-variant">default mode</dt>
                <dd className="text-on-surface">{health.mode}</dd>
                <dt className="text-on-surface-variant">text + image</dt>
                <dd className="text-on-surface">{health.models.text_image}</dd>
                <dt className="text-on-surface-variant">video frames</dt>
                <dd className="text-on-surface">{health.models.video_frames}</dd>
                <dt className="text-on-surface-variant">audio model</dt>
                <dd>{health.models.audio_enabled ? <Badge tone="cyan">ENABLED</Badge> : <Badge tone="muted">DISABLED — bol criteria UNCERTAIN</Badge>}</dd>
              </dl>
            )}
          </div>

          <div className="space-y-2">
            <div className="text-on-surface-variant uppercase font-semibold">Requested mode (sent as ?mode=)</div>
            <div className="grid grid-cols-3 gap-2">
              {(['default', 'recorded', 'live'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => choose(m)}
                  className={`py-2 rounded border uppercase transition-colors ${mode === m ? 'border-cadmium-amber bg-cadmium-amber/15 text-cadmium-amber font-bold' : 'border-outline bg-surface-dim text-on-surface-variant hover:text-on-surface'}`}
                >
                  {m === 'default' ? 'server default' : m}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-on-surface-variant font-sans leading-relaxed">
              <b>recorded</b> replays recorded model runs (fails with REPLAY_MISMATCH rather than calling a model). <b>live</b> calls models on the server. Each result shows what actually ran: LIVE, RECORDED LIVE or DETERMINISTIC.
            </p>
          </div>

          <div className="p-3 bg-surface-dim rounded border border-outline/40 text-[11px] text-on-surface-variant leading-relaxed font-sans">
            Model keys and calls live only on the server. The four showcase cases are SYNTHETIC replay fixtures and never call the service.
          </div>
        </div>
      </div>
    </div>
  );
}
