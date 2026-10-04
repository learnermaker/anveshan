# Anveshan — Transmission Instrument (Frontend)

The high-precision, documentary-grade UI/UX for **Anveshan**, built for the Google Cloud AI Builder Cup 2026.

## Core Architectural Seam

The frontend consumes the frozen **8-contract shared data seam** defined in `tracks/common/schemas/`:

```text
Track A (Expert Grounding)
  ↓
KnowledgePackage (PKG-OPT-001)
  ↓
RubricDefinition (RUBRIC-OPT-001)
  ↓
PracticeTask (TASK-OPT-001)
  │
  └─────────────── Shared Seam ───────────────┐
                                              ↓
Track B (Evaluation & Transmission)    LearnerAttempt (Baseline & Retry)
                                              ↓
                                         Evaluation (Criterion-Level)
                                              ↓
                                           Feedback (Evidence-Grounded)
                                              ↓
                                      TransmissionRecord (+5.5 pts gain)
```

## Aesthetic Identity

- **Design System:** Precision Laboratory Instrument meets Documentary Craft.
- **Palette:** Darkroom Optics (`#08090a`, `#0b0d0e`), Cadmium Amber (`#e67e22`) telemetry indicators, Transmission Emerald (`#10b981`) verification badges, Caliper Cyan (`#00e5ff`) technical reticles, and Divergence Crimson (`#f87171`) technique warnings.
- **Typography:** Playfair Display (Serif authority), Plus Jakarta Sans (High-clarity geometry), JetBrains Mono (Raw instrumentation telemetry).
- **Design Tokens:** Synchronized with `DESIGN.md` and Google Stitch MCP Project `6307547599991476233` (Screen `dabd99b4d7a24c598259db1dca58ba38`).

## Key Capabilities & Interactions

1. **Dual-Deck Comparative Telemetry:** Side-by-side inspection between a **reference replay fixture** and **learner replay attempt**, with toggleable Baseline vs Retry.
2. **Jump to First Divergence:** One-click snap to the configured replay divergence at `00:19.2` (`CRIT-RATCHET`).
3. **Multi-Modal Sensory Ribbon:** Replay annotations for ratchet clicks, drag duration, and dial-settle observations; physical force remains unmeasured.
4. **8-Contract Rubric HUD:** Criterion-level replay scoring for `CRIT-WIPE`, `CRIT-RATCHET`, and `CRIT-LOCK`, with evidence jumps and model-assisted observation notes.
5. **Deterministic Transmission Gain Hero:** Quantitative progression display showing the configured baseline-to-retry gain and improved criteria; it does not assert mastery or certification.
6. **Provenance / Lineage Inspector:** Interactive replay lineage view showing contract nodes, hashes, parent links, and configured provenance metadata. Cryptographic display is fixture data unless backed by real verification.

## Canonical prototype direction

The current Transmission Instrument is the canonical **forensic workspace** for the micrometer case, not the entire Anveshan product.

The prototype direction now demonstrates multiple source/transmission modes:
- demonstration-first;
- target/image-first;
- attempt/correction-first.

The seven capability cases and adaptive workspace mapping are documented in:
- `docs/research/multimodal-capability-case-portfolio.md`
- `docs/research/source-strategy-and-transmission-modes-2026-10-04.md`
- `docs/status/CANONICAL-SOURCES.md`

Prototype data must distinguish live Gemini results, replay/fixture results, and synthetic/illustrative data.

## Running Locally

```bash
cd app
npm install
npm run dev
```

## Production Build & Verification

```bash
npm run build
npm run audit:devtools
```



> **Replay boundary:** current fixture identities, consent metadata, review state, scores, and provenance displays are engineering fixtures unless explicitly replaced by authorized real evidence.