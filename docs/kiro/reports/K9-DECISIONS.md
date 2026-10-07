# K9 Build — Decisions and Deviations

This file records K9 build decisions where spec intent was followed but literal text deviated, plus quality deviations noted during review.

---

## P7 — Verification tools (2026-10-07)

### PNG fixture size (SHOULD, review finding #4)

**File:** `app/scripts/fixtures/attempt.png`
**Spec:** "64x64 PNG fixture"
**Actual:** 181-byte 1x1 RGB PNG
**Reason:** A 1x1 PNG is functionally equivalent for upload testing — any valid PNG is accepted by the file input. The size was kept minimal to reduce fixture weight. The file works correctly for all upload-testing purposes.
**Impact:** None on test correctness. The fixture is used only to exercise the file-upload path in `check_roles.mjs`.

---

## P2 — Learner surface (2026-10-07)

### ReviewNote uses trustLine() instead of literal spec text (SHOULD, review finding #2)

**File:** `app/src/hero/Guidance.tsx` — `ReviewNote` component
**Spec:** "The steps come from an openly licensed source and the AI, so treat results as practice feedback, not a certificate."
**Actual:** Calls `trustLine({ runtime_label, review_status })` which adapts the sentence to the source type: internet reference → "From an openly licensed internet source…"; upload → different wording; synthetic → crimson warning.
**Reason:** K9-ORCHESTRATOR.md §8 default 6 ("Spec intent over the spec's literal text when the code has moved") and default 2 ("Plain language for learners wins over completeness"). The `trustLine()` output is accurate for every source type; the literal spec sentence is only accurate for INTERNET_REFERENCE. Using `trustLine()` avoids a honesty issue for other source types.
**Impact:** The wording changes slightly by source type. All variants are honest and plain. The suffix "Treat results as practice feedback, not a certificate." is still present verbatim.

---

### attemptLabel(2) returns "Second try" without the "whole task again" qualifier (SHOULD, review finding #3)

**File:** `app/src/copy/plain.ts` — `attemptLabel(n)` function
**Spec:** The spec maps "Attempt 2 · retry (full task)" → "Second try (the whole task again)" and "Attempt 2 · retry" → "Second try" as two distinct outputs.
**Actual:** `attemptLabel(2)` returns "Second try" for both cases because the function only receives the attempt number, not the retry type.
**Reason:** Hero cases have only full retries; the "whole task again" qualifier is hardcoded correctly in the panel kicker (`kicker={n === 0 ? 'First try' : 'Second try (the whole task again)'}`) which is the most prominent placement. The attempt-selector buttons and ProgressCurve series labels show "Second try" via `attemptLabel(2)`. Since the hero case always does a full retry, this is never misleading.
**Impact:** Attempt selector buttons show "Second try" rather than "Second try (the whole task again)". The panel kicker, which is the primary heading, is correct. The deviation is cosmetic for the current hero-only context.

---
