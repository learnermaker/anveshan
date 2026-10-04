import React, { useState } from 'react';
import { Key, Sparkles, X, Shield, Cpu, Check, Radio } from 'lucide-react';
import type { GeminiConfig } from '../types/gemini';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: GeminiConfig;
  onSaveConfig: (newConfig: GeminiConfig) => void;
}

export function SettingsModal({
  isOpen,
  onClose,
  config,
  onSaveConfig,
}: SettingsModalProps) {
  if (!isOpen) return null;

  const [mode, setMode] = useState<'REPLAY' | 'LIVE'>(config.mode);
  const [apiKey, setApiKey] = useState<string>(config.apiKey ?? '');
  const [modelName, setModelName] = useState<'gemini-2.5-flash' | 'gemini-2.5-pro'>(config.modelName);

  const handleSave = () => {
    onSaveConfig({
      mode,
      apiKey: apiKey.trim(),
      modelName,
      temperature: 0.1,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md animate-fade-in">
      <div className="bg-surface-elevated border border-outline rounded-xl shadow-2xl max-w-lg w-full overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 bg-surface-dim border-b border-outline flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Cpu className="w-5 h-5 text-cadmium-amber" />
            <h2 className="text-sm font-semibold font-mono text-on-surface">
              GEMINI MODEL GATEWAY & RUNTIME SETTINGS
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-on-surface-variant hover:text-on-surface transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 text-xs font-mono">
          {/* Execution Mode */}
          <div className="space-y-2">
            <label className="text-on-surface-variant uppercase font-semibold">
              ANALYSIS EXECUTION MODE:
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setMode('REPLAY')}
                className={`p-3 rounded-lg border text-left transition-all ${
                  mode === 'REPLAY'
                    ? 'border-transmission-emerald bg-transmission-emerald/15 text-on-surface'
                    : 'border-outline bg-surface-dim text-on-surface-variant'
                }`}
              >
                <div className="font-bold flex items-center gap-1.5 text-transmission-emerald">
                  <span className="w-2 h-2 rounded-full bg-transmission-emerald" />
                  REPLAY FIXTURES
                </div>
                <div className="text-[10px] text-on-surface-variant mt-1 leading-normal font-sans">
                  Deterministic cached outputs. Instant, zero API quota risk, 100% demo reliability.
                </div>
              </button>

              <button
                type="button"
                onClick={() => setMode('LIVE')}
                className={`p-3 rounded-lg border text-left transition-all ${
                  mode === 'LIVE'
                    ? 'border-caliper-cyan bg-caliper-cyan/15 text-on-surface'
                    : 'border-outline bg-surface-dim text-on-surface-variant'
                }`}
              >
                <div className="font-bold flex items-center gap-1.5 text-caliper-cyan">
                  <Sparkles className="w-3.5 h-3.5" />
                  GEMINI LIVE API
                </div>
                <div className="text-[10px] text-on-surface-variant mt-1 leading-normal font-sans">
                  Real Google Generative AI REST endpoint calls with structured JSON output.
                </div>
              </button>
            </div>
          </div>

          {/* Model Name */}
          <div className="space-y-2">
            <label className="text-on-surface-variant uppercase font-semibold">
              GEMINI MODEL TARGET:
            </label>
            <div className="grid grid-cols-2 gap-3">
              {(['gemini-2.5-flash', 'gemini-2.5-pro'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setModelName(m)}
                  className={`py-2 px-3 rounded border text-center transition-all ${
                    modelName === m
                      ? 'border-cadmium-amber bg-cadmium-amber/15 text-cadmium-amber font-bold'
                      : 'border-outline bg-surface-dim text-on-surface-variant'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          {/* API Key */}
          {mode === 'LIVE' && (
            <div className="space-y-2 animate-fade-in">
              <label className="text-on-surface-variant uppercase font-semibold flex items-center justify-between">
                <span>GEMINI API KEY:</span>
                <span className="text-[10px] text-cadmium-amber">STORED LOCALLY IN BROWSER</span>
              </label>
              <div className="relative">
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="AIzaSy..."
                  className="w-full bg-surface-dim border border-outline rounded-lg px-3 py-2 text-on-surface placeholder:text-on-surface-variant/40 focus:border-caliper-cyan outline-none"
                />
              </div>
              <p className="text-[10px] text-on-surface-variant font-sans">
                If key is invalid or quota is exceeded, system will automatically fall back to deterministic replay fixtures.
              </p>
            </div>
          )}

          {/* Honesty Note */}
          <div className="p-3 bg-surface-dim rounded border border-outline/40 text-[11px] text-on-surface-variant leading-relaxed font-sans">
            <strong className="text-on-surface font-mono">Epistemic Transparency:</strong> The application header displays whether analysis is running via Replay Fixtures or Live Gemini calls. Synthetic/replay fixtures are never misrepresented as live calls.
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-surface-dim border-t border-outline flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface transition-colors"
          >
            CANCEL
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="px-4 py-2 rounded-lg bg-cadmium-amber hover:bg-cadmium-amber/90 text-background font-mono font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 transition-colors"
          >
            <Check className="w-3.5 h-3.5" />
            <span>SAVE CONFIGURATION</span>
          </button>
        </div>
      </div>
    </div>
  );
}
