---
name: anveshan-a11y
description: Accessibility checklist for Anveshan's React/Tailwind UI. Covers text size, contrast, icon-only buttons, dialogs, keyboard and focus, 375 px layout, touch targets, motion, media and live regions, with the grep and script commands to check each. Use when building or reviewing any component, dialog or screen in app/src.
---

# Anveshan accessibility checklist

**Target:** WCAG 2.2 AA in practice, for a dark-theme app used on phones. axe-core is **not** installed; do not add it. Use the checks below. Any file you edit must leave this checklist better or equal, never worse.

## 1. Text size

- Body is at least `text-xs` (12 px); labels and chips are at least `text-[11px]`. Never add `text-[8px]`, `text-[9px]` or `text-[10px]`; replace them in files you touch.
- Check:

  ```bash
  grep -rn "text-\[\(8\|9\|10\)px\]" app/src
  ```

  The target is empty (K9-B1 sweeps the rest).
- Don't put important information in uppercase tracking-wide micro-labels only. Pair them with readable text.

## 2. Contrast (dark theme)

- Body text needs **4.5:1**; large text (≥18.66 px bold / 24 px) and UI boundaries need **3:1**.
- **Muted text:** `on-surface-variant` must be at least `#a9afb4` (K9-B1 changes it from `#9ba1a6`) on `surface-container` `#14181a` and `background` `#08090a`.
- **Coloured text:** check it on the actual surface. Amber `#e67e22` and crimson `#f87171` are fine for text on these darks. Never put white text on amber buttons without checking: use dark text on amber.
- **Ratio one-liner** (edit the two hex values):

  ```bash
  node -e "const L=h=>{const c=[1,3,5].map(i=>parseInt(h.slice(i,i+2),16)/255).map(v=>v<=.03928?v/12.92:((v+.055)/1.055)**2.4);return .2126*c[0]+.7152*c[1]+.0722*c[2]};const a=L('#a9afb4'),b=L('#14181a');console.log(((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toFixed(2))"
  ```

- Never convey meaning by colour alone: Met / Not met chips also carry text or an icon.

## 3. Names and roles

- **Icon-only buttons** have `aria-label` (and lucide icons inside get `aria-hidden="true"`). To find candidates, run the command below and inspect those with no text child:

  ```bash
  grep -rn "<button" app/src
  ```

- **Links vs buttons:** use `<button>` for actions and `<a href>` for navigation. No clickable `div`/`span`; if one is unavoidable, add `role="button"`, `tabIndex={0}` and Enter/Space handling.
- **Inputs:** every input has a visible `<label>` (or `aria-label` when the visible label is impossible). Required fields say so in text.
- **Status changes** (upload processing, evaluation done, "Saved") are announced with a polite live region: `role="status"` or `aria-live="polite"`. Errors rendered by `ErrorNote` should use `role="alert"`.

## 4. Dialogs

Every modal has all of the following:
- `role="dialog"`, `aria-modal="true"` and `aria-labelledby` pointing at its heading;
- a visible "Close" button;
- Escape closes it, via the `useEscape` hook (`app/src/hero/useEscape.ts`);
- when it opens, focus moves into the dialog (to the heading or the first field); when it closes, focus returns to the button that opened it;
- the background is not tabbable while open, or at least focus is kept inside the dialog.

**Confirmations** (Remove step, Reject, Hide) are dialogs too, not `window.confirm`.

## 5. Keyboard and focus

- Global focus ring in `app/src/index.css`:

  ```css
  :focus-visible { outline: 2px solid #00e5ff; outline-offset: 2px; }
  ```

  Never use `outline-none` without a visible replacement.
- **Tab order** follows the visual order. The main path (Library → Start → Start practising → submit try → Results) must be completable with Tab, Enter and Space only.
- **Drawing canvas (Kolam):** keyboard users need an alternative, the "upload a photo" path or a sample attempt. Make sure it is reachable and announced.

## 6. Layout at 375 px

- No horizontal page scroll:

  ```js
  document.documentElement.scrollWidth <= 375
  ```

- Fix overflow with `min-w-0`, `flex-wrap`, `break-words`, and `overflow-x-auto` on tables only.
- **Touch targets** are at least 44×44 px for primary actions and at least 24×24 px for everything else (WCAG 2.5.8). Small inline "Show me" links need padding.
- Content reflows at 200 % zoom without loss.

## 7. Motion, media, time

- **Motion:** respect `prefers-reduced-motion` by wrapping new animations in `motion-safe:`. No autoplaying motion over 5 s without a pause control.
- **Video sources** keep native controls. Give audio-only feedback (Tabla) a text equivalent of what was measured.
- **No time limits** on reading feedback or filling forms.

## 8. How to verify

1. Run the greps in §1 and §3.
2. Run the contrast one-liner for any new colour pair.
3. In the preview (`anveshan-ui-check`): Tab through the changed screen and screenshot the focused states; open and close each dialog with the keyboard; check 375 px.
4. Once K9-B1 is merged, run its 375 px mobile check.

Report what you checked and anything left failing. Don't claim "accessible": say which checks pass.
