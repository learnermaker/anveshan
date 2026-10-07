---
name: anveshan-ux
description: Anveshan's product UX rules: the three roles (learner, creator, steward), what each may see, plain-language copy, honesty labels, progressive disclosure and the visual language. Use before designing, writing or changing any screen, label, empty state, error or dialog in app/src, and when reviewing UI for "does this feel like a product, not an evaluation tool".
---

# Anveshan UX rules

Anveshan is a product for people who want to learn a skill, not a dashboard for evaluating AI. Every screen must make sense to a first-time learner with no technical background. The machinery (claims, confidence, run classes, provenance) stays in the product, but only in the steward's "Details" and behind `?debug=1`.

**Authoritative sources (read the relevant part before a non-trivial change):**
- `docs/kiro/specs/K9-00-PRODUCT-UX.md`: the full brief (roles, IA, copy dictionary, screen briefs). This skill is its working summary; if they disagree, K9-00 wins.
- `docs/product/product-vision.md` §9A and `docs/product/user-journeys.md` Journeys 7–8.
- `app/src/copy/plain.ts`: every plain label as a constant. Until K9 is merged to `main`, it lives at `docs/kiro/specs/K9-P0-files/app/src/copy/plain.ts`.

## 1. Decide who the screen is for

| Role | Reaches it by | Never show them |
|---|---|---|
| **Learner** (default, everyone) | Library → skill → Learn → Practise → Results | claim IDs, confidence, approve/revise/reject, LIVE / RECORDED / DETERMINISTIC, lineage or hashes, criterion IDs, raw warnings, status enums |
| **Creator** (owns the skill via the `anv_vid` cookie; `access.owner`) | My skills (`?view=mine`), the "Your skill" panel on Learn | same as the learner; they edit their own steps in plain words |
| **Steward** (access code, `X-Steward-Token`) | Steward console (`?view=steward`) | nothing hidden, but plain labels first and technical detail inside a "Details" disclosure |

`?debug=1` is a team diagnostic, not a role. Never link to it. If a new panel is technical, gate it with `DEBUG` from `app/src/api/debug.ts`.

## 2. Twelve rules for every screen

1. **One primary action.** Exactly one `btn.primary`; everything else is secondary or a link.
2. **A one-sentence purpose at the top** ("Watch how the source does it, then press Start practising.").
3. **Plain words** (§3). Never show an internal ID, enum or code to learners or creators.
4. **Progressive disclosure.** Basics first; reasons behind "Why this feedback?", "Show me in the source" or "Details". Never hide honesty to simplify.
5. **Honesty labels stay visible, translated.** Use `trustLine()`:
   - SYNTHETIC → "Synthetic example (made up for the demo)";
   - INTERNET_REFERENCE → "From an openly licensed internet source, not a verified expert";
   - INFERRED → "AI's reading";
   - pending review → "Not yet checked by an expert".
6. **Empty states teach**: what will appear, how to make it appear, and a button when there is an action.
7. **Errors say what to do next**: render through `ErrorNote` (`app/src/hero/ui.tsx`). No empty `catch {}`.
8. **Confirm destructive or public actions** (Publish, Send for review, Remove step, Reject, Hide). Steward decisions ask for a note.
9. **Status is always visible**: the creator sees the library status chip plus its help line; the steward sees queue counts.
10. **Accessible by default**: see the `anveshan-a11y` skill.
11. **No new dependencies**: React 18, Tailwind, lucide-react 0.475. Declare each new lucide icon in `app/src/vite-env.d.ts`.
12. **Match the visual language** (§5).

## 3. Copy: say this, not that

| Never on learner/creator surfaces | Say instead |
|---|---|
| CLM-03, claim(s) | "step 3", "steps", "what the source shows" |
| knowledge package | "the skill", "the steps" |
| OBSERVED / INFERRED | `CERTAINTY_PLAIN`: "Seen in the source" / "AI's reading" |
| confidence, conf 0.82 | nothing (steward Details only) |
| REVIEW: pending/approved… | `REVIEW_LABEL` (learner) / `OWN_REVIEW_LABEL` (creator) |
| SATISFIED / PARTIAL / NOT SATISFIED / UNCERTAIN | `STATUS_PLAIN`: "Met" / "Partly met" / "Not met" / "Couldn't tell" |
| criterion, criteria, rubric | "check", "checks" |
| baseline / retry | `attemptLabel(n)`: "First try" / "Second try" |
| session, Start session | "Start practising" |
| divergence, first divergence | "where you first went off track" |
| trajectory | "how your attempt progressed" |
| transmission (record) | "results", "what changed" |
| modality | `MODALITY_PHRASE` |
| provenance, lineage, hashes | one credit line: "Source: <attribution> · <licence>" |
| Expert review · Approve, revise or reject claims | creator: "Check what the AI understood"; steward: "Review" |
| MOCK DATA, technical warnings | nothing (debug only) |

**Allowed words:** AI, AI key, check, step, score, source, licence, steward.

**Data-borne text** (skill titles, step statements, quotes from the source) may contain any word. Wrap its container in `data-plain-exempt` so the plain-language scan skips it. Never use the attribute to hide UI copy.

**Voice:**
- Short sentences, action first.
- Speak to the learner ("you").
- Never blame: "Not met yet. Try keeping the loops closed." rather than "Failed".
- Numbers in words a person would use ("3 of 5 checks met").
- Never claim more than the evidence: an internet source is never "an expert", and validation is "engineering evidence", not proof that people learn.

**"Why this feedback?"** has a fixed order:
1. From the source (cited steps, each with "Show me").
2. What was measured.
3. "Scored by fixed rules from what was measured; the AI never sets a score."
4. If the advice is AI-worded, say so and offer the plain version.

## 4. Information architecture (target)

```
Header:  Anveshan · Library · My skills · (Steward when signed in)   [How it works] [AI key]
         Inside a skill: breadcrumb "Library › <title>" + stepper 1 Learn · 2 Practise · 3 Results
Footer:  "Scores come from fixed rules, never from the AI" · Steward sign-in
Views:   ?view=discovery | source | practice | transmission | composer | mine | steward | evidence
```

Screen-by-screen "what good looks like" is in K9-00 §6. Read the matching subsection before changing a screen.

## 5. Visual language

- **Dark theme only.** Tokens are in `app/tailwind.config.js`:
  - surfaces: `bg-background`, `bg-surface-container(-high)`;
  - text: `text-on-surface`, muted `text-on-surface-variant`;
  - borders: `border-outline`.
- **Colour has meaning; don't use it for decoration:**
  - `cadmium-amber`: primary action and attention;
  - `transmission-emerald`: success / met;
  - `caliper-cyan`: links, info, focus;
  - `divergence-crimson`: problems / not met.
- **Type:** `font-serif` (Playfair) for headings, sans (Plus Jakarta) for body, mono only in steward Details or debug.
- **Primitives first:** use `Panel`, `Badge`, `btn.*`, `ErrorNote`, `Spinner` and `ProgressBar` from `app/src/hero/ui.tsx` before writing new styling.
- **Motion:** only the existing `animate-fade-in`, and nothing that blocks reading.

## 6. Before you finish a UI change

- Who is this for? Does anything from the "never show" column appear?
- Is there one primary button and a one-line purpose?
- Are the empty, loading and error states all written?
- Is every honesty label still visible?
- Run the `anveshan-ui-check` skill (screenshots plus scans) and the `anveshan-a11y` checklist.
