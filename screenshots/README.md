# Anveshan Visual Evidence & Screenshot Management

This directory contains the canonical visual validation artifacts for the **Anveshan** platform and the Google Cloud AI Builder Cup 2026 submission.

In accordance with [AGENTS.md](file:///c:/Jim/JimCodes/anveshan/AGENTS.md) **Rule 12** (*"Evidence follows claims. Validation claims require a durable evidence artifact"*), all UI claims, visual layouts, and component states must be backed by durable, timestamped screenshots captured through automated Chrome DevTools Protocol (CDP) audits.

---

## Directory Structure

```text
screenshots/
├── README.md                      # Instructions for coding agents and contributors
├── manifest.json                  # Master append-only ledger of all historical audit runs
├── latest/                        # Stable pointers to the most recent verified audit
│   ├── 01_workbench_overview.png
│   ├── 02_lineage_modal.png
│   ├── 03_stitch_canvas_modal.png
│   ├── 04_source_stage_modal.png
│   └── 05_practice_stage_modal.png
└── runs/
    └── <TIMESTAMP>/               # Immutable run archive (e.g. 2026-10-04T11-11-15Z/)
        ├── audit_report.json      # Machine-readable CDP diagnostic metadata
        ├── 01_workbench_overview_<TIMESTAMP>.png
        ├── 02_lineage_modal_<TIMESTAMP>.png
        ├── 03_stitch_canvas_modal_<TIMESTAMP>.png
        ├── 04_source_stage_modal_<TIMESTAMP>.png
        └── 05_practice_stage_modal_<TIMESTAMP>.png
```

---

## Canonical Screen Inventory

| Screen Identifier | Target View & State | Verification Criteria |
|---|---|---|
| **`01_workbench_overview`** | Dual-Deck Player + Sensory Waveform Ribbon + Rubric HUD + Gain Hero Card | Active playhead at `00:19.2`, baseline divergence visible, acoustic spikes mapped, `+5.5 PTS GAIN` displayed. |
| **`02_lineage_modal`** | Cryptographic Provenance DAG Drawer | Complete 8-contract Merkle graph indexed, raw JSON payload visible, `CROSS-CONTRACT INVARIANTS: PASS`. |
| **`03_stitch_canvas_modal`** | Google Stitch Generative Canvas Modal | Project `6307547599991476233` reference canvas displayed, design system match verified. |
| **`04_source_stage_modal`** | Stage 01: Capture & Consent Modal | Elena Rostova 4K macro video preview, expert consent, and peer review records. |
| **`05_practice_stage_modal`** | Stage 03: Practice Task Modal | Marcus Vance trial feed, task execution constraints, and target rubric criteria. |

---

## Instructions for Coding Agents

### Rule 1: Automated Capture Only
**Do not manually upload or commit ad-hoc screenshots.**
All screenshots must be captured programmatically using the Chrome DevTools audit script:
```bash
cd app
npm run audit:devtools
```
or from the repository root:
```bash
npm --prefix app run audit:devtools
```

### Rule 2: Dual-Destination Preservation
When capturing new visual evidence:
1. The script automatically creates an immutable timestamped folder in `runs/<TIMESTAMP>/` containing the timestamped `.png` files and `audit_report.json`.
2. The script copies the images to `latest/<BASE_NAME>.png` without timestamps so that documentation links remain persistent.
3. The script appends the run to `screenshots/manifest.json`.

### Rule 3: Zero-Defect Threshold
A visual audit is only considered **PASS** when:
- Console errors = `0`
- Uncaught exceptions = `0`
- Failed network requests (404/500) = `0`
- All verified images load with `complete: true` and `naturalWidth > 0`

If the audit script exits with code `1`, inspect the console error details in `runs/<TIMESTAMP>/audit_report.json`, resolve the issue in the code, and re-run the audit before committing.

### Rule 4: Linking in PRs and Documentation
- When linking current visuals in documentation (e.g. `README.md`), use `screenshots/latest/<name>.png`.
- When linking validation evidence for a specific PR or milestone release, reference the immutable run: `screenshots/runs/<TIMESTAMP>/<name>_<TIMESTAMP>.png`.
