# Kiro Report — 2026-10-06 ~16:00 IST

## Summary

- Task 1 Media: DONE (1 origami, 4 tabla, 3 kolam — 8 files total; 5 additional kolam items documented with verified URLs but not downloaded due to Wikimedia CDN rate limiting)
- Task 2 Console guide: DONE
- Task 3 Official rules: DONE

---

## 1. Media Candidates

Full table: [docs/kiro/media-candidates.md](media-candidates.md)

### Best picks

**Origami ⭐:** `hk_protesters_crane_fold.webm` — Hong Kong VOA clip (Public Domain), 79.9 s, 25.9 MB. People actively folding traditional cranes. Only PD crane-folding video found outside the existing `OrigamiCrane.ogv`/`Crane.ogv` pair. Not a tutorial, but does show the folding act. Downloaded to `var/kiro/media/origami/`.

**Key finding for Claude Code:** Genuinely independent crane-folding *tutorial* videos with permissive licences do not exist on Wikimedia Commons beyond the two already in the project. The existing `OrigamiCrane.ogv` and `Crane.ogv` are confirmed different recordings of the same performance. The best path for an independent learner video may be for a team member to record one under CC BY.

**Tabla ⭐:** `tabla_chanderi_1.webm` — Man playing tabla, Pranpur village (CC BY-SA 4.0, Manishontop02), 35 s, 7.2 MB. Steady playing. If `tabla_chanderi_1` is the goal, `tabla_chanderi_2` (same uploader, same date, 47 s) is a natural learner-attempt pair — likely the same player/session, so they are paired, not independent. `tabla_yavagal_sample.webm` (Ravindra Yavagal, CC BY 3.0, 8 s) is a genuinely independent player but very short. `tabla_kangutkar.webm` (Vijay Kangutkar, CC BY 3.0, 4m12s) is the richest independent sample (museum context, different tradition).

**Kolam ⭐:** `kolam_8_mayoo.png` — Mayooranathan diagram (Public Domain), 600×599 px, 90 KB. High-contrast black/white pulli kolam, same author as the existing Ithayakkamalam target. Different pattern (dot grid count and topology). `thirukulam_mayoo.png` and `thoddil_mayoo.png` are additional diagram-style kolams.

**Floor photos (not yet downloaded due to CDN 429):** The McKay Savage "India — Kolam" Flickr series (CC BY 2.0) provides 8+ real floor kolam photographs at 3264×2448 px. These are the best "harder cases" for the geometry pipeline. See retry instructions in `media-candidates.md`. URLs and expected sizes are verified via the Wikimedia API.

### Files present in `var/kiro/media/`

| Path | Size | SHA-256 |
|---|---|---|
| origami/hk_protesters_crane_fold.webm | 25,873,856 | 65E8E2896D13B5EA063A38A7F1B68DDF1509131DE10AAD07CE67C1663C34D86B |
| tabla/tabla_chanderi_1.webm | 7,219,730 | 0E0B17B17CC0AFEC6AD043D1006FD41D72E974B1747CF8D65C997B21E665B17B |
| tabla/tabla_chanderi_2.webm | 9,152,801 | 289DF988C2CC1547C9A68B2E3650C23C59C982882CF18177B7A1F8875FBE5BBC |
| tabla/tabla_yavagal_sample.webm | 2,160,563 | 8B1BACC129B3B750917AB29CE0B21D277606BE792FBBC2A9A0F436CA0CF0A285 |
| tabla/tabla_kangutkar.webm | 26,301,519 | 9B7AAEDF0907B202A014EE9C95898324A459C84A76A56D32CEC9B2A66633DF81 |
| kolam/kolam_8_mayoo.png | 90,108 | 74BBD4C4EA8E6394445894A4D5E99884D4038C912ED58FD7C7E1B89E60E68AC6 |
| kolam/thirukulam_mayoo.png | 38,152 | 3CF6E1DEC0A7F0DF332C675FBEF5CDB57148A406E9076ABD21F5C254843998AC |
| kolam/thoddil_mayoo.png | 46,293 | 3C8ECD02BAC23E7B413500078E7FD991378457EB9E32C8AEC6333D73893B046F |

---

## 2. Console Deployment Guide

Full guide: [docs/kiro/cloud-run-console-guide.md](cloud-run-console-guide.md)

**Recommended deploy option:** Option A — Continuous deployment from GitHub via Cloud Build. It uses the repo's own `Dockerfile`, builds automatically on every push to `main`, and gives one-click rollback in the Revisions tab. Cloud Shell (Option B) is the fallback if the GitHub App cannot be installed.

**[VERIFY] items in the guide that Claude Code should confirm:**
- Region dropdown label: `asia-south1 (Mumbai)` — may appear as "Mumbai (asia-south1)"
- "Continuously deploy from a repository" button label may vary slightly between console releases
- Field label for concurrency: "Maximum concurrent requests per instance" vs "Concurrency"
- SA permissions step: confirm whether the Compute Engine default SA is used or a custom SA is configured

**Important note from the Dockerfile:** The build bakes ~50 MB of licensed case media via `tools/fetch_media.py` (sha256-verified). If Cloud Build fails, it will most likely be in this step — a hash mismatch or a Wikimedia CDN 429 error during the build. Check Cloud Build logs for `fetch_media.py` errors specifically.

---

## 3. Official Rules

Full snapshot: [docs/kiro/official-rules-2026-10-06.md](official-rules-2026-10-06.md)

**Top differences from `docs/hackathon/ai-builder-cup.md`:**

