# L1–L3 Accessibility Enhancements: Deep-Dive Strategy

> Comprehensive audit of the three low-severity accessibility issues, with
> enhancements discovered during the review.

## Core Principle

Accessibility fixes are **CSS-only** — no Python code changes needed. This
makes them low-risk, easy to verify, and impossible to break widget logic.

## L1: Low Contrast — Full Audit

The review mentions two opacity levels but the audit found **9 text elements**
below WCAG AA (4.5:1 contrast ratio on dark backgrounds).

### Text elements to fix

| CSS selector | Current | Target | Rationale |
|---|---|---|---|
| `.hero-subtitle` | `alpha(..., 0.45)` | `0.65` | Hero subtitle text |
| `.monitor-name-label` | `alpha(..., 0.45)` | `0.65` | Card titles like "STAPM LIMIT" |
| `.step-btn` | `alpha(..., 0.45)` | `0.7` | Interactive button labels — needs more |
| `.health-stat-label` | `alpha(..., 0.4)` | `0.6` | Uppercase labels like "TEMPERATURE" |
| `.health-stat-sub` | `alpha(..., 0.4)` | `0.6` | Sub-stat explanation text |
| `.monitor-unit-label` | `alpha(..., 0.4)` | `0.6` | Units like "W", "A", "°C" |
| `.health-status-pill.idle` | `alpha(..., 0.5)` | `0.65` | Idle status pill text |
| `.apply-btn` (idle) | `alpha(..., 0.5)` | `0.65` | Still subdued but readable |

### Elements to leave alone (decorative, not text)

| CSS selector | Current | Why |
|---|---|---|
| `.monitor-icon` | `alpha(..., 0.4)` | Decorative icon, not text content |
| `.navigation-sidebar row image` | `opacity: 0.7` | Decorative sidebar icons |

### C5 elements (already accessible)

The C5 safety guidance elements I added already use 0.6–0.95 opacity, which
is above the WCAG threshold. No changes needed.

## L2: Focus Indicators — Full Audit

The CSS has **zero** `:focus` or `:focus-visible` selectors. Keyboard users
get no visual feedback when tabbing through any interactive element.

### Elements needing focus styles

1. **All buttons** — preset, apply, step, adj, revert, remove, refresh, sidebar
   toggle, menu
2. **Sliders** (`Gtk.Scale`) — the slider handle and/or trough
3. **Sidebar navigation rows** — already get `:selected` for mouse but not
   keyboard focus
4. **SpinButton** — in the target-value popover
5. **Toggle buttons** — enthusiast mode, persistence, etc.

### Design decisions

- Use `:focus-visible` (not `:focus`) — only shows for keyboard navigation,
  not mouse clicks. Avoids visual noise for mouse users.
- Use `@accent_bg_color` for the outline — visible on dark backgrounds.
- 2px outline with 2px offset for standard buttons.
- 3px outline for small step buttons (they're tiny and need more emphasis).
- Don't override existing `:hover`, `:active`, or `:selected` states.
- Use `outline` (not `border`) so it doesn't affect layout.

### CSS

```css
/* Global keyboard focus indicators (L2 accessibility) */
button:focus-visible,
button.text-button:focus-visible,
button.image-button:focus-visible,
button.circular:focus-visible {
    outline: 2px solid @accent_bg_color;
    outline-offset: 2px;
}

/* Sliders — focus the trough so the user can see which slider is active */
scale:focus-visible trough {
    outline: 2px solid @accent_bg_color;
    outline-offset: 2px;
    border-radius: 8px;
}

/* Sidebar rows — keyboard focus distinct from mouse :selected */
.navigation-sidebar row:focus-visible {
    outline: 2px solid @accent_bg_color;
    outline-offset: -2px;
}

/* Step buttons — larger outline since they're small */
.step-btn:focus-visible,
.adj-btn:focus-visible {
    outline: 3px solid @accent_bg_color;
    outline-offset: 1px;
}

/* SpinButton in the target-value popover */
spinbutton:focus-visible {
    outline: 2px solid @accent_bg_color;
    outline-offset: 1px;
}
```

## L3: Touch Target Sizes — Full Audit

### Current sizes

| Element | Current min-size | Target | Rationale |
|---|---|---|---|
| `.step-btn` | 34×26px | 36×36px | Below 44×44 but 36 is practical for 6-button rows |
| `.adj-btn` | 32×32px | 36×36px | Match step buttons for visual consistency |
| `.preset-btn` | 48px height | Already good | Exceeds 44px target |
| `.apply-btn` | 48px height | Already good | Exceeds 44px target |
| Revert/remove buttons | GTK default (~24px) | 32×32px | Add explicit min-size |

### Layout impact check

- Step buttons: 6 buttons × 36px = 216px + slider. On a 1000px clamp, fits.
- Adj buttons: 2 buttons × 36px = 72px. No issue.
- Revert/remove: 2 icon buttons × 32px = 64px. No issue.

## Bonus: Reduced Motion (found during audit)

The CSS has multiple `transition` and `animation` properties with no
`prefers-reduced-motion` guard:

- `.monitor-card:hover` — transform + box-shadow transition
- `.preset-btn:hover` — transform + box-shadow transition
- `.apply-btn.pending:hover` — transform transition
- `.monitor-limit-badge.bottleneck` — `status-pulse` animation (infinite)
- `.slider-row-item` — background-color transition
- `.step-btn`, `.adj-btn` — opacity transition

Users with vestibular disorders need these disabled. One `@media` block:

```css
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}
```

High value, zero risk — motion is decorative, not functional.

## Implementation Plan

All changes are in `src/styles.py` only — no Python code changes.

### Phase A: L1 contrast fixes
- Bump 8 text opacity values (0.4→0.6, 0.45→0.65/0.7, 0.5→0.65)
- Leave decorative icons at 0.4

### Phase B: L2 focus indicators
- Add global `:focus-visible` rules for buttons, scales, sidebar, spinbutton
- Add specific rules for step/adj buttons (3px outline)

### Phase C: L3 touch target sizes
- Step buttons: 34×26 → 36×36
- Adj buttons: 32×32 → 36×36
- Add min-size for revert/remove flat buttons

### Phase D: Reduced motion (bonus)
- Add `@media (prefers-reduced-motion: reduce)` block

## Verification

Programmatic test that:
1. App loads without CSS errors
2. All 45 slider rows still render
3. Step buttons have the new min-size
4. CSS parses cleanly (no GTK CSS warnings in stderr)
5. No regressions in existing layout (sidebar, sub-tabs, action bar)
