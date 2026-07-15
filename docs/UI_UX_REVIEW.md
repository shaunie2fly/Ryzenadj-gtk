# Ryzenadj-gtk — Deep-Dive UI/UX Review

Review conducted by running the application and screenshotting the Dashboard, Power, Profiles, Settings, and Undervolt pages on a real machine (Ryzen 7 PRO 6850U, KDE Plasma Wayland), combined with a full source-code review of all UI-related modules (`ui.py`, `pages.py`, `widgets.py`, `styles.py`, `main.py`, `monitor.py`, `actions.py`, `params.py`, `ryzen.py`, `system.py`).

## Executive Summary

The app has a **polished visual foundation** — dark theme, glassy cards, gradient hero, animated status indicators, seven accent themes. The information architecture (sidebar + paged content) is sound. However, there are significant UX issues in five areas: **(1) broken/empty dashboard states**, **(2) slider step buttons that don't match value ranges**, **(3) context-insensitive global action bar**, **(4) weak error/empty-state communication**, and **(5) accessibility gaps**. Below I break these down by severity and give concrete, code-level suggestions.

---

## Critical Issues (Broken or Actively Misleading)

### C1. Dashboard shows empty cards with no explanation when telemetry is unavailable

**Observed:** On a machine where `ryzenadj -i` can't read the SMU power metric table (Secure Boot / kernel lockdown / missing `ryzen_smu`), the dashboard renders the three section headers ("Power Envelope", "Electrical Current", "Thermal Status") but the actual metric cards underneath are **hidden via `set_visible(False)`** — leaving large empty gaps with no explanation of why data is missing.

**Root cause:** In `main.py :: _on_initial_load_done` (lines 238–241):

```python
for card in self._dashboard_cards:
    val_key = getattr(card, "_val_key", None)
    visible = val_key in info if val_key else True
    card.set_visible(visible)
```

Cards are hidden silently when their `value_key` isn't in the telemetry dict. The diagnostic banner only fires for Secure Boot/lockdown — not for the general "SMU metric table unavailable" case (which `ryzenadj -i` reports as `Unable to init power metric table: -5`).

**Suggestion:** Instead of hiding cards, show them in a **disabled/skeleton state** with a "—" value and a subtitle explaining why: "Telemetry unavailable — ryzen_smu module not loaded or memory access blocked." Also detect the `Unable to init power metric table` error from `ryzenadj -i` output and show a dedicated diagnostic banner (the infrastructure is already there — just needs a new condition).

### C2. Curve Optimizer sliders show ±100/±10 step buttons on a −30 to +30 range

**Observed:** On the Undervolt page, the Curve Optimizer sliders (`set-coall`, `set-cogfx`, `set-coper-N`) have the same six step buttons as the power sliders: `−100`, `−10`, `−1`, `+1`, `+10`, `+100`. But the CO range is `[-30, +30]`. Clicking `+100` instantly clamps to `+30`; `±10` is too coarse to be useful. This is confusing and makes the step buttons appear broken.

**Root cause:** In `widgets.py :: _build_slider_row` (lines 350–353), the step buttons are hardcoded:

```python
btn_minus_100 = make_step_btn("−100", -1, 100, f"−100 {unit_label}")
btn_minus_10  = make_step_btn("−10",  -1,  10, f"−10 {unit_label}")
btn_plus_10   = make_step_btn("+10",   1,  10, f"+10 {unit_label}")
btn_plus_100  = make_step_btn("+100",  1, 100, f"+100 {unit_label}")
```

