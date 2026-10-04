---
name: Anveshan Transmission Instrument
colors:
  surface: '#0b0d0e'
  surface-dim: '#070809'
  surface-bright: '#1a1d20'
  surface-container-lowest: '#050607'
  surface-container-low: '#0f1214'
  surface-container: '#14181a'
  surface-container-high: '#1c2124'
  surface-container-highest: '#242a2e'
  on-surface: '#edece8'
  on-surface-variant: '#9ba1a6'
  inverse-surface: '#edece8'
  inverse-on-surface: '#14181a'
  outline: '#2e353b'
  outline-variant: '#1a1e22'
  surface-tint: '#e67e22'
  primary: '#e67e22'
  on-primary: '#08090a'
  primary-container: '#2a1708'
  on-primary-container: '#f8b878'
  secondary: '#10b981'
  on-secondary: '#041d14'
  secondary-container: '#063826'
  on-secondary-container: '#6ee7b7'
  tertiary: '#00e5ff'
  on-tertiary: '#001f24'
  tertiary-container: '#00363d'
  on-tertiary-container: '#80f2ff'
  error: '#f87171'
  on-error: '#450a0a'
  background: '#08090a'
  on-background: '#edece8'
  surface-variant: '#181c1f'
typography:
  display-lg:
    fontFamily: Playfair Display
    fontSize: 56px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Playfair Display
    fontSize: 36px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Playfair Display
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 15px
    fontWeight: '400'
    lineHeight: '1.5'
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: '0.05em'
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '600'
    lineHeight: '1.0'
    letterSpacing: '0.12em'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  max_width: 1440px
  gutter: 24px
  container_padding: 32px
---

# Anveshan Design System — Transmission Workbench

**Aesthetic Identity:** Precision Laboratory Instrument meets Documentary Craft.  
**Core Thesis:** Human expertise is bodily, physical, and temporal. The software interface must treat evidence not as metadata, but as an undeniable physical artifact.

---

## 1. Design Philosophy

Anveshan is not a chatbot and not a corporate dashboard. It is a **living transmission instrument**.

1. **Documentary Restraint over Artificial Flash:** The background is dense obsidian (`#08090a`), dark room optics, and milled aluminum. We reject neon gradients, floating glass bubbles, and "magic AI" sparkles.
2. **Evidence as a First-Class Citizen:** Every claim, feedback note, and score references an observable physical event. If an item cannot be traced to a timestamp or sensory cue, it does not exist in the UI.
3. **Synchronized Comparative Temporality:** The heart of the experience is comparing master demonstration with learner attempt. Time is continuous, scrubbable, and measurable.
4. **Deterministic Authority:** The scoring rubric is explicit, weighted, and unyielding. The AI functions as an acute observer and perceptual annotator, never as an unconstrained grading judge.

---

## 2. Color Palette & Semantic Tokens

- **Deep Obsidian (`#08090a` / `#0b0d0e`):** The primary canvas. Mimics optical calibration rooms, reducing eye fatigue and making video footage and waveforms pop with high contrast.
- **Warm Bone (`#edece8`):** Off-white typography with subtle warmth, mimicking archival print and high-grade technical manuals.
- **Cadmium Amber (`#e67e22` / `#f39c12`):** The telemetry and active claim color. Used for active scrubbing playheads, cue highlights, and expert observation markers.
- **Transmission Emerald (`#10b981`):** The verification color. Reserved strictly for verified passing criteria, positive transmission gain ($\Delta$), and authenticated cryptographic lineage.
- **Caliper Cyan (`#00e5ff`):** Fine technical lines (0.5px), bounding indicators, and angular calipers overlaid on video frames.
- **Divergence Crimson (`#f87171`):** Indicates physical technique deviation or safety violation.

---

## 3. Typographic Hierarchy

- **Authority & Heritage (Serif):** *Playfair Display* (or *Fraunces*). Used for procedure titles, expert quotes, and skill titles. Conveys mastery, tradition, and human knowledge continuity.
- **Telemetry & Tele-Inspection (Monospace):** *JetBrains Mono*. Used for all timecodes (`00:19.2`), criterion IDs (`CRIT-WIPE`), cryptographic hashes, and score deltas (`+5.5 PTS`).
- **Instructional Clarity (Geometric Sans):** *Plus Jakarta Sans*. Clean, legible, high-x-height body text for step explanations and corrective coaching advice.

---

## 4. Key UI Primitives

### 4.1 The Dual-Deck Comparative Scrubber
- Two synchronized video feeds: **Expert Reference** vs. **Learner Attempt** (toggleable between Baseline and Retry).
- Single unified master scrubber timeline below both decks.
- Hotkey / button: **"Jump to First Divergence"** immediately snaps both video playheads to the precise millisecond where the learner's technique differed.

### 4.2 The Sensory Cue Waveform Ribbon
- An audio/video spectrogram ribbon tracking tacit sensory cues:
  - Sound cues (e.g. *Ratchet click 1, 2, 3*)
  - Visual cues (e.g. *Needle settled at zero*)
  - Tactile conditions (e.g. *Unidirectional continuous drag*)
- Clicking any cue badge triggers immediate synchronized playback.

### 4.3 The Rubric Criterion HUD & Morphing Radar
- Displays criteria directly linked to the 8-contract `RubricDefinition`.
- Each criterion card displays:
  - Observable indicator
  - Assigned score vs. max points
  - Status badge: `SATISFIED`, `PARTIALLY_SATISFIED`, `NOT_SATISFIED`, `UNCERTAIN`
  - "Inspect Evidence" button that highlights the relevant video frame.
- **Transmission Gain Polygon:** Dynamically renders the Baseline score footprint expanding into the Retry footprint.

### 4.4 The Living Lineage Drawer
- Accessible via a prominent header trigger.
- Displays the cryptographic lineage DAG:
  - Source Expert $\to$ KnowledgePackage $\to$ Learner Baseline $\to$ Feedback Loop $\to$ Retry $\to$ Transmission Record.
  - Proves the permanent provenance record of the transfer event.

---

## 5. Explicit Anti-Patterns (What We Ban)

1. ❌ **No Chat Bubbles:** Knowledge transmission is not a casual conversational exchange.
2. ❌ **No Purple/Neon "AI Magic" Gradients:** Visual elements must look calibrated and engineered.
3. ❌ **No Arbitrary Scalar Scores:** Never show a raw "85% Skill Score" without criterion-level breakdown.
4. ❌ **No Disconnected Cards:** Every feedback item must visually connect to a rubric criterion and timestamp.
