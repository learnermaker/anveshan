/** "Use your own Gemini API key" dialog (bring your own key). The key stays in this browser. */

import React, { useEffect, useState } from 'react';
import { Check, Eye, EyeOff, KeyRound, X } from 'lucide-react';
import { api } from '../api/client';
import { clearUserKey, getUserKey, isRemembered, looksLikeKey, maskKey, setUserKey } from '../api/userKey';
import { ErrorNote, btn } from '../hero/ui';
import { useEscape } from '../hero/useEscape';

export function ApiKeyModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  useEscape(isOpen, onClose);
  const [value, setValue] = useState('');
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const [ok, setOk] = useState<string | null>(null);
  const current = getUserKey();

  useEffect(() => {
    if (isOpen) {
      setValue('');
      setErr(null);
      setOk(null);
      setShow(false);
      setRemember(isRemembered());
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const save = async () => {
    const k = value.trim();
    setErr(null);
    setOk(null);
    if (!looksLikeKey(k)) {
      setErr(new Error('That does not look like a Google API key. New keys (from AI Studio, May 2026+) start with "AQ.Ab"; older keys start with "AIza".'));
      return;
    }
    const previous = getUserKey();
    const wasRemembered = isRemembered();
    setUserKey(k, remember);
    setBusy(true);
    try {
      const r = await api.checkKey();
      setOk(`Key works (${r.model.replace(/^models\//, '')}). Live AI calls now use your key.`);
      setValue('');
    } catch (e) {
      // keep the previous state if the new key is not accepted
      if (previous) setUserKey(previous, wasRemembered);
      else clearUserKey();
      setErr(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-4 bg-background/80 backdrop-blur-md overflow-y-auto" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="key-title"
        className="w-full max-w-lg rounded-xl border border-outline bg-surface-container shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-outline">
          <h2 id="key-title" className="flex items-center gap-2 font-semibold text-on-surface">
            <KeyRound className="w-4 h-4 text-cadmium-amber" aria-hidden="true" /> Use your own Gemini API key
          </h2>
          <button onClick={onClose} aria-label="Close" title="Close (Esc)" className="flex items-center gap-1 px-2 py-1 rounded text-on-surface-variant hover:text-on-surface">
            <X className="w-5 h-5" aria-hidden="true" />
            <span className="text-xs font-mono">Close</span>
          </button>
        </div>
        <div className="p-5 space-y-4 text-sm">
          <p className="text-on-surface-variant leading-relaxed">
            Optional. The demo has a shared daily AI budget. With your own key, AI calls (perceiving uploads, judging checks, coaching wording) run on your quota
            instead, without the shared limit. Get a free key at{' '}
            <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" className="text-caliper-cyan underline">
              aistudio.google.com/apikey
            </a>
            .
          </p>

          {current && (
            <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-lg border border-transmission-emerald/40 bg-transmission-emerald/5">
              <span className="flex items-center gap-2">
                <Check className="w-4 h-4 text-transmission-emerald" aria-hidden="true" />
                Using your key <code className="font-mono">{maskKey(current)}</code>
                <span className="text-xs text-on-surface-variant">({isRemembered() ? 'remembered on this device' : 'this tab only'})</span>
              </span>
              <button
                className={btn.secondary}
                onClick={() => {
                  clearUserKey();
                  setOk('Your key was removed from this browser.');
                }}
              >
                Remove key
              </button>
            </div>
          )}

          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <label className="block space-y-1">
              <span className="text-xs font-semibold text-on-surface">{current ? 'Replace with another key' : 'API key'}</span>
              <span className="flex gap-2">
                <input
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  type={show ? 'text' : 'password'}
                  autoComplete="off"
                  spellCheck={false}
                  placeholder="AQ.Ab…"
                  className="flex-1 min-w-0 bg-surface-dim border border-outline rounded-lg px-3 py-2 font-mono text-sm outline-none focus:border-caliper-cyan"
                />
                <button type="button" onClick={() => setShow((v) => !v)} className={btn.secondary} aria-label={show ? 'Hide key' : 'Show key'}>
                  {show ? <EyeOff className="w-4 h-4" aria-hidden="true" /> : <Eye className="w-4 h-4" aria-hidden="true" />}
                </button>
              </span>
            </label>
            <label className="flex items-start gap-2 text-xs text-on-surface-variant">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="mt-0.5" />
              <span>Remember on this device. Leave this off on shared computers: the key is then forgotten when you close the tab.</span>
            </label>
            <button type="submit" disabled={busy || !value.trim()} className={btn.primary}>
              {busy ? 'Checking the key…' : 'Check and use this key'}
            </button>
          </form>

          {ok && (
            <p role="status" className="text-transmission-emerald">
              {ok}
            </p>
          )}
          <ErrorNote error={err} />

          <details className="text-xs text-on-surface-variant">
            <summary className="cursor-pointer select-none">How your key is handled</summary>
            <ul className="mt-2 list-disc pl-5 space-y-1">
              <li>It is stored only in this browser (this tab, or this device if you choose), never in a link.</li>
              <li>It is sent over HTTPS only to this app's own server, in a request header, and used for that request only.</li>
              <li>The server never saves it, logs it or shows it back; error messages are scrubbed of it.</li>
              <li>Checking it reads model information, which uses no generation quota.</li>
              <li>You can remove it here at any time. For extra safety, restrict the key to the Gemini API in Google AI Studio and delete it after the demo.</li>
            </ul>
          </details>
        </div>
      </div>
    </div>
  );
}
