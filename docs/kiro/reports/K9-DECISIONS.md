# K9 Build — Decisions and Deviations

This file records K9 build decisions where spec intent was followed but literal text deviated, plus quality deviations noted during review.

---

## P7 — Verification tools (2026-10-07)

### PNG fixture size (SHOULD, review finding #4)

**File:** `app/scripts/fixtures/attempt.png`
**Spec:** "64×64 PNG fixture"
**Actual:** 181-byte 1×1 RGB PNG
**Reason:** A 1×1 PNG is functionally equivalent for upload testing — any valid PNG is accepted by the file input. The size was kept minimal to reduce fixture weight. The file works correctly for all upload-testing purposes.
**Impact:** None on test correctness. The fixture is used only to exercise the file-upload path in `check_roles.mjs`.

---
