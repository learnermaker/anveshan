/**
 * StewardConsole: the steward surface — sign-in, tabs, overview (K9-P3 §3.1).
 */

import React, { useEffect, useState } from 'react';
import { BarChart3, Gauge, Inbox, Library, LogOut, ShieldCheck } from 'lucide-react';
import type { HealthResponse, StewardOverview } from '../../api/types';
import { api } from '../../api/client';
import { ApiError } from '../../api/errors';
import { clearStewardToken, getStewardToken, subscribeStewardToken } from '../../api/steward';
import { StewardSignIn } from './StewardSignIn';
import { OverviewTab } from './OverviewTab';
import { QueueTab } from './QueueTab';
import { LibraryTab } from './LibraryTab';
import { ConsentTab } from './ConsentTab';
import { UsageTab } from './UsageTab';

type Tab = 'overview' | 'queue' | 'library' | 'consent' | 'usage';

const TAB_KEY = 'anveshan.steward_tab';

function readSavedTab(): Tab {
  try {
    const v = sessionStorage.getItem(TAB_KEY);
    if (v && ['overview', 'queue', 'library', 'consent', 'usage'].includes(v)) return v as Tab;
  } catch { /* storage blocked */ }
  return 'overview';
}

function saveTab(t: Tab) {
  try { sessionStorage.setItem(TAB_KEY, t); } catch { /* ignore */ }
}

interface Props {
  health: HealthResponse | null;
  onOpenSkill: (caseId: string) => void;
  onLibraryChanged: () => void;
}

export function StewardConsole({ health, onOpenSkill, onLibraryChanged }: Props) {
  const [token, setToken] = useState<string | null>(getStewardToken());
  const [tab, setTab] = useState<Tab>(readSavedTab);
  const [signedOutMsg, setSignedOutMsg] = useState<string | null>(null);
  // For passing a case directly into the queue-review flow from the overview
  const [reviewingFromOverview, setReviewingFromOverview] = useState<string | null>(null);

  // Queue badge count — hoisted before any early return (Rules of Hooks)
  const [queueCount, setQueueCount] = useState(0);

  const stewardOpen = health?.steward_open === true;
  const stewardEnabled = health?.steward_enabled !== false;
  const signedIn = stewardOpen || Boolean(token);

  const changeTab = (t: Tab) => { setTab(t); saveTab(t); };

  // 401 handling: if any steward call returns 401, log out and show message
  const handle401 = (e: unknown) => {
    if (e instanceof ApiError && e.status === 401) {
      clearStewardToken();
      setSignedOutMsg('Your steward session ended. Enter the code again.');
      return true;
    }
    return false;
  };

  useEffect(() => subscribeStewardToken(setToken), []);
  useEffect(() => {
    if (!signedIn) return;
    api.stewardOverview()
      .then((d: StewardOverview) => setQueueCount(d.waiting_review))
      .catch((e: unknown) => handle401(e));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signedIn]);

  if (!stewardEnabled) {
    return (
      <div className="max-w-sm mx-auto text-center py-10 space-y-3">
        <p className="text-sm text-on-surface-variant">The steward console isn't enabled on this server.</p>
        <a href="?view=discovery" className="text-caliper-cyan underline text-sm">Back to the library</a>
      </div>
    );
  }

  if (!signedIn) {
    return <StewardSignIn onSignedIn={() => setSignedOutMsg(null)} message={signedOutMsg} />;
  }

  const tabs: { id: Tab; label: string; icon: typeof Gauge }[] = [
    { id: 'overview', label: 'Overview', icon: Gauge },
    { id: 'queue', label: 'Review queue', icon: Inbox },
    { id: 'library', label: 'Library', icon: Library },
    { id: 'consent', label: 'Consent & licences', icon: ShieldCheck },
    { id: 'usage', label: 'Usage', icon: BarChart3 },
  ];

  const handleOpenSkill = (id: string) => {
    onOpenSkill(id);
  };

  return (
    <div className="flex flex-col gap-5 w-full max-w-5xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <h1 className="font-serif text-3xl text-on-surface">Steward console</h1>
            <p className="text-sm text-on-surface-variant">
              Look after the library: check skills before they are published, keep credit and consent records, and watch usage.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {stewardOpen && (
              <span className="text-[11px] font-mono text-transmission-emerald border border-transmission-emerald/40 rounded px-2 py-0.5">
                Open on this local server
              </span>
            )}
            {!stewardOpen && (
              <button
                onClick={() => { clearStewardToken(); setSignedOutMsg(null); }}
                className="flex items-center gap-1.5 text-[11px] font-mono text-on-surface-variant hover:text-on-surface transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" aria-hidden="true" /> Sign out
              </button>
            )}
          </div>
        </div>

        {/* Steward banner */}
        <div className="flex items-start gap-2 p-3 rounded-lg border border-cadmium-amber/40 bg-cadmium-amber/5 text-[11px] text-on-surface-variant">
          Changes on this demo server are temporary and are lost when it restarts. To keep an expert's review of a featured skill, use Download decisions and commit it.
        </div>
      </div>

      {/* Tabs */}
      <div role="tablist" aria-label="Steward console tabs" className="flex flex-wrap gap-1 border-b border-outline pb-0">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            id={`tab-${id}`}
            role="tab"
            aria-selected={tab === id}
            onClick={() => { changeTab(id); setReviewingFromOverview(null); }}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-mono border-b-2 transition-colors whitespace-nowrap ${
              tab === id
                ? 'border-cadmium-amber text-on-surface font-bold'
                : 'border-transparent text-on-surface-variant hover:text-on-surface hover:border-outline'
            }`}
          >
            <Icon className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
            {label}
            {id === 'queue' && queueCount > 0 && (
              <span className="ml-1 px-1.5 py-0 rounded-full bg-cadmium-amber text-background text-[11px] font-bold">
                {queueCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab panel */}
      <div role="tabpanel" aria-labelledby={`tab-${tab}`} className="min-h-[300px]">
        {tab === 'overview' && (
          <OverviewTab
            onSwitchToQueue={() => changeTab('queue')}
            onReviewCase={(id) => { changeTab('queue'); setReviewingFromOverview(id); }}
          />
        )}
        {tab === 'queue' && (
          <QueueTab
            onOpenSkill={handleOpenSkill}
            onLibraryChanged={() => { onLibraryChanged(); api.stewardOverview().then((d: StewardOverview) => setQueueCount(d.waiting_review)).catch((e: unknown) => handle401(e)); }}
            reviewingCaseId={reviewingFromOverview}
            onClearReviewing={() => setReviewingFromOverview(null)}
          />
        )}
        {tab === 'library' && (
          <LibraryTab
            onOpenSkill={handleOpenSkill}
            onLibraryChanged={onLibraryChanged}
          />
        )}
        {tab === 'consent' && <ConsentTab />}
        {tab === 'usage' && <UsageTab />}
      </div>
    </div>
  );
}
