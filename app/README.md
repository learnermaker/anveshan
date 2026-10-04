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

1. **Dual-Deck Comparative Telemetry:** Side-by-side inspection of the **micrometer reference fixture** and **learner replay fixture** with toggleable Baseline vs Retry evidence.
2. **Jump to First Divergence:** One-click snap to the fixture's first divergence at `00:19.2` (`CRIT-RATCHET`). This timestamp is replay-fixture data, not a validated real-world observation.
3. **Multi-Modal Sensory Ribbon:** Acoustic waveform impulse peaks for ratchet clicks (18.4s, 18.8s, 19.2s), tactile friction drag duration (4.5s – 12.0s), and dial needle settle zone (26.0s – 31.0s).
4. **8-Contract Rubric HUD:** Criterion-level scoring breakdown for `CRIT-WIPE`, `CRIT-RATCHET`, and `CRIT-LOCK` with direct evidence jumps and Gemini 2.5 Flash observation notes.
5. **Deterministic Transmission Gain Hero:** Quantitative progression display derived from the replay fixture's baseline/retry evaluations. The current `+5.5` gain is synthetic/replay data, not a product validation result.
6. **Lineage DAG:** Interactive provenance inspector over the current contract chain. Fixture hashes/signature labels are illustrative unless a live cryptographic verification path is explicitly connected.

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

## Production Build

```bash
npm run build
```
