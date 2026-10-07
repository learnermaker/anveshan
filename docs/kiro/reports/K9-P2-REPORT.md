# K9-P2 Report

## Done (per screen)

### New components (§3)
- `hero/TrustLine.tsx`: one-sentence trust line with Info icon, crimson for SYNTHETIC
- `hero/StepsList.tsx`: ordered list of claims with Show-me buttons and `pointNumber()` helper
- `hero/WhyThisFeedback.tsx`: `<details>` "Why this feedback?" with source, measured, scoring, AI-wording

### Badges updated (§2)
- `RuntimeClassBadge`: returns null when !DEBUG
- `SourceLabelBadge`: plain SOURCE_LABEL in learner mode (SYNTHETIC→crimson, INTERNET→cyan, others→muted)
- `ReviewBadge`: REVIEW_LABEL / OWN_REVIEW_LABEL; added `own?: boolean` prop
- `VerificationBadge`: observed→null, inferred→"AI's reading" amber, unverified→muted "Not checked"
- `StatusBadge`: uses STATUS_PLAIN in learner mode

### Learn (HeroSourceView + UniversalSourceView) (§4)
- Badge row → TrustLine; Reload, warnings, provenance → DEBUG only
- Plain paragraph "Watch how the source does it…"
- Left: credit line from first source; kicker "Source"
- Right: "What you'll learn" panel with StepsList; Claims panel DEBUG only
- EvidenceQuery: kicker "Ask", "From:", "The source does not say.", point-N buttons, data-plain-exempt answer
- ExpertReview panel → DEBUG only
- UniversalSourceView: "Portfolio" → "All skills", UNIVERSAL/Composed INFERRED badge → DEBUG only, GoalStateSection plain labels

### Practise (HeroPracticeView + UniversalPracticeView) (§5)
- "Start session" → "Start practising" throughout
- Badge row → TrustLine; Learner badge title "Your name for this practice"
- Panel kickers: "First try" / "Second try (the whole task again)"
- Kolam photo note changed to plain language
- Sample picker `<details>` "No materials? Try a sample attempt" with previews and Use button
- `attemptLabel()` used in attempt selector buttons

### Guidance (§6)
- `WithClaimRefs`: strips CLM refs in learner mode (no double spaces)
- `TaskInstructions`: item text wrapped in `data-plain-exempt`, footnote DEBUG only
- `AttemptProgress`: steps "First try / Second try / See what changed"
- `ReviewNote`: uses trustLine(); signature `{ status, runtimeLabel }`

### Results (§7)
- `AttemptResultView`: attemptLabel, WhyThisFeedback per item and DrillCard, plain feedback labels, DEBUG-only criterion_id/RunClass/OriginBadge, check name as first line
- `FirstDivergenceCard`: kicker "Where you first went off track", "What we saw", "Why it matters" (no "source"), DEBUG-only claim spans, WhyThisFeedback added
- `ProgressCurve`: "No progress points to show…", "went off track", "WENT OFF TRACK" SVG label
- `HeroTransmissionView`: TrustLine header, plain wording throughout, attempt 1/2 spans DEBUG, transmission record panel DEBUG only, empty state plain, series labels use attemptLabel

### Library (DiscoveryView) (§8)
- Hero: primary "Start with the Kolam drawing (about 2 minutes)", secondary "Share a skill you know"
- "Featured skills" section (hero+published cases)
- "Shared by the community" section with empty state
- Owned skills → single line with link to My skills; composer teaser (no file input here)
- Synthetic examples collapsed (unchanged)

### How it works (HowItWorks) (§9)
- LABELS glossary updated with plain labels; old technical labels removed
- "Three ways to use Anveshan" section added (Learn / Share / Steward)
- AiRoleNote uses plain words

## Before/After top strings
| Before | After |
|---|---|
| "Start session" | "Start practising" |
| "Attempt 1 (baseline)" | "First try" |
| "Attempt 2 (retry)" | "Second try (the whole task again)" |
| "REVIEW: pending" | "Not yet checked by an expert" |
| "REVIEW: approved" | "Checked by an expert" |
| "Transmission record" | (DEBUG only, not shown to learner) |
| "SATISFIED" | "Met" |
| "UNCERTAIN" | "Couldn't tell" |
| "CITED:" | "From:" |
| "INSUFFICIENT_EVIDENCE" badge | "The source does not say." |

## What is DEBUG-only now
- RuntimeClassBadge, MockBadge (already was), UNIVERSAL badge, warnings list
- Provenance panel, Claims panel with IDs/confidence, ExpertReview panel
- Source caption `{source_id} · {mime}` in UniversalSourceView
- VerificationBadge when state=observed
- criterion_id, required annotation, OriginBadge in AttemptResultView
- `<code>{e.kind}</code>` in events list
- "cites CLM-.." spans in feedback items
- Transmission record panel in HeroTransmissionView
- claim-id spans in FirstDivergenceCard

## Requests for PC
- None: all changes are within P2's ownership files

## Open issues
- None

## Live calls used
0
