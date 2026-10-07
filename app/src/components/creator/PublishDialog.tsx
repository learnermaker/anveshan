/**
 * PublishDialog: creator fills in credit, licence and consent, then submits to the steward queue (K9-P3 §2.4).
 */

import React, { useState } from 'react';
import { Send, X } from 'lucide-react';
import type { CaseView, LibraryRecord, LicenceId, SubmitBody } from '../../api/types';
import { ApiError } from '../../api/errors';
import { api } from '../../api/client';
import { ErrorNote, btn } from '../../hero/ui';
import { LICENCE_OPTIONS } from '../../copy/plain';
import { useEscape } from '../../hero/useEscape';

interface Props {
  view: CaseView;
  isOpen: boolean;
  onClose: () => void;
  onSubmitted: (rec: LibraryRecord) => void;
}

export function PublishDialog({ view, isOpen, onClose, onSubmitted }: Props) {
  useEscape(isOpen, onClose);

  const [creditName, setCreditName] = useState(view.access?.credit_name ?? '');
  const [licence, setLicence] = useState<LicenceId>('CC-BY-4.0');
  const [peopleVisible, setPeopleVisible] = useState(false);
  const [peopleConsented, setPeopleConsented] = useState(false);
  const [rightsConfirmed, setRightsConfirmed] = useState(false);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [blockers, setBlockers] = useState<string[]>([]);

  if (!isOpen) return null;

  const canSubmit = creditName.trim().length > 0 && rightsConfirmed && (!peopleVisible || peopleConsented);

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    setBlockers([]);
    const body: SubmitBody = {
      credit_name: creditName.trim(),
      licence,
      consent_scope: 'public_practice',
      rights_confirmed: rightsConfirmed,
      people_visible: peopleVisible,
      people_consented: peopleVisible ? peopleConsented : false,
      note: note.trim() || undefined,
    };
    try {
      const rec = await api.submitToLibrary(view.case_id, body);
      onSubmitted(rec);
    } catch (e) {
      if (e instanceof ApiError && e.status === 400) {
        const details = e.details as { blockers?: string[] } | null;
        if (details?.blockers?.length) {
          setBlockers(details.blockers);
          setBusy(false);
          return;
        }
      }
      setError(e);
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-4 bg-background/80 backdrop-blur-md overflow-y-auto"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="publish-dialog-title"
        className="w-full max-w-lg rounded-xl border border-outline bg-surface-container shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-outline">
          <h2 id="publish-dialog-title" className="font-semibold text-on-surface">Send for review</h2>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            title="Close (Esc)"
            className="flex items-center gap-1 px-2 py-1 rounded text-on-surface-variant hover:text-on-surface"
          >
            <X className="w-5 h-5" aria-hidden="true" />
            <span className="text-xs font-mono">Close</span>
          </button>
        </div>

        <div className="p-5 space-y-5 overflow-y-auto max-h-[75vh]">
          {/* Credit */}
          <div>
            <label htmlFor="publish-credit" className="block text-[11px] font-mono uppercase text-on-surface-variant mb-1">
              Credit (shown to learners) <span className="text-divergence-crimson">*</span>
            </label>
            <input
              id="publish-credit"
              value={creditName}
              maxLength={60}
              autoComplete="name"
              onChange={(e) => setCreditName(e.target.value)}
              className="w-full bg-surface-dim border border-outline rounded-lg px-3 py-2 text-sm outline-none focus:border-caliper-cyan"
              placeholder="Your name or handle"
              required
            />
          </div>

          {/* Licence */}
          <fieldset>
            <legend className="text-[11px] font-mono uppercase text-on-surface-variant mb-2">
              Licence <span className="text-divergence-crimson">*</span>
            </legend>
            <div className="space-y-2">
              {LICENCE_OPTIONS.map((opt) => (
                <label key={opt.id} className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="licence"
                    value={opt.id}
                    checked={licence === opt.id}
                    onChange={() => setLicence(opt.id)}
                    className="mt-0.5 accent-cadmium-amber"
                  />
                  <div>
                    <span className="text-sm font-semibold text-on-surface">{opt.label}</span>
                    <span className="block text-[11px] text-on-surface-variant">{opt.help}</span>
                  </div>
                </label>
              ))}
            </div>
          </fieldset>

          {/* Who can practise */}
          <div>
            <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-1">Who can practise it</div>
            <p className="text-sm text-on-surface-variant">Anyone using Anveshan, once a steward publishes it.</p>
          </div>

          {/* People visible */}
          <div className="space-y-2">
            <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-1">
              Are other people identifiable in your photo, video or audio?
            </div>
            <div className="flex gap-4">
              {(['No', 'Yes'] as const).map((label) => (
                <label key={label} className="flex items-center gap-2 cursor-pointer text-sm">
                  <input
                    type="radio"
                    name="people-visible"
                    checked={peopleVisible === (label === 'Yes')}
                    onChange={() => setPeopleVisible(label === 'Yes')}
                    className="accent-cadmium-amber"
                  />
                  {label}
                </label>
              ))}
            </div>
            {peopleVisible && (
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={peopleConsented}
                  onChange={(e) => setPeopleConsented(e.target.checked)}
                  className="mt-0.5 accent-cadmium-amber"
                  required
                />
                <span className="text-sm text-on-surface-variant">
                  They agreed to it being shared for practice.
                </span>
              </label>
            )}
          </div>

          {/* Rights */}
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={rightsConfirmed}
              onChange={(e) => setRightsConfirmed(e.target.checked)}
              className="mt-0.5 accent-cadmium-amber"
              required
            />
            <span className="text-sm text-on-surface-variant">
              I created this or have the right to share it. <span className="text-divergence-crimson">*</span>
            </span>
          </label>

          {/* Note to steward */}
          <div>
            <label htmlFor="publish-note" className="block text-[11px] font-mono uppercase text-on-surface-variant mb-1">
              Note to the steward (optional)
            </label>
            <textarea
              id="publish-note"
              value={note}
              maxLength={500}
              rows={3}
              onChange={(e) => setNote(e.target.value)}
              className="w-full bg-surface-dim border border-outline rounded-lg px-3 py-2 text-sm outline-none focus:border-caliper-cyan resize-none"
              placeholder="Anything you'd like to tell the reviewer…"
            />
          </div>

          {blockers.length > 0 && (
            <ul className="space-y-1 text-[11px] text-divergence-crimson">
              {blockers.map((b, i) => <li key={i}>{b}</li>)}
            </ul>
          )}

          <ErrorNote error={error} />

          <div className="space-y-2">
            <button
              onClick={() => void handleSubmit()}
              disabled={!canSubmit || busy}
              className={btn.primary}
            >
              <Send className="w-3.5 h-3.5" aria-hidden="true" />
              {busy ? 'Sending…' : 'Send for review'}
            </button>
            <p className="text-[11px] text-on-surface-variant">
              A steward checks every skill before it appears in the library. You can withdraw it at any time.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
