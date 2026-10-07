# K9-00 — Product, UX and copy rules (read first, every K9 task)

This file is the product brief for K9: three product roles and end-user-centric surfaces. Every K9 task (P1 backend, P2 learner, P3 creator and steward, PC integration) reads it before its own spec.

Source of truth:
- `docs/product/product-vision.md` §9A (roles and the trust layer);
- `docs/product/user-journeys.md` Journeys 7–8 and the 2026-10-07 UX rule;
- `docs/status/DECISIONS.md` (2026-10-07).

If anything here seems to conflict with those, those win. Log the conflict in your report.

---

## 1. What we are building, in one paragraph

Anveshan passes on skills of the physical world: learned from a real demonstration, practised with real hands, and checked against a photo, video or recording of the learner's real attempt ([positioning](../../product/novelty-boundary.md#skills-of-the-physical-world-positioning-decided-2026-10-07)). Before K9, the app shows all its machinery to everyone: claim IDs, confidence numbers, "Approve package" buttons, run classes and lineage hashes. That makes it look like an evaluation tool. K9 makes it a product for three kinds of people:
- **learners** practise;
- **creators** share their own skill and see whether it is being learned;
- **stewards** look after the library.

The machinery stays, as the steward's audit detail and behind `?debug=1` for the team. Learners get it as plain, useful explanations.

## 2. The three roles

| Role | How the demo identifies them | Where they go | What they must never see |
|---|---|---|---|
| **Learner** | Everyone, by default | Library → a skill → Learn → Practise → Results | Claim IDs, confidence numbers, approve/reject/revise controls, run class (LIVE / RECORDED / DETERMINISTIC), lineage or provenance hashes, raw warnings, criterion IDs, technical status codes |
| **Creator** | The visitor who created a skill. The service sets `access.owner = true` from the `anv_vid` cookie; no accounts | **My skills** (`?view=mine`), plus a "Your skill" panel on their own skill's Learn page | The same as the learner, except they edit their own steps in plain words |
| **Steward** | A visitor who entered the steward access code (`X-Steward-Token`). On a local server without a code the console is open | **Steward console** (`?view=steward`) | Nothing is hidden, but the console still uses plain labels first and puts the technical detail in a "Details" disclosure |

**Debug view (not a role):** `?debug=1` keeps today's technical panels for the team. It is never linked from the UI.

## 3. UX principles (apply them to every screen you touch)

1. **One obvious next step.** Each screen has exactly one primary button (`btn.primary`). Everything else is secondary or a link.
2. **Say what it is for, in one sentence, at the top of the screen.** Example: "Watch how the source does it, then press Start practising."
3. **Plain words.** Use the dictionary in §5. Never show an internal ID, enum or code to learners or creators.
4. **Progressive disclosure** (Nielsen Norman Group). Show the basics; put reasons and detail behind "Why this feedback?", "Show me in the source", or a "Details" disclosure. Never hide honesty.
5. **Honesty labels stay visible**, translated:
   - SYNTHETIC → "Synthetic example (made up for the demo)";
   - INTERNET_REFERENCE → "From an openly licensed internet source, not a verified expert";
   - INFERRED → "AI's reading";
   - pending review → "Not yet checked by an expert".

   Use `trustLine()` from `app/src/copy/plain.ts`.
6. **Every empty state teaches.** No blank panels. Say what will appear and how to make it appear, with a button when there is an action. Example: "No one has practised this yet. When learners do, you'll see where they struggle (no names, no recordings)."
7. **Every error says what to do next.** Use the existing `ErrorNote` (it already turns API errors into a title, a message and a fix).
8. **Confirm destructive or public actions:**
   - "Publish" (steward) and "Send for review" (creator) show what will happen;
   - "Remove step", "Reject" and "Hide from library" ask for confirmation and, for steward decisions, a note.
9. **Status is always visible.** The creator always sees their skill's library status (chip and one-line help: `LIBRARY_STATUS_LABEL` / `LIBRARY_STATUS_HELP`). The steward sees counts on the queue tab.
10. **Accessible by default:**
    - text at least 12 px for body and 11 px for labels: do not add new `text-[8px]`, `text-[9px]` or `text-[10px]`; replace any in files you edit;
    - every icon-only button has `aria-label`;
    - dialogs use `role="dialog"`, `aria-modal`, a labelled heading, a visible "Close" and the `useEscape` hook (`app/src/hero/useEscape.ts`);
    - focus stays visible;
    - layout works at 375 px wide with no horizontal scroll.
