/**
 * StewardSignIn: access-code form for the steward console (K9-P3 §3.2).
 */

import React, { useState } from 'react';
import { api } from '../../api/client';
import { ApiError } from '../../api/errors';
import { IS_MOCK } from '../../api/runtime';
import { clearStewardToken, setStewardToken } from '../../api/steward';
import { ErrorNote, btn } from '../../hero/ui';

interface Props {
  onSignedIn: () => void;
  message?: string | null;
}

export function StewardSignIn({ onSignedIn, message }: Props) {
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [codeError, setCodeError] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  const handleSignIn = async () => {
    if (!code.trim()) return;
    setBusy(true);
    setCodeError(null);
    setError(null);
    setStewardToken(code.trim());
    try {
      await api.stewardCheck();
      onSignedIn();
    } catch (e) {
      clearStewardToken();
      if (e instanceof ApiError && e.status === 401) {
        setCodeError('That code is not right.');
      } else if (e instanceof ApiError && e.status === 429) {
        setError(e);
      } else {
        setError(e);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-sm mx-auto">
      <div className="rounded-xl border border-outline bg-surface-container p-6 space-y-4">
        <div className="space-y-1">
          <h2 className="font-semibold text-on-surface">Steward access</h2>
          <p className="text-sm text-on-surface-variant">
            Stewards look after the library: they check skills before they are published, keep credit and consent records, and watch usage.
          </p>
        </div>

        {message && (
          <p className="text-sm text-cadmium-amber">{message}</p>
        )}

        {IS_MOCK && (
          <p className="text-[11px] font-mono text-caliper-cyan bg-caliper-cyan/5 border border-caliper-cyan/20 rounded px-3 py-2">
            Mock mode: the code is "steward".
          </p>
        )}

        <form
          onSubmit={(e) => { e.preventDefault(); void handleSignIn(); }}
          className="space-y-3"
        >
          <label className="block space-y-1">
            <span className="text-[11px] font-mono uppercase text-on-surface-variant">Access code</span>
            <input
              type="password"
              value={code}
              autoComplete="off"
              onChange={(e) => setCode(e.target.value)}
              className="w-full bg-surface-dim border border-outline rounded-lg px-3 py-2 text-sm outline-none focus:border-caliper-cyan font-mono"
              placeholder="Enter the access code"
            />
          </label>

          {codeError && (
            <p className="text-[11px] text-divergence-crimson font-mono">{codeError}</p>
          )}

          <button
            type="submit"
            disabled={busy || !code.trim()}
            className={btn.primary}
          >
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <ErrorNote error={error} />

        <p className="text-[11px] text-on-surface-variant">
          The code stays in this tab only and is sent only to this app's server.
        </p>
      </div>
    </div>
  );
}
