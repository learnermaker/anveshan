# K9-P6 Report

## Done

- **§2 LICENSE**: Apache-2.0 downloaded from apache.org; verified "Apache License" and "Version 2.0, January 2004".
- **§3 README.md**: Rewritten top to bottom (141 lines, ≤ 220). No BOM, no mojibake. Sections: title/pitch, Try it, Three roles, How it works, Gen AI table, Evidence, Limits, Run locally, Deploy, Repository map, Licence, Team.
- **§4 judges-panel-review-2026-10-07.md**: Status summary table added (J-01..J-21). Status column added to P0, P1, P2 finding tables. Mojibake fixed throughout file.
- **§5 experiments.md**: E8 (AI coaching wording, guard design, 7 unit tests, browser walk-through) and E9 (BYOK security, 6 BYOK tests, browser test) appended.
- **§6 NEXT-STEPS.md**: "After K9 (2026-10-08)" section added with Jim's remaining 9 steps. Step 4 (licence) marked DONE (K9). D1 (Origami) marked DONE (K9).

## Tests

- `check_governance.py`: PASS
- `Select-String README.md -Pattern "â€\|Ã"`: False (no mojibake)
- `LICENSE` contains "Apache License": True
- Non-live test suite: 480 tests pass (unaffected; this task makes no code changes)

## Deviations

- The judges-panel-review file stored findings in Markdown tables (not separate `###` headings per finding). Status annotations were added as a new `Status (2026-10-08)` column rather than a line under a heading, which is the only Markdown-compatible approach for table rows. Intent fully met.
- Mojibake in the original judges-panel-review file required a full file rewrite rather than incremental str_replace (file was stored in garbled encoding).

## Requests for PC

None.

## Open issues

- J-08: Needs human pilot and expert review. Not a K9 task.
- J-18, J-19: Jim's decisions (screenshots, large modules). Not a K9 task.
- J-20: Python version mismatch between CI and container remains open.

## Review fixes (2026-10-08)

Review verdict was REVISE (1 MUST, 2 SHOULD).

**MUST — README UTF-8 BOM (fixed)**
- `README.md` had a UTF-8 BOM (`EF BB BF`) at offset 0. Stripped by reading raw bytes, decoding as UTF-8, and rewriting with `encoding='utf-8'` (not `utf-8-sig`).
- Verified: `[System.IO.File]::ReadAllBytes('README.md')[0..2]` → `0x23 0x20 0x41` (`# A`). No BOM.
- Verify JSON updated with byte-level BOM check.

**SHOULD — Gen AI table audio model row (fixed)**
- Spec §3.5 lists `vision_fast, audio` for the Perceiving uploads row. The initial README listed only `gemini-3.5-flash-lite`.
- Row updated to: `gemini-3.5-flash-lite; audio model configured separately (disabled by default; set \`ANVESHAN_AUDIO_MODEL\` to enable)`.

**SHOULD — Run locally npm install (no action)**
- Review noted `npm install` before `npm run dev` deviates from CLAUDE.md. Reviewer marked it minor ("No action needed unless the spec intent was to match CLAUDE.md exactly"). Left as-is; it is correct for a fresh clone.

## Live calls used

0