1. **Team size mismatch:** Our doc says 1–4 members during build phase. Official site says teams must be 2–4 members by Oct 11 (solo registration is an initial step, not a valid team). Minimum competing team size is 2.

2. **Students not eligible:** "Working professionals only. Students are not eligible." Not mentioned in our doc. Confirm all team members qualify.

3. **Stale submission category text:** The "Category Specification" field on the official page says "(Healthcare, Education, Sustainability, Accessibility, Social Goal)" — this does not match any of the 6 official themes. Use `"Sustainability & Social Impact"` when submitting.

4. **Deadline timezone not stated:** Oct 18, 2026 deadline has no timezone on the official page. Likely 23:59 IST (UTC+5:30) given Hack2skill is based in India. **Confirm before submission.**

5. **No submission portal found:** The official pages have "Register now" buttons that require JavaScript to resolve. Jim should identify the submission platform (likely a Devpost or Hack2skill-hosted form) and record its URL.

6. **Hack2skill is the organiser:** "independently operated by Hack2skill and is not directly administered by Google Cloud." For submission queries, contact Hack2skill, not Google.

---

## Problems / Questions for Claude Code

1. **Origami learner video:** No independent crane-folding tutorial found under a permissive licence. The Hong Kong VOA clip (downloaded) shows crane folding but is a news clip, not a tutorial. Consider having a team member record an independent attempt under CC BY. The hexagonal box videos are a geometry-only fallback (188–344 MB originals; use the 240P transcode URL documented in `media-candidates.md`).

2. **Wikimedia CDN rate limiting:** The CDN returned HTTP 429 after ~7 requests, blocking downloads of 5 kolam items (3 floor photos + 2 small diagrams). All URLs are verified and documented in `media-candidates.md` with SHA-1 hashes from the Wikimedia API. Retry with ≥60 s between requests; use 1000px thumbnail URLs for the large floor photos as suggested by Wikimedia. The floor photos (McKay Savage India—Kolam series, CC BY 2.0) are the most valuable missing items for the harder-case test suite.

3. **Tabla audio extraction:** The tabla downloads are WebM video files (not pure audio). The `tabla_chanderi_1.webm` and `tabla_chanderi_2.webm` are portrait-orientation phone videos. The audio track will need to be extracted (PyAV can do this). Confirm Track A's `onsets.py` handles the WebM container.

4. **Cloud Run build warning:** The `tools/fetch_media.py` step in the Dockerfile fetches ~50 MB of case media from external URLs at build time. If any source URL changes or returns an error, Cloud Build fails. Consider caching these in a GCS bucket as a backup source before the Oct 18 deadline.

5. **Submission portal unknown:** The submission URL was not found. Jim should visit https://aibuildercup.com, click "Register now", and record the portal URL and required form fields here before Oct 15.

6. **GitHub CLI:** gh v2.102.0 was installed on this machine during an earlier session attempt. It is installed but not authenticated. Jim should run `gh auth login` to authenticate (GitHub Desktop credentials do not carry over to the CLI).

---

## Follow-up (2026-10-06 ~16:30 IST)

### Kolam downloads — not completed (persistent CDN block)

All 5 remaining kolam images (3 McKay Savage floor photos + 2 small Mayooranathan diagrams) returned HTTP 429 from Wikimedia's Varnish CDN throughout the follow-up session. The rate limit is IP-level, not request-rate-level — the block persisted across a 2-hour gap, multiple download tools (curl.exe, PowerShell Invoke-WebRequest), and both full-size and thumbnail URL formats.

**Resolution:** Download from a different IP. Quickest path:
1. Open GCP Cloud Shell (already has gcloud, curl, and a Google-owned IP not rate-limited by Wikimedia).
2. Run: `curl -A "AnveshanHackathon/0.1 (research prototype)" -L -o kolam_06.jpg "https://upload.wikimedia.org/wikipedia/commons/9/95/India_-_Kolam_-_06_%282486394060%29.jpg"` with 60 s delays between each file.
3. Copy the downloaded files to `var/kiro/media/kolam/` in the repo.

The exact URLs, expected sizes, and Wikimedia API-verified SHA-1 hashes for all 5 missing files are in `docs/kiro/media-candidates.md`.

### Official rules — deadline time and portal URL found

**Submission portal:** `https://hack2skill.com/event/aibuildercup2026/registration`  
This was found by inspecting the live page with a browser — the "Register now" button leads here. It requires a Hack2skill login. Jim should log in and verify the form fields.

**Deadline time and timezone:** After checking aibuildercup.com, Faqs.html, the Terms & Conditions Google Doc, and all third-party listings, **no specific time or timezone is stated on any official source**. The official text says only "submit it before October 18." Treat this as an end-of-day deadline in the most conservative timezone. **Contact Hack2skill or check the registration confirmation email for the exact cut-off time.**

**Critical new finding — fresh code requirement:** The Terms & Conditions and FAQ both state that only code created after the official program launch (7 September 2026) is eligible. Pre-existing work disqualifies the entire team. Anveshan must have been started on or after that date. Verify before submission.

**Terms & Conditions URL** (newly found, not in original rules snapshot):  
`https://docs.google.com/document/d/e/2PACX-1vRm7ChZ6Ij9fG7uFDkxzUMpwgVeBmnQ6cMDnAIEEX84AiLBOOQ9cYbl3S5OzFBbcVb8TF55s-eVpiXb/pub`

Full updates in `docs/kiro/official-rules-2026-10-06.md`.