**Suggestion:** Make the step button set **range-aware**. For small ranges (like CO's -30 to +30), show only `−1`/`+1` and `−5`/`+5`. For large ranges (power in mW), keep `−100`/`−10`/`−1`/`+1`/`+10`/`+100`. A simple heuristic:

```python
range_size = hi - lo
if range_size <= 60:
    # Small range (Curve Optimizer): show ±1, ±5
    step_configs = [(-1, 5, "−5"), (-1, 1, "−1"), (1, 1, "+1"), (1, 5, "+5")]
else:
    # Large range (power, current, clocks): show ±1, ±10, ±100
    step_configs = [(-1, 100, "−100"), (-1, 10, "−10"), (-1, 1, "−1"),
                    (1, 1, "+1"), (1, 10, "+10"), (1, 100, "+100")]
```

### C3. All sliders show "(Unsupported on this CPU)" when telemetry fails — even supported params

**Observed:** On the Power page, every slider shows "(Unsupported on this CPU)" in red. But these parameters (STAPM, PPT, etc.) **are** supported on the Ryzen 7 6850U — the issue is that `ryzenadj -i` failed to return the supported parameters list because it couldn't access the SMU.

**Root cause:** In `params.py :: is_parameter_supported`, the final fallback for most parameters is:

```python
if supported_params and param in supported_params:
    return True
# ...
return False
```

When `supported_params` is empty (because `ryzenadj -i` failed), **everything** returns `False`, even params that are universally supported on the CPU family. This is a false negative that makes the entire app appear non-functional.

**Suggestion:** When `supported_params` is empty (failed read), don't mark params as unsupported — mark them as **"unknown status"** with a neutral (yellow) indicator instead of red "(Unsupported)". The user can still try to apply settings; ryzenadj will return an error if the param truly isn't supported. At minimum, power/current/thermal limits should be assumed supported on any known Ryzen APU family.

### C4. Dashboard requires domain knowledge to interpret

**Observed:** The dashboard shows 11 streaming metrics with technical acronyms (STAPM, PPT Fast/Slow, TDC VDD/SoC, EDC VDD/SoC, THM, STT). Average users cannot determine at a glance whether their system is running well, whether their tuning is effective, or what to adjust. The data answers "what are the raw sensor values?" but not "is my system healthy?" or "what should I tune?"

**Root cause:** The dashboard (`pages.py :: _build_dashboard_page`) is purely a sensor readout grid. It has color-coded progress bars and a "CAPPED" indicator at 95% of limit, but these signals are buried at the card level — the user must mentally aggregate 11 cards to form a verdict.

**Suggestion:** Add a **System Health summary** at the top of the dashboard that computes a single status verdict from the existing telemetry data:

- **Status pill** with priority logic: 🔴 Thermal Limited > 🟠 Current Limited > 🟡 Power Limited > ⚫ Light Load > 🟢 Optimal
- **Plain-language sentence** explaining the status and what to adjust (e.g., "Power budget is the bottleneck at 18W. Raising STAPM/PPT may improve performance.")
- **Three headline stats**: Temperature (°C), Power Usage (W/% of budget), Headroom (% of capacity unused)

The existing 11-card grid stays below as a "Detailed Metrics" section for enthusiasts. All data needed for the summary is already in `self.current_info` and `self._dashboard_cards` — this is pure presentation logic.

### C5. No safety guidance — beginners can make harmful changes unknowingly ✅ Resolved

**Observed:** The app exposes real hardware-level controls (power limits, VRM currents, voltages, Curve Optimizer) that can cause overheating, system instability, data loss, or reduced hardware lifespan if set incorrectly. Yet a beginner has almost no guidance on what's safe to change:

- Parameter descriptions are technical ("TDC Limit VDD - VRM Current") — they say what a parameter _is_, not what happens if you get it wrong.
- The risk confirmation dialog only fires _after_ the user makes changes, and only for "extreme" values.
- Enthusiast Mode unlocks 250W / 500A limits behind a single toggle.
- There's no revert capability in-session — only "remove from startup" which requires a reboot.
- No stability testing guidance for Curve Optimizer, where instability often appears hours later under specific workloads.

**Why absolute "safe zones" don't work:** Safe ranges depend on hardware the app can't see — cooling solution, VRM quality, chassis thermal design, and silicon quality (the "silicon lottery"). Two identical CPUs have different stable limits. The overclocking community has no universal rules; the only reliable method is iterative testing. Hardcoding green/yellow/red zones would give false confidence and could mislead users into harmful changes. **False safety guidance is worse than no guidance.**

**Suggestion:** Instead of absolute safe-zone coloring, implement six honest, additive safety features:

1. **Plain-language descriptions** (always visible, not hover-gated): Add a second line under each parameter's technical description explaining what it does and the consequences of pushing it too far. Example: STAPM → "The maximum power your CPU can draw continuously. Higher = faster sustained speed but more heat. Too high can overheat laptops with limited cooling."

2. **Relative deviation indicator**: Instead of claiming a value is "safe" or "dangerous," show how far the user has deviated from the current hardware reading (proxy for stock). A subtle badge appears when the change is significant: "⚠ Adjusted from current — test for stability" or "⚠ Major change — verify temperatures under load." This is truthful — it says "you've made a big change" without claiming to know if it's safe.

3. **Revert button** per slider row: A small revert icon next to the existing remove button that resets the slider to the last applied value (`applied_settings`), or to the live hardware reading if never applied. The single biggest confidence-builder — users experiment more freely when they know they can undo.

4. **Stability test reminder**: When the user applies Curve Optimizer or OC changes, the toast or risk dialog includes: "⚠ Test for stability (Prime95, OCCT, or a game loop) — instability may appear hours later under load." Standard practice in the overclocking community.

5. **Improved risk dialog**: The existing risk dialog fires for extreme values but shows a generic warning. Make it per-parameter specific: show each changed setting with a one-line explanation of the risk and a "What to watch for" hint.

6. **Temperature spike warning**: After applying aggressive settings, monitor temperatures in the refresh loop for 30–60 seconds. If temps exceed 90°C post-change, show a toast: "⚠ Temperature elevated after tuning change — consider reverting or improving cooling." The hardware itself is the ground truth — not our guess about safe values.

---

## High-Severity Issues (Significant UX Degradation)

### H1. Global bottom action bar is context-insensitive

**Observed:** The bottom action bar with "Power Saving", "Max Performance", and "Apply Settings" buttons is **always visible** on every page — including Dashboard, Profiles, and Settings.

**Problem:** "Apply Settings" makes no sense on the Dashboard (there's nothing to apply — you haven't changed anything). "Power Saving" / "Max Performance" presets are irrelevant on the Settings page. This wastes vertical space and creates cognitive noise.

**Suggestion:** Make the action bar **page-aware**:

- **Dashboard:** Hide the action bar entirely, or show only the preset buttons (quick actions).
- **Slider pages (Power, Clocks, Current, Thermal, Undervolt):** Show the full action bar.
- **Profiles page:** Hide presets; show only "Apply Settings" if a profile was just loaded.
- **Settings page:** Hide the action bar entirely.

Implementation: connect to the `view_stack`'s `notify::visible-child` signal and toggle `action_bar.set_visible()` based on the page name.

### H2. No way to type a specific value into a slider

**Observed:** Every parameter is adjusted exclusively via slider drag or step buttons. For precision tuning (e.g., setting exactly `25.0W` or CO offset of `-15`), users must carefully drag the slider.

**Suggestion:** Add a **double-click-to-edit** interaction on the "Target:" badge, turning it into a spin button / text entry. Or add a small edit icon next to the target badge. This is especially important for Curve Optimizer where ±1 increments matter.

### H3. No visual indication of unsaved changes

**Observed:** When a user drags a slider, the "Target:" badge updates, but there's no visual indicator at the page or app level that there are **pending unsaved changes**. The "Apply Settings" button doesn't change appearance when there are pending changes vs. when there aren't.

**Suggestion:**

- Change the "Apply Settings" button to a **suggested-action style** (accent color, subtle glow) when there are pending changes, and a **disabled/flat style** when there aren't.
- Add a small dot or badge to the sidebar items that have pending changes (like Git's modified-file indicator).
- Show a "You have unsaved changes" warning if the user tries to close the window with pending changes (via `win.connect("close-request", ...)`).

### H4. Toast timeout is too short for error messages

**Observed:** In `main.py :: _show_toast`, all toasts have a 2-second timeout:

```python
toast.set_timeout(2)
```

Error messages from ryzenadj (which can be multi-line) disappear before the user can read them.

**Suggestion:** Use a longer timeout for errors (5–8 seconds), and add a "Dismiss" button on error toasts:

```python
toast.set_timeout(8 if is_error else 2)
if is_error:
    toast.set_button_label("Dismiss")
    toast.connect("button-clicked", lambda t: t.dismiss())
```

### H5. No "Reset to Default" per-slider — only "Remove from Startup"

**Observed:** The per-row clear button (`edit-clear-symbolic`) has the tooltip "Remove this setting from startup/boot service." This removes the setting from the saved config, but it doesn't reset the slider to the hardware's current value or the default value in the current session.

**Suggestion:** Add a **secondary action** (right-click menu or a small "reset" icon) that resets the slider to the current live hardware value or the parameter default, without removing it from the saved config. The current "remove from startup" behavior should be relabeled or moved to a secondary menu.

---

## Medium-Severity Issues (Polish & Usability)

### M1. Eight sidebar items is too many — consider grouping ✅ Resolved

**Observed:** The sidebar has 8 items: Dashboard, Profiles, Power, Clocks, Current, Thermal, Undervolt, Settings. On smaller screens, this requires scrolling.

**Suggestion:** Consider consolidating:

- Merge **Power**, **Current**, **Thermal**, and **Clocks** into a single **"Tuning"** page with expandable sections (accordion). This reduces the sidebar to 4 items: Dashboard, Tuning, Profiles, Settings.
- Alternatively, use a **two-level sidebar** (categories with expandable sub-items).

**Resolution:** Implemented as **Option F — tabbed sub-navigation** (see `M1_STRATEGY.md` for the full design exploration). The five slider pages are consolidated into a single **Tuning** sidebar entry. Each former page is now a sub-tab inside the Tuning page, driven by a nested `Adw.ViewStack` + `Adw.ViewSwitcherBar` (the standard GNOME Settings sub-navigation pattern). The sidebar now has 4 items (Dashboard, Profiles, Tuning, Settings). All slider row registration, refresh, apply, conflict, preset, and profile logic is unchanged because it operates on the page-agnostic `app._slider_rows` dict.

### M2. No onboarding / first-run guidance

**Observed:** A new user opening the app sees a dashboard with telemetry cards (possibly empty) and a sidebar with technical parameter names. There's no explanation of what STAPM, PPT, TDC, EDC mean, or what values are safe.

**Suggestion:**

- Add a **first-run tour** (3–4 tooltips highlighting key areas) or a "Getting Started" banner on the dashboard.
- Add **tooltips on parameter titles** with plain-language explanations and safe ranges. E.g., hovering "STAPM Limit" could show: "Sustained Power Limit — the long-term power ceiling. Safe range: 15–65W for most laptops."
- Consider linking to the README's safety notes from within the app.

### M3. Slider descriptions are too technical for newcomers

**Observed:** Descriptions like "Sustained Power Limit (STAPM)", "Actual Power Limit (PPT FAST)", "TDC Limit VDD - VRM Current" assume the user knows AMD power management terminology.

**Suggestion:** Add a **plain-language subtitle** or expandable info popover for each parameter. For example:

- STAPM → "The maximum power your CPU can sustain indefinitely. Lower this to reduce heat and battery drain."
- PPT Fast → "The peak power allowed for short bursts. Higher = more boost, more heat."

### M4. Diagnostic banner is hidden when telemetry fails for non-lockdown reasons

**Observed:** The diagnostic banner only appears when Secure Boot or kernel lockdown is detected. But telemetry can also fail because `ryzen_smu` isn't loaded (without Secure Boot), or because `ryzenadj` returned an error.

**Suggestion:** Broaden the diagnostic banner conditions to include:

- `ryzen_smu` module not loaded → "Install `ryzen_smu-dkms-git` for enhanced monitoring"
- `ryzenadj -i` returned non-zero → show the actual error message
- Supported params list is empty → "Could not detect supported parameters. Some sliders may be incorrectly marked as unsupported."

### M5. No light theme support ✅ Resolved

**Observed:** The app forces dark mode in `main.py :: do_activate`:

```python
Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK)
```

Users who prefer light mode have no option.

**Suggestion:** Respect the system theme by default (`Adw.ColorScheme.DEFAULT`), or add a theme toggle in the Settings page (Dark / Light / System). The CSS uses `@window_bg_color` and `@window_fg_color` which adapt automatically — most of the styling should work in light mode already.

**Resolution:** Changed PREFER_DARK to DEFAULT in src/main.py do_activate. The app now follows the system theme (light or dark). All CSS uses libadwaita semantic variables that adapt automatically. No CSS changes needed.

### M6. No keyboard navigation between sidebar pages

**Observed:** F5 refreshes and Ctrl+S applies, but there are no keyboard shortcuts for navigating between pages (e.g., Ctrl+1 for Dashboard, Ctrl+2 for Power, etc.).

**Suggestion:** Add accelerators:

```python
self.set_accels_for_action("app.page-dashboard", ["<Ctrl>1"])
self.set_accels_for_action("app.page-power", ["<Ctrl>2"])
# etc.
```

With corresponding `Gio.SimpleAction` entries that call `self.view_stack.set_visible_child_name(...)`.

### M7. Profiles page lacks edit, duplicate, and import/export

**Observed:** The Profiles page only supports Save (new), Apply, and Delete. There's no way to edit an existing profile's values, duplicate a profile, or import/export profiles for backup or sharing.

**Suggestion:**

- Add an **"Edit"** button that loads the profile's values into the sliders for modification, then re-save.
- Add a **"Duplicate"** option in a popover menu.
- Add **Import/Export** buttons that read/write the `profiles.json` file (or a selected file path).

### M8. Window size and sidebar state not persisted

**Observed:** The window always opens at 1050×780 and the sidebar is always shown. If the user resizes the window or collapses the sidebar, these preferences are lost on restart.

**Suggestion:** Save window size and sidebar state to `ui.json` using `Gio.Settings` or manual JSON persistence. Connect to `win.connect("close-request", ...)` to save the current geometry.

---

## Low-Severity Issues (Polish & Accessibility)

### L1. Low contrast text in several places ✅ Resolved

The CSS uses very low opacity for secondary text:

- `color: alpha(@window_fg_color, 0.45)` for hero subtitles, monitor name labels, step button text
- `color: alpha(@window_fg_color, 0.4)` for unit labels, monitor icons

On a dark background, `0.4–0.45` opacity white text is below WCAG AA contrast ratio (4.5:1). **Suggestion:** Increase to at least `0.6` for text content, keeping `0.4` only for decorative icons.

### L2. No visible focus indicators ✅ Resolved

The CSS doesn't define any `:focus` or `:focus-visible` styles. Keyboard users have no visual indication of which element is focused. **Suggestion:** Add focus styles:

```css
button:focus-visible,
scale:focus-visible {
  outline: 2px solid @accent_bg_color;
  outline-offset: 2px;
}
```

### L3. Step buttons are too small ✅ Resolved

The step buttons have `min-height: 26px` and `min-width: 34px`, which is below the recommended 44×44px touch target. **Suggestion:** Increase to at least `32×32px`, or better `36×36px`.

### L4. Emoji in preset buttons may render inconsistently

The preset buttons use emoji: `"⚡ Power Saving"` and `"🚀 Max Performance"`. Emoji rendering varies across font configurations and may look inconsistent. **Suggestion:** Use GTK symbolic icons instead (`power-profile-power-symbolic`, `power-profile-performance-symbolic`).

### L5. "About" section is duplicated

The About information appears both in the Settings page (bottom section) and in the menu (via `app.about` action). **Suggestion:** Remove the About section from the Settings page and keep only the menu entry (`Adw.AboutDialog`), which is the standard libadwaita pattern.

### L6. No spinner or loading indicator during refresh

When the refresh button is clicked, it's disabled but there's no spinner or progress indication. The user doesn't know when the refresh will complete. **Suggestion:** Use `Adw.Spinner` as the button's icon during refresh, or show a subtle progress bar at the top of the content area.

### L7. Theme menu has no previews

The theme menu (7 accent colors) lists names only ("Ryzen Red", "DLSS Green", etc.) with no color swatches. **Suggestion:** Add a small color dot next to each theme name using `Adw.ActionRow` with a suffix widget.

---

## Positive Aspects (Worth Preserving)

1. **Curve Optimizer design** — Per-core sliders with all-core/iGPU options and conflict detection is well-executed and is the app's standout feature.
2. **Conflict resolution** — Automatically disabling conflicting settings (CO all vs per-core, GFX min/max vs forced) with clear inline messages is excellent.
3. **Sysfs fallback** — The transparent fallback to AMDGPU sysfs for iGPU clock limits, with green "(AMDGPU Sysfs Overdrive - fallback)" annotation, is a smart graceful-degradation pattern.
4. **Sleep/wake restoration** — Re-applying settings after suspend via D-Bus `PrepareForSleep` is a thoughtful reliability feature.
5. **Persistence Guard** — Periodic re-application to counter firmware resets is unique and valuable.
6. **Risk confirmation dialogs** — Warning before risky changes (high power limits, CO changes) is good safety UX.
7. **Visual polish** — The glassy card design, gradient hero, animated bottleneck indicators, and hover effects are aesthetically strong.
8. **Threading model** — All hardware calls are properly threaded with `GLib.idle_add` callbacks, keeping the UI responsive.

---

## Implementation Status

| Priority | Issue                                                       | Effort | Status  |
| -------- | ----------------------------------------------------------- | ------ | ------- |
| 🔴 P0    | C2: Fix CO step buttons (±100 on −30 range)                 | Small  | ✅ Done |
| 🔴 P0    | C3: Don't mark all params unsupported when telemetry fails  | Medium | ✅ Done |
| 🔴 P0    | C1: Show explanation when dashboard cards are empty         | Medium | ✅ Done |
| 🔴 P0    | C4: Dashboard requires domain knowledge to interpret        | Medium | ✅ Done |
| 🔴 P0    | C5: No safety guidance — beginners can make harmful changes | Large  | ✅ Done |
| 🟠 P1    | H1: Make action bar page-aware                              | Small  | ✅ Done |
| 🟠 P1    | H3: Visual indicator for unsaved changes                    | Medium | ✅ Done |
| 🟠 P1    | H4: Longer toast timeout for errors                         | Small  | ✅ Done |
| 🟡 P2    | H2: Allow typing specific values                            | Medium | ✅ Done |
| 🟡 P2    | M2: Onboarding / first-run guidance                         | Medium | ✅ Done |
| 🟡 P2    | M4: Broaden diagnostic banner conditions                    | Small  | ✅ Done |
| 🟢 P3    | M1: Consolidate sidebar items                               | Large  | ✅ Done |
| 🟢 P3    | M5: Light theme support                                     | Small  | ✅ Done |
| 🟢 P3    | L1–L3: Accessibility fixes                                  | Small  | ✅ Done |

### P0 Implementation Details (Completed)

- **C2** (`src/widgets.py`): Step buttons are now generated from `step_buttons_before`/`step_buttons_after` lists, populated based on `range_size = hi - lo`. Ranges ≤100 get ±1/±5; ranges >100 get ±1/±10/±100.
- **C3** (`src/params.py`): Added a `if not supported_params: return True` fallback before the final `return False` in `is_parameter_supported()`, so standard params are assumed supported when detection fails. Family-specific checks (CO, OC, GFX, skin temp) still run first.
- **C1** (`src/main.py`, `src/pages.py`): Dashboard cards are always visible (they show "—" for missing data). The diagnostic banner now also fires when telemetry is unavailable and `ryzen_smu` isn't loaded, with dynamic title/subtitle distinguishing lockdown vs missing-module causes.
- **C4** (`src/pages.py`, `src/monitor.py`, `src/styles.py`): Added a System Health summary card at the top of the dashboard. Computes a priority-based status verdict (🔴 Thermal > 🟠 Current > 🟡 Power > ⚫ Idle > 🟢 Optimal) from the existing telemetry fractions, with a plain-language explanation sentence and three headline stats (temperature, power, headroom). The existing 11-card grid remains below as detailed metrics.

### C5 Implementation Plan (Completed)

Safety guidance for beginners. Deliberately avoids absolute "safe zone" coloring — safe ranges are hardware-dependent (cooling, VRM, silicon lottery) and false safety guidance is worse than no guidance. See `C5_STRATEGY.md` for the full iterative review and enhanced plan.

**Implemented features (9):**

1. **Inherent risk tag per param** (`src/params.py`): Every parameter now carries a `risk` field (`low`/`moderate`/`high`) that is hardware-INDEPENDENT — setting `oc-clk` is always riskier than `stapm-time` regardless of cooling. Displayed as a colour-coded pill next to the parameter title. NOT a safe-zone indicator; the tooltip explicitly states this.

2. **Plain-language descriptions** (`src/params.py`, `src/widgets.py`): Every parameter has a `plain_desc` field — a one-sentence non-technical explanation of what it does and the consequences of pushing it too far. Always visible under the technical description, never hover-gated. Example: STAPM → "The maximum power your CPU can draw continuously (over several minutes). Higher = faster sustained speed but more heat and shorter battery life."

3. **"What to watch for" hints** (`src/params.py`, `src/widgets.py`): Every parameter has a `watch_for` field with a concrete symptom to monitor. Example: STAPM → "Sustained temperatures under load; battery life."

4. **Category-level safety banners** (`src/pages.py`): Each tuning sub-tab (Power, Clocks, Current, Thermal, Undervolt) has a dismissible info banner at the top with category-level guidance. Dismissals persist in `ui_settings["category_banners_dismissed"]`.

5. **Relative deviation indicator** (`src/widgets.py`, `src/styles.py`): A badge appears on each slider row when the value deviates significantly from a reference point (last applied value → live hardware reading). Direction-aware (↑ increase = "verify cooling", ↓ decrease = "expect lower performance"). Curve Optimizer uses absolute offset, not percentage. Never claims a value is safe or unsafe — only flags the magnitude of the change. Two tiers: moderate (≥20% / CO ≥5) and major (≥50% / CO ≥20).

6. **Revert button per slider** (`src/widgets.py`): A revert icon (edit-undo-symbolic) next to the existing remove-from-startup button. Resets the slider to the last applied value, or to the live hardware reading if never applied. Tooltip shows exactly what value will be restored (e.g. "Revert to last applied (25.0 W)").

7. **Revert All button** (`src/actions.py`, `src/ui.py`): A revert-all icon in the action bar that restores every slider to its last applied value in one click. Single biggest confidence-builder — users experiment more freely when they can undo everything at once.

8. **Improved risk dialog** (`src/actions.py`): The apply confirmation dialog now shows each changed parameter with its delta from current (e.g. "25.0 W → 65.0 W (+160%)"), inherent risk tag, and "what to watch for" hint. Response appearance is tiered — DESTRUCTIVE for high-risk params or extreme deltas (>200%), SUGGESTED otherwise. The stability-test reminder (feature 4 from the original plan) is merged into this dialog — it appears when Curve Optimizer or manual overclock parameters are in the diff.

9. **Temperature spike warning** (`src/monitor.py`, `src/actions.py`): After applying settings, a 5-minute monitoring window is set. During this window, each refresh checks for temperature spikes (baseline + 10°C OR absolute >90°C) and for failed hardware reads (a strong instability signal). Each warning fires at most once per apply. The hardware is the ground truth — not our guess about safe values.

10. **Enthusiast mode educational dialog** (`src/actions.py`): The first time a user enables Enthusiast Mode, a one-time educational dialog replaces the previous toast, explaining that the limits exist for desktop chips with heavy-duty cooling and that most laptops cannot safely sustain these values. Persisted in `ui_settings["enthusiast_warned"]`. Subsequent toggles still get a toast.

### P1 Implementation Details (Completed)

- **H1** (`src/ui.py`): The bottom action bar (Power Saving, Max Performance, Apply Settings, Revert All) is now hidden on Dashboard, Profiles, and Settings pages. It only appears on the consolidated Tuning page. Uses a `notify::visible-child` signal handler with a `_SLIDER_PAGES = {"tuning"}` set.

- **H3** (`src/main.py`, `src/widgets.py`, `src/monitor.py`, `src/actions.py`, `src/styles.py`): The Apply button now has two visual states — idle (flat/subdued) when there are no pending changes, and active (accent-colored with shadow glow) when `pending_settings != applied_settings`. Driven by `_update_apply_button_state()` called at every point settings can change (slider drag, apply complete, refresh, profile load).
- **H4** (`src/main.py`): Error toasts now use an 8-second timeout (up from 2s) and include a "Dismiss" button. Success toasts remain at 2 seconds.

### P2 Implementation Details (Completed)

- **H2** (`src/widgets.py`, `src/styles.py`): The "Target:" badge on each slider row is now wrapped in a `Gtk.MenuButton` that opens a popover with a `Gtk.SpinButton`. The SpinButton works in display units (e.g., W instead of mW), so users type natural values. Clicking "Set" converts back to native units and updates the slider. The popover syncs to the current slider value when opened. A CSS hover effect on the badge indicates it's clickable.
- **M2** (`src/main.py`, `src/pages.py`, `src/widgets.py`): Added a `first_run` flag to `ui_settings` (defaults to `True`). On first run, a dismissible welcome banner appears on the dashboard with getting-started guidance (where to start, what Curve Optimizer does, how to use profiles, reminder to test for stability). Also added tooltips to all parameter title labels showing the full name and description on hover.
- **M4** (`src/main.py`): The diagnostic banner now has three detection states: lockdown (Secure Boot / kernel lockdown), missing telemetry (ryzen_smu not loaded), and parameter detection failure (telemetry available but supported_params empty). Each state has a distinct title and subtitle message guiding the user to the fix.

### P3 Implementation Details (M1 + M5 + L1-L3 All Completed)

- **M1** (`src/pages.py`, `src/ui.py`): The five separate sidebar entries (Power, Clocks, Current, Thermal, Undervolt) have been consolidated into a single **Tuning** entry. Each former page becomes a sub-tab driven by a nested `Adw.ViewStack` + `Adw.ViewSwitcherBar` (the standard GNOME Settings sub-navigation pattern). The sidebar now has 4 items (Dashboard, Profiles, Tuning, Settings) instead of 8.
  - `_build_tuning_page()` in `pages.py` builds the consolidated page, reusing `_build_slider_page()` unchanged for each category. Slider rows are still registered in `app._slider_rows`, so refresh / apply / conflict / preset / profile logic is completely unaffected.
  - `_SLIDER_PAGES` in `ui.py` is now `{"tuning"}`; the page-aware action bar shows whenever the tuning page is visible, regardless of which sub-tab is active.
  - The window title's subtitle shows the active sub-tab on the tuning page (e.g. `Power • AMD Ryzen 7 PRO 6850U`) and reverts to just the CPU name on other pages. The nested stack's `notify::visible-child` signal is connected to refresh the subtitle on sub-tab switches.
  - `app.tuning_stack` and `app.tuning_switcher_bar` are exposed for future enhancements (sub-tab persistence, search/filter across categories).
  - See `M1_STRATEGY.md` for the full design rationale (Option F selected over accordion, single long page, hierarchical sidebar, jump links, hybrid grouping, and in-page search).

- **L1–L3** (`src/styles.py`): All three low-severity accessibility issues fixed with CSS-only changes. See `L1_L3_STRATEGY.md` for the full deep-dive audit.
  - **L1 (contrast)**: Bumped 8 text opacity values — `0.4→0.6`, `0.45→0.65`/`0.7`, `0.5→0.65` — for hero subtitle, monitor card names, step button labels, health stat labels, unit labels, idle status pill, and idle apply button. Decorative icons left at `0.4`. All text now meets WCAG AA contrast ratio (4.5:1).
  - **L2 (focus indicators)**: Added `:focus-visible` rules for buttons (2px outline, 2px offset), sliders (`scale:focus-visible trough`), sidebar navigation rows, step/adjustment buttons (3px outline for emphasis), and SpinButton. Uses `@accent_bg_color` for visibility on dark backgrounds. `:focus-visible` (not `:focus`) ensures mouse users don't see rings.
  - **L3 (touch targets)**: Step buttons `34×26px → 36×36px`; adjustment buttons `32×32px → 36×36px`; added `min-width/min-height: 32px` for flat icon buttons (revert, remove). Preset and apply buttons already at 48px.
  - **Bonus (reduced motion)**: Added `@media (prefers-reduced-motion: reduce)` block disabling all animations and transitions for users with vestibular disorders. Note: GTK CSS does NOT support `!important` or `::before`/`::after` pseudo-elements — these were removed during implementation.

- **M5** (completed): Light theme support — changed `Adw.ColorScheme.PREFER_DARK` to `Adw.ColorScheme.DEFAULT` in `src/main.py :: do_activate`. The app now follows the system theme (light or dark). All CSS uses libadwaita semantic variables that adapt automatically. No CSS changes needed.