11. **No new dependencies.** React 18, Tailwind, lucide-react 0.475. Every lucide icon you import must already be declared in `app/src/vite-env.d.ts`; if not, add its declaration line there, copying the existing pattern.
12. **Match the existing visual language.**
    - Use the tokens in `app/tailwind.config.js`: `bg-surface-container`, `border-outline`, `text-on-surface`, `text-on-surface-variant`, `cadmium-amber` for primary or attention, `transmission-emerald` for success, `caliper-cyan` for links and info, `divergence-crimson` for problems.
    - Use the primitives in `app/src/hero/ui.tsx` (`Panel`, `Badge`, `btn.*`, `ErrorNote`, `Spinner`, `ProgressBar`).
    - Headings use `font-serif`.
13. **Speak about the physical world** (added 2026-10-07). Product-level wording (home page, about text) comes from `PITCH`; the page title and description are in `app/index.html` in `app/src/copy/plain.ts`, which adapts the [positioning](../../product/novelty-boundary.md#skills-of-the-physical-world-positioning-decided-2026-10-07). When asking for an attempt, say what to capture in the real world ("Take a photo of your drawing from above", "Film your hands"), not "upload a file". When something cannot be sensed (pressure, force, touch), say so.

## 4. Information architecture (target state after K9)

```
Header:  [Anveshan]  Library · My skills · (Steward, only when signed in)     [How it works] [AI key]
         Inside a skill only: breadcrumb "Library › <skill title>" and the stepper 1 Learn · 2 Practise · 3 Results
Footer:  "Scores come from fixed rules, never from the AI" · "Steward sign-in" link

?view=discovery   Library (default)        Featured skills (curated) · Shared by the community (published) · Synthetic examples (collapsed)
?view=source      Learn                    trust line · source · "What you'll learn" (steps with Show me) · Ask about this skill · [Your skill panel if owner]
?view=practice    Practise                 unchanged flow, plain words
?view=transmission Results                 what changed, plain words, "Why this feedback?"
?view=composer    Share a new skill        the existing composer wizard, plain words
?view=mine        My skills                own skills with status and next action; insights
?view=steward     Steward console          Overview · Review queue · Library · Consent & licences · Usage
```

The case dropdown (`<select>`) in the header becomes the breadcrumb. The select remains only when `DEBUG` is true (P3 owns `Header.tsx`).

## 5. Copy dictionary (learner and creator surfaces)

Import from `app/src/copy/plain.ts` wherever a constant exists; write the others exactly as shown.

| Do not show | Show instead |
|---|---|
| CLM-03, claim, claims | "step 3" / "point 3" (numbered by position in the list), "steps", "what the source shows" |
| knowledge package, package | "the skill", "the steps" |
| OBSERVED / INFERRED badges | `CERTAINTY_PLAIN`: "Seen in the source" / "AI's reading" |
| conf 0.82, confidence | nothing (steward Details only) |
| REVIEW: pending / approved / revised / rejected | `REVIEW_LABEL` (library and learner) or `OWN_REVIEW_LABEL` (creator) |
| INTERNET REFERENCE / UPLOAD / SYNTHETIC / OWNED · CONSENTED | `SOURCE_LABEL`, or the full `trustLine()` |
| LIVE / RECORDED LIVE / DETERMINISTIC | nothing (steward Details and debug only) |
| SATISFIED / PARTIAL / NOT SATISFIED / UNCERTAIN | `STATUS_PLAIN`: "Met" / "Partly met" / "Not met" / "Couldn't tell" |
| criterion, criteria, CRIT-…, rubric | "check", "checks" |
| baseline / retry, Attempt 1 (baseline) | `attemptLabel(n)`: "First try" / "Second try" |
| session, Start session | "Start practising" |
| first divergence, divergence | "where you first went off track" |
| trajectory, progress curve | "how your attempt progressed" |
| transmission, transmission record | "results", "what changed" |
| modality | `MODALITY_PHRASE` ("Draw it on screen or upload a photo"…) |
| provenance, lineage, provenance_hash, DAG | nothing for learners. Credit appears as one line: "Source: <attribution> · <licence>" |
| Expert review · Approve, revise or reject claims | removed from the learner surface. The creator sees "Check what the AI understood"; the steward sees "Review" |
| MOCK DATA | nothing (mock mode is a developer tool) |
| warnings such as "package not expert-approved" | nothing for learners (`trustLine()` already says "not yet checked by an expert"); debug only |

**Why this feedback?** Use this exact disclosure label on every feedback item, the first-off-track card and the drill. Its content, in this order:
1. **From the source:** the statements of the cited steps (`source_claim_ids` → `view.package.claims[].statement`), each with a "Show me" button when it has evidence.
2. **What was measured:** the finding text that already exists (`what_was_observed`, `observed_finding`, metric findings).
3. **How it was scored:** the sentence "Scored by fixed rules from what was measured; the AI never sets a score."
4. **AI-worded advice only (`coaching.status === 'ai_worded'`):** add "The advice was worded by AI from these findings. Show the plain version" (the existing toggle).

**Allowed technical words.** "AI", "AI key", "check", "step", "score", "source", "licence" and "steward" are fine.

**Data-borne text.** Skill titles, step statements and answers quoting the source are authored by people or by the source. They may contain any word. Mark their container with the attribute `data-plain-exempt` so the plain-language scan (PC §3) skips them.

## 6. Role-by-role screen briefs

The P2 and P3 specs give file-level instructions. This section is the "what good looks like" that those instructions implement.

### 6.1 Library (learner)
- **Hero:**
  - one headline;
  - one sentence;
  - primary button "Start with the Kolam drawing (about 2 minutes)";
  - secondary link-button "Share a skill you know" (goes to the composer).
- **How it works:** the existing three steps.
- **Featured skills:** cards for curated skills with `access.library_status === 'published'`. Each card shows:
  - the title;
  - "What you'll do" (`MODALITY_PHRASE`);
  - the trust line, shortened to its first sentence;
  - the check status (`REVIEW_LABEL`);
  - a primary "Start" button.
- **Shared by the community:** published community skills with "Shared by <credit_name>". Empty state: "No community skills yet. Share one you know." with a button to the composer.
- **Synthetic examples:** collapsed, as today.
- **Your own skills:** if the visitor owns skills, show one line "You have N skills in My skills →". Do not list them here.

### 6.2 Learn (learner)
- Title and the trust line (one sentence, muted, with an info icon).
- A one-sentence purpose: "Watch how the source does it, then press Start practising."
- **Source** panel (unchanged media) with a credit line "Source: <attribution> · <licence>".
- **What you'll learn:** a numbered list of the skill's steps and checks (claim statements, in order). Each item:
  - shows its number;
  - shows the plain certainty ("AI's reading" only when inferred; nothing when seen in the source);
  - has a "Show me" button when it has evidence, which focuses the source panel exactly as clicking a claim does today.
- **Ask about this skill** (the existing query form). Cited claims become "point N" buttons; `INSUFFICIENT_EVIDENCE` becomes "The source does not say."
- Primary: "Start practising".
- **If owner:** the "Your skill" panel (P3 component) at the top of the right column.

### 6.3 Practise (learner)
The flow is unchanged: a name is optional, then the first try, the feedback, the second try. Only the wording changes:
- "First try", "Second try";
- "Start practising" instead of "Start session";
- task steps without `[CLM-..]` tags.

### 6.4 Results (learner)
- **Per try:**
  - a plain summary ("3 of 5 checks met");
  - the checks table with Met / Partly met / Not met / Couldn't tell;
  - feedback items with "Why this feedback?";
  - the drill labelled "Practice exercise (not scored)".
- **Results page:**
  - "What changed between your first and second try";
  - the "What to do next" panel (exists);
  - no transmission-record table, which becomes debug-only.

### 6.5 My skills (creator)
- **Top:** "My skills" + primary "Share a new skill".
- **Explanation:** "Skills you create are private to this browser until you publish them. Private skills are kept for about N hours on this demo." N comes from `health.data_ttl_hours`; omit the second sentence when it is 0.
- **One card per owned skill:**
  - title;
  - status chip (`LIBRARY_STATUS_LABEL`) and help line;
  - the steward note when returned or rejected;
  - the next-action button by status (§6.6).
- **Empty state:** "You haven't shared a skill yet. Upload a photo, video or audio of something you know how to do. Anveshan turns it into a practice task with feedback." Button: "Share a new skill".

### 6.6 "Your skill" panel (creator, on their own skill's Learn page)

A three-item checklist:

| # | Item | Done when | Action |
|---|---|---|---|
| 1 | Check what the AI understood | `review_status` is approved or revised | Opens **Check steps**: each step's text with Edit and Remove, then "Looks right" |
| 2 | Try it yourself (optional) | — | Link to Practise |
| 3 | Publish to the library | Status is submitted or published | Opens **Publish**, enabled only when item 1 is done; otherwise shows `submit_blockers` |

**Status-specific actions:**

| Status | Actions |
|---|---|
| submitted | "Withdraw" |
| returned | Shows the steward note; "Fix and send again" (opens Publish) |
| published | "See how learners are doing" (Insights) and "Make private" |
| rejected | Shows the note |

**Check steps dialog:**
- Intro: "These are the steps and checks the AI took from your upload. Learners will practise against them. Fix anything that's wrong."
- Edit saves with `reviewCase(... 'revise_claim', reviewer: 'creator')`.
- Remove asks "Remove this step? Learners will no longer be checked on it." and then calls `reject_claim`.
- "Looks right" calls `approve` with reviewer `'creator'`.

**Publish dialog:** credit name (required), licence (radio from `LICENCE_OPTIONS`, default CC BY 4.0), the fixed text "Who can practise it: anyone using Anveshan", "Are other people identifiable in your photo, video or audio?" (No/Yes; Yes requires "They agreed to it being shared for practice"), "I created this or have the right to share it" (required), an optional note to the steward, and the primary button "Send for review". Under the button: "A steward checks every skill before it appears in the library. You can withdraw it at any time."

### 6.7 Insights (creator and steward; one shared component)
- **Empty state:** "No one has practised this yet. When learners do, you'll see where they struggle (no names, no recordings)."
- **Numbers row:** Learners · Tries · Finished both tries.
- **First try vs second try:** "First try: 29% met every required check → Second try: 60%".
- **Where learners first go wrong:** bars (plain `div` widths) with the check name and count.
- **Hardest checks:** bars with the miss rate.
- **Did the feedback help?** "In 3 of 5 second tries, the check the feedback focused on improved."
- **Suggestions:** a bulleted list. Footnote: "Suggestions follow fixed rules from these numbers. They are not written by AI."
- **When `enough_data` is false:** "Fewer than 3 learners so far: treat these numbers as anecdotes."
- **Always:** "Counts since this demo server last started."

### 6.8 Steward console
- **Not signed in, steward enabled:**
  - one card titled "Steward access";
  - text: "Stewards look after the library: they check skills before they are published, keep credit and consent records, and watch usage.";
  - a code field (password type);
  - "Sign in";
  - a note: "The code stays in this tab only."
- **Not enabled:** "The steward console isn't enabled on this server."
- **`steward_open` (local):** no sign-in; show a small note "Open on this local server".
- **Persistent banner:** "Changes on this demo server are temporary and are lost when it restarts. To keep an expert's review of a featured skill, use Download decisions and commit it."
- **Tabs:**
  - Overview;
  - Review queue (with a count badge);
  - Library;
  - Consent & licences;
  - Usage;
  - plus "Sign out".
- **Overview:**
  - KPI cards: skills in the library, waiting for review, learners today, tries today, AI calls today vs budget, storage used;
  - "Needs your attention" items, each with a button.
- **Review queue → Review detail:**
  - the source media;
  - the steps with full detail: claim ID, type, "Seen in the source" / "AI's reading", confidence and time. Show these in small muted text; they are allowed here;
  - Edit and Remove per step;
  - **For a submission:** "Publish", "Send back to creator" (note required) and "Reject" (note required).
  - **For a featured skill:**
    - "Mark as checked by an expert", which asks for the reviewer's name shown in the record;
    - "Download decisions";
    - "Hide from library" / "Show in library".
- **Library:** a table of skill, collection (Featured / Community), status, checked, learners, last activity and actions (Insights, Hide/Show, Open).
- **Consent & licences:**
  - a table of skill, credit, licence, consent, rights confirmed (date), people in media (No / "Yes, they agreed") and sources (attribution · licence);
  - a "Download record (JSON)" button.
- **Usage:**
  - AI calls today vs budget (a progress bar);
  - calls made with visitors' own keys;
  - repeat calls answered from the cache;
  - blocked requests by type;
  - errors by type;
  - storage used vs cap;
  - "Private data is kept for N hours";
  - server mode;
  - uptime.

## 7. Non-negotiables (from AGENTS.md and 00-COMMON; they still apply)

1. The eight contracts in `tracks/common/schemas/` and their mirror `app/src/types/contracts.ts` are frozen. All new shapes are view types (`app/src/api/types-product.ts`, service JSON).
2. **No model call decides anything new.** Insights, suggestions, library status and permissions are deterministic. No AI wording for insights or suggestions.
3. **Privacy:**
   - insights never contain learner names, session IDs (hash them), media paths or media;
   - the steward sees other visitors' skills only after those skills are submitted. A private skill stays private.
4. **Security:**
   - compare the steward code with `hmac.compare_digest`;
   - rate-limit `/api/steward/check`;
   - never log or echo the code;
   - the client sends it only as the `X-Steward-Token` header.
5. **Honesty:**
   - synthetic stays labelled;
   - internet sources are never called experts;
   - mock data is never presented as real;
   - "temporary on this demo server" is stated wherever durability matters.
6. **No silent failures.** API errors render through `ErrorNote`. Never swallow an error with an empty `catch {}` in new code; the existing silent catch in `UniversalSourceView.doRevise` must be fixed.
7. **Tests never call live APIs.** Use the fakes in `service/tests/conftest.py` and `test_public_demo.py`.
