# Anveshan Visual Evidence & Screenshot Management

This directory contains the canonical visual validation artifacts for the **Anveshan** platform and the Google Cloud AI Builder Cup 2026 submission.

In accordance with [AGENTS.md](file:///c:/Jim/JimCodes/anveshan/AGENTS.md) **Rule 12** (*"Evidence follows claims. Validation claims require a durable evidence artifact"*), all UI claims, visual layouts, and component states must be backed by durable, timestamped screenshots captured through automated Chrome DevTools Protocol (CDP) audits.

---

## Directory Structure

```text
screenshots/
├── README.md                      # Instructions for coding agents and contributors
├── manifest.json                  # Master append-only ledger of all historical audit runs
├── latest/                        # Stable pointers to the most recent verified audit (15 canonical screens)
│   ├── 01_landing_discovery.png
│   ├── 02_source_grounding_kolam.png
│   ├── 03_adaptive_workspace_kolam.png
│   ├── 04_first_divergence_modal.png
│   ├── 05_micropractice_modal.png
│   ├── 06_transmission_complete_kolam.png
│   ├── 07_lineage_dag.png
│   ├── 08_workbench_micrometer.png
│   ├── 09_diagnostic_workspace_bike.png
│   ├── 10_rhythm_workspace_tabla.png
│   ├── 11_state_transition_weaving.png
│   ├── 12_spatial_sequence_origami.png
│   ├── 13_first_divergence_knot.png
│   ├── 14_stitch_canvas_modal.png
│   └── 15_gemini_settings_modal.png
└── runs/
    └── <TIMESTAMP>/               # Immutable run archive (e.g. runs/2026-10-04T12-00-00Z/)
        ├── audit_report.json      # Machine-readable CDP diagnostic metadata
        └── <name>_<TIMESTAMP>.png # 15 timestamped high-resolution captures
```

---

## Canonical Screen Inventory (Chronological Lifecycle Order)

| Screen Identifier | Target View & Capability | Verification Criteria & Key Primitives |
|---|---|---|
| **`01_landing_discovery`** | Stage 00 Capability Portfolio Landing View | Landing headline ("Transmit what matters"), 7 capability archetypes, 3 transmission modes (Forward, Goal-Target, Corrective), end-to-end lifecycle pipeline. |
| **`02_source_grounding_kolam`** | Stage 01 Source & Grounding (Kolam) | Authentic demonstration media, grounded claims, Epistemic Certainty Taxonomy table (`OBSERVED`, `INFERRED`, `UNKNOWN`). |
| **`03_adaptive_workspace_kolam`** | Stage 02 Spatial Practice Canvas (Kolam) | $5 \times 5$ orthogonal pulli dot matrix, continuous Brahma Mudi closed loop, 4-fold rotational symmetry guides, coordinate telemetry. |
| **`04_first_divergence_modal`** | Forensic First Divergence Modal | 6-element breakdown: empirical observation, coordinate locus, Gemini interpretation, rubric criterion, uncertainty boundary, failure consequence. |
| **`05_micropractice_modal`** | Bounded Adaptive Micro-Practice Modal | Interactive convex orbital arc selector, live deterministic rubric recalculation ($0.5 \rightarrow 4.0\text{ pts}$). |
| **`06_transmission_complete_kolam`** | Stage 03 Transmission Event Complete | Verified `+4.3 PTS GAIN`, improved criteria list, immutable SHA-256 Merkle root hash. |
| **`07_lineage_dag`** | Cryptographic Provenance DAG Drawer | Complete 8-contract Merkle graph, raw JSON inspection, cross-contract invariant validation pass. |
| **`08_workbench_micrometer`** | Mechanical Micrometer (Forensic Instrument) | Dual-deck comparative video player, 3.2 kHz ratchet acoustic spikes, vernier needle stabilization, torque clutch limiter, `+5.5 PTS GAIN`. |
| **`09_diagnostic_workspace_bike`** | Diagnostic Workspace (Bicycle Repair) | 4-stage causal decision tree, water bath bubble leak stream, matte cross-hatch vs factory glaze butyl surface microscopy. |
| **`10_rhythm_workspace_tabla`** | Rhythm Practice Instrument (Tabla) | Dual Bayan/Dayan percussion pads, 44.1 kHz PCM audio onset envelope oscillogram, $-48\text{ ms}$ bimanual timing drift. |
| **`11_state_transition_weaving`** | State Transition Workspace (Weaving) | Discrete picks 1–8 matrix, 48mm warp shed aperture gauge, treadle switch sequence, pick #7 float defect. |
| **`12_spatial_sequence_origami`** | Spatial Sequence Workspace (Origami) | 5-step fold timeline, 3D crease polarity vectors (convex mountain ridge $+180^\circ$ vs concave valley trough $-180^\circ$). |
| **`13_first_divergence_knot`** | First-Divergence Workspace (Square Knot) | Cord chirality crossing topology, granny knot vs square knot bights, interactive $0\text{–}25\text{ N}$ tensile slip test slider. |
| **`14_stitch_canvas_modal`** | Google Stitch Generative Canvas Modal | Project `6307547599991476233` reference design canvas (Workbench Screen & Discovery Screen) and design tokens inspection. |
| **`15_gemini_settings_modal`** | Gemini Model Gateway Settings Modal | Execution mode toggle (`REPLAY FIXTURE` vs `GEMINI LIVE API`), `gemini-2.5-flash` / `gemini-2.5-pro` model selector. |

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
