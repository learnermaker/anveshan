"""K9 Phase 0: apply the shared UI foundation (types, client, mock, copy, debug flag).

Run from the repository root of the worktree that should receive the foundation:

    .venv\\Scripts\\python.exe docs\\kiro\\specs\\K9-P0-files\\apply_p0.py

It copies the new files under docs/kiro/specs/K9-P0-files/app/ into app/ and applies exact,
anchored edits to existing files. Every anchor is asserted; if one is missing the script stops
before writing anything, so a half-applied state cannot happen. Running it twice is safe: it
detects that the foundation is already present and exits.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent
NEW_FILES = [
    "app/src/api/types-product.ts",
    "app/src/api/debug.ts",
    "app/src/api/steward.ts",
    "app/src/api/mock/library.ts",
    "app/src/copy/plain.ts",
]

# (file, anchor, replacement). Each anchor must occur exactly once.
K9_ICONS = ["Lightbulb", "Users", "BarChart3", "Inbox", "Library", "FileDown", "LogOut", "Trash2", "BookOpen", "Share2", "Gauge", "HardDrive", "ListChecks", "Hourglass", "Globe"]

EDITS = [
    (
        "app/src/vite-env.d.ts",
        "  export const Zap: LucideIcon;\n}\n",
        "  export const Zap: LucideIcon;\n  // K9 (product roles): declared once here so parallel tasks never edit this file\n"
        + "".join(f"  export const {n}: LucideIcon;\n" for n in K9_ICONS)
        + "}\n",
    ),
    (
        "app/src/types/workspace.ts",
        "  | 'composer';\n",
        "  | 'composer'\n  | 'mine'\n  | 'steward';\n",
    ),
    # Integration seams between P2 (owns these views) and P3 (owns App.tsx): the props exist from Phase 0.
    (
        "app/src/hero/HeroSourceView.tsx",
        "  onBack: () => void;\n}\n",
        "  onBack: () => void;\n  /** K9: the creator's \"Your skill\" panel (built by P3), shown at the top of the right column for the owner */\n  ownerSlot?: React.ReactNode;\n}\n",
    ),
    (
        "app/src/hero/HeroSourceView.tsx",
        "function HeroSourceViewInner({ view, onViewChange, onReload, onEnterPractice, onBack }: Props) {",
        "function HeroSourceViewInner({ view, onViewChange, onReload, onEnterPractice, onBack, ownerSlot }: Props) {",
    ),
    (
        "app/src/hero/HeroSourceView.tsx",
        "        <div className=\"space-y-5 min-w-0\">\n          <Panel kicker=\"Knowledge package\"",
        "        <div className=\"space-y-5 min-w-0\">\n          {ownerSlot}\n          <Panel kicker=\"Knowledge package\"",
    ),
    (
        "app/src/hero/universal/UniversalSourceView.tsx",
        "  onBack: () => void;\n}\n",
        "  onBack: () => void;\n  /** K9: the creator's \"Your skill\" panel (built by P3), shown at the top of the right column for the owner */\n  ownerSlot?: React.ReactNode;\n}\n",
    ),
    (
        "app/src/hero/universal/UniversalSourceView.tsx",
        "export function UniversalSourceView({ view, onViewChange, onReload, onEnterPractice, onBack }: Props) {",
        "export function UniversalSourceView({ view, onViewChange, onReload, onEnterPractice, onBack, ownerSlot }: Props) {",
    ),
    (
        "app/src/hero/universal/UniversalSourceView.tsx",
        "        <div className=\"space-y-5 min-w-0\">\n          <Panel kicker=\"Knowledge package\"",
        "        <div className=\"space-y-5 min-w-0\">\n          {ownerSlot}\n          <Panel kicker=\"Knowledge package\"",
    ),
    (
        "app/src/components/DiscoveryView.tsx",
        "  onOpenGuide?: () => void;\n}\n",
        "  onOpenGuide?: () => void;\n  /** K9: open My skills (App.tsx, P3) */\n  onOpenMine?: () => void;\n}\n",
    ),
    (
        "app/src/api/types.ts",
        "} from '../types/contracts';\n",
        "} from '../types/contracts';\nimport type { CaseAccess } from './types-product';\n\nexport * from './types-product';\n",
    ),
    (
        "app/src/api/types.ts",
        "  curated_review_open?: boolean;\n",
        "  curated_review_open?: boolean;\n"
        "  /** the browser may send its own Gemini key (X-Gemini-Api-Key) */\n"
        "  own_key_supported?: boolean;\n"
        "  server_key_configured?: boolean;\n"
        "  /** the steward console exists on this server (an access code is configured, or it is open) */\n"
        "  steward_enabled?: boolean;\n"
        "  /** local development: the steward console needs no access code */\n"
        "  steward_open?: boolean;\n"
        "  /** private skills and uploads are deleted after this many hours (0 = kept) */\n"
        "  data_ttl_hours?: number;\n",
    ),
    (
        "app/src/api/types.ts",
        "  structures?: string[];\n}\n",
        "  structures?: string[];\n  /** library and ownership state for the current visitor (K9) */\n  access?: CaseAccess;\n}\n",
    ),
    (
        "app/src/api/types.ts",
        "  lesson?: Record<string, unknown>;\n}\n",
        "  lesson?: Record<string, unknown>;\n  /** library and ownership state for the current visitor (K9) */\n  access?: CaseAccess;\n}\n",
    ),
    (
        "app/src/api/client.ts",
        "import { getUserKey } from './userKey';\n",
        "import { getUserKey } from './userKey';\nimport { getStewardToken } from './steward';\n",
    ),
    (
        "app/src/api/client.ts",
        "  CaseView,\n  CreateFromDraftEdits,\n",
        "  CaseView,\n  ConsentRow,\n  CreateFromDraftEdits,\n",
    ),
    (
        "app/src/api/client.ts",
        "  HealthResponse,\n  QueryAnswer,\n  ReviewAction,\n  SessionCreated,\n  SessionResult,\n  SessionView,\n} from './types';\n",
        "  HealthResponse,\n  InsightsView,\n  LibraryRecord,\n  QueryAnswer,\n  ReviewAction,\n  SessionCreated,\n  SessionResult,\n  SessionView,\n"
        "  StewardDecision,\n  StewardLibraryRow,\n  StewardOverview,\n  StewardQueueItem,\n  SubmitBody,\n  UsageView,\n} from './types';\n",
    ),
    (
        "app/src/api/client.ts",
        "function toApiError(",
        "/** The steward access code for this tab, if the visitor signed in to the steward console. Header only. */\n"
        "function stewardHeader(): Record<string, string> {\n"
        "  const t = getStewardToken();\n"
        "  return t ? { 'X-Steward-Token': t } : {};\n"
        "}\n\n"
        "function toApiError(",
    ),
    (
        "app/src/api/client.ts",
        "        ...userKeyHeader(),\n      },\n",
        "        ...userKeyHeader(),\n        ...stewardHeader(),\n      },\n",
    ),
    (
        "app/src/api/client.ts",
        "    for (const [k, v] of Object.entries(userKeyHeader())) xhr.setRequestHeader(k, v);\n",
        "    for (const [k, v] of Object.entries({ ...userKeyHeader(), ...stewardHeader() })) xhr.setRequestHeader(k, v);\n",
    ),
    (
        "app/src/api/client.ts",
        "const enc = encodeURIComponent;\n",
        "/** GET a file download (e.g. a JSON export) with the steward header; returns the body as a Blob. */\n"
        "async function requestBlob(path: string): Promise<Blob> {\n"
        "  let res: Response;\n"
        "  try {\n"
        "    res = await fetch(`${API_BASE}${path}`, { headers: { ...stewardHeader() } });\n"
        "  } catch (e) {\n"
        "    throw new ApiError('NETWORK', `Service unreachable at ${API_BASE || window.location.origin}: ${(e as Error).message}`);\n"
        "  }\n"
        "  if (!res.ok) {\n"
        "    let parsed: unknown = null;\n"
        "    try {\n"
        "      parsed = await res.json();\n"
        "    } catch {\n"
        "      parsed = null;\n"
        "    }\n"
        "    throw toApiError(res.status, parsed, `HTTP ${res.status} ${res.statusText}`);\n"
        "  }\n"
        "  return res.blob();\n"
        "}\n\n"
        "const enc = encodeURIComponent;\n",
    ),
    (
        "app/src/api/client.ts",
        "    request<CaseView>('POST', `/api/compose/${enc(draftId)}/create`, edits, o),\n};\n",
        "    request<CaseView>('POST', `/api/compose/${enc(draftId)}/create`, edits, o),\n"
        "\n"
        "  // ---- K9: library (creator) ----\n"
        "  /** GET /api/library/{case_id} (owner or steward) */\n"
        "  getLibraryRecord: (caseId: string, o?: CallOptions) => request<LibraryRecord>('GET', `/api/library/${enc(caseId)}`, undefined, o),\n"
        "  /** POST /api/library/{case_id}/submit: send the visitor's own skill to the steward review queue */\n"
        "  submitToLibrary: (caseId: string, body: SubmitBody, o?: CallOptions) => request<LibraryRecord>('POST', `/api/library/${enc(caseId)}/submit`, body, o),\n"
        "  /** POST /api/library/{case_id}/withdraw: make the visitor's own skill private again */\n"
        "  withdrawFromLibrary: (caseId: string, o?: CallOptions) => request<LibraryRecord>('POST', `/api/library/${enc(caseId)}/withdraw`, {}, o),\n"
        "  /** GET /api/insights/{case_id} (owner or steward): aggregate, anonymous learner outcomes */\n"
        "  getInsights: (caseId: string, o?: CallOptions) => request<InsightsView>('GET', `/api/insights/${enc(caseId)}`, undefined, o),\n"
        "\n"
        "  // ---- K9: steward console (X-Steward-Token) ----\n"
        "  stewardCheck: (o?: CallOptions) => request<{ ok: boolean }>('POST', '/api/steward/check', {}, o),\n"
        "  stewardOverview: (o?: CallOptions) => request<StewardOverview>('GET', '/api/steward/overview', undefined, o),\n"
        "  stewardQueue: (o?: CallOptions) => request<StewardQueueItem[]>('GET', '/api/steward/queue', undefined, o),\n"
        "  stewardLibrary: (o?: CallOptions) => request<StewardLibraryRow[]>('GET', '/api/steward/library', undefined, o),\n"
        "  stewardDecide: (caseId: string, d: StewardDecision, o?: CallOptions) => request<LibraryRecord>('POST', `/api/steward/library/${enc(caseId)}/decide`, d, o),\n"
        "  stewardConsent: (o?: CallOptions) => request<ConsentRow[]>('GET', '/api/steward/consent', undefined, o),\n"
        "  stewardUsage: (o?: CallOptions) => request<UsageView>('GET', '/api/steward/usage', undefined, o),\n"
        "  /** JSON download of the consent and licence ledger */\n"
        "  stewardConsentExport: () => requestBlob('/api/steward/consent/export'),\n"
        "  /** JSON download of one skill's latest reviewed steps and review record (commit it with tools/apply_expert_review.py) */\n"
        "  stewardReviewExport: (caseId: string) => requestBlob(`/api/steward/review-export/${enc(caseId)}`),\n"
        "};\n",
    ),
    (
        "app/src/api/mock.ts",
        "} from './mock/composer';\n",
        "} from './mock/composer';\n"
        "import {\n"
        "  MOCK_STEWARD_CODE,\n"
        "  accessFor,\n"
        "  mockConsent,\n"
        "  mockDecide,\n"
        "  mockInsights,\n"
        "  mockOverview,\n"
        "  mockQueue,\n"
        "  mockStewardLibrary,\n"
        "  mockSubmit,\n"
        "  mockUsage,\n"
        "  mockWithdraw,\n"
        "  recordFor,\n"
        "  requireMockSteward,\n"
        "} from './mock/library';\n"
        "import { getStewardToken } from './steward';\n"
        "import type { ConsentRow, InsightsView, LibraryRecord, StewardDecision, StewardLibraryRow, StewardOverview, StewardQueueItem, SubmitBody, UsageView } from './types';\n",
    ),
    (
        "app/src/api/mock.ts",
        "    return { ok: true, mode: 'recorded', models:",
        "    return { ok: true, mode: 'recorded', own_key_supported: true, server_key_configured: false, steward_enabled: true, steward_open: false, data_ttl_hours: 6, models:",
    ),
    (
        "app/src/api/mock.ts",
        "      structures: v.modality === 'universal' ? ((v.goal.ui_view as { structures?: string[] }).structures ?? []) : undefined,\n    }));\n",
        "      structures: v.modality === 'universal' ? ((v.goal.ui_view as { structures?: string[] }).structures ?? []) : undefined,\n      access: accessFor(v),\n    }));\n",
    ),
    (
        "app/src/api/mock.ts",
        "  async getCase(caseId: string): Promise<CaseView> {\n    await delay(150);\n    return clone(getView(caseId));\n",
        "  async getCase(caseId: string): Promise<CaseView> {\n    await delay(150);\n    return { ...clone(getView(caseId)), access: accessFor(getView(caseId)) };\n",
    ),
    (
        "app/src/api/mock.ts",
        "    const view = composedCaseView(profile, null);\n    cases.set(view.case_id, view);\n    return clone(view);\n  },\n};\n",
        "    const view = composedCaseView(profile, null);\n    cases.set(view.case_id, view);\n    return clone(view);\n  },\n"
        "\n"
        "  // ---- K9: library, insights and steward console (SYNTHETIC mock state) ----\n"
        "  async getLibraryRecord(caseId: string): Promise<LibraryRecord> {\n"
        "    await delay(100);\n"
        "    return clone(recordFor(getView(caseId)));\n"
        "  },\n"
        "  async submitToLibrary(caseId: string, body: SubmitBody): Promise<LibraryRecord> {\n"
        "    await delay(400);\n"
        "    return clone(mockSubmit(getView(caseId), body));\n"
        "  },\n"
        "  async withdrawFromLibrary(caseId: string): Promise<LibraryRecord> {\n"
        "    await delay(300);\n"
        "    return clone(mockWithdraw(getView(caseId)));\n"
        "  },\n"
        "  async getInsights(caseId: string): Promise<InsightsView> {\n"
        "    await delay(200);\n"
        "    return mockInsights(getView(caseId));\n"
        "  },\n"
        "  async stewardCheck(): Promise<{ ok: boolean }> {\n"
        "    await delay(300);\n"
        "    if (getStewardToken() !== MOCK_STEWARD_CODE) throw new ApiError('STEWARD_REQUIRED', 'That access code is not right.', 401);\n"
        "    return { ok: true };\n"
        "  },\n"
        "  async stewardOverview(): Promise<StewardOverview> {\n"
        "    await delay(200);\n"
        "    return mockOverview([...cases.values()]);\n"
        "  },\n"
        "  async stewardQueue(): Promise<StewardQueueItem[]> {\n"
        "    await delay(200);\n"
        "    return mockQueue([...cases.values()]);\n"
        "  },\n"
        "  async stewardLibrary(): Promise<StewardLibraryRow[]> {\n"
        "    await delay(200);\n"
        "    return mockStewardLibrary([...cases.values()]);\n"
        "  },\n"
        "  async stewardDecide(caseId: string, d: StewardDecision): Promise<LibraryRecord> {\n"
        "    await delay(300);\n"
        "    return clone(mockDecide(getView(caseId), d));\n"
        "  },\n"
        "  async stewardConsent(): Promise<ConsentRow[]> {\n"
        "    await delay(200);\n"
        "    return mockConsent([...cases.values()]);\n"
        "  },\n"
        "  async stewardUsage(): Promise<UsageView> {\n"
        "    await delay(200);\n"
        "    return mockUsage();\n"
        "  },\n"
        "  async stewardConsentExport(): Promise<Blob> {\n"
        "    const rows = mockConsent([...cases.values()]);\n"
        "    return new Blob([JSON.stringify({ exported_at: new Date().toISOString(), synthetic_mock: true, skills: rows }, null, 2)], { type: 'application/json' });\n"
        "  },\n"
        "  async stewardReviewExport(caseId: string): Promise<Blob> {\n"
        "    requireMockSteward();\n"
        "    const v = getView(caseId);\n"
        "    return new Blob([JSON.stringify({ case_id: caseId, synthetic_mock: true, review_status: v.review_status, knowledge_package: v.package }, null, 2)], { type: 'application/json' });\n"
        "  },\n"
        "};\n",
    ),
]


def main() -> int:
    types_file = ROOT / "app/src/api/types.ts"
    if not types_file.is_file():
        print("Run this from the repository root (app/src/api/types.ts not found).")
        return 2
    if "export * from './types-product';" in types_file.read_text(encoding="utf-8"):
        print("K9 foundation already applied; nothing to do.")
        return 0

    # Check every anchor before writing anything.
    texts: dict[str, str] = {}
    for rel, anchor, _ in EDITS:
        p = ROOT / rel
        texts.setdefault(rel, p.read_text(encoding="utf-8").replace("\r\n", "\n"))
    problems = []
    staged = dict(texts)
    for rel, anchor, repl in EDITS:
        n = staged[rel].count(anchor)
        if n != 1:
            problems.append(f"{rel}: anchor found {n} times: {anchor[:70]!r}")
            continue
        staged[rel] = staged[rel].replace(anchor, repl, 1)
    if problems:
        print("Phase 0 NOT applied. Fix these anchors (the file changed since the spec was written):")
        for p in problems:
            print("  -", p)
        return 1

    for rel in NEW_FILES:
        dest = ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / rel, dest)
    for rel, text in staged.items():
        (ROOT / rel).write_text(text, encoding="utf-8", newline="\n")
    print(f"K9 foundation applied: {len(NEW_FILES)} new files, {len(EDITS)} edits in {len(staged)} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
