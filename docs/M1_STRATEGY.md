/# M1 Strategy: Consolidate Sidebar Items — Deep Analysis

## 1. Current State

The sidebar has **8 items** via `Adw.ViewSwitcherSidebar` bound to a flat `Adw.ViewStack`:

| # | Page | Icon | Content | Slider count |
|---|---|---|---|---|
| 1 | Dashboard | utilities-system-monitor | Health summary + telemetry cards | 0 |
| 2 | Profiles | user-bookmarks | Save/apply/delete profiles | 0 |
| 3 | Power | battery | STAPM, PPT Fast/Slow/APU, time constants | 6 |
| 4 | Clocks | system-run | GFX clk, OC clk/volt, SoC, FCLK, VCN, LCLK | 14 |
| 5 | Current | thunderbolt | TDC/EDC VDD/SoC/GFX, PSI0/PSI3, CVIP | 11 |
| 6 | Thermal | display-brightness | Tctl, skin temps (APU/dGPU), skin power | 4 |
| 7 | Undervolt | computer | Curve Optimizer (all-core, iGPU, per-core) | 2 + N cores |
| 8 | Settings | preferences-system | Automation, persistence, enthusiast, about, reset | 0 |

Five of the eight items are slider pages built by the same generic function (`_build_slider_page`) with different parameter groups. The other three (Dashboard, Profiles, Settings) are unique layouts.

## 2. Options Explored

Seven approaches were analyzed, each with distinct trade-offs:

### Option A: Accordion with Adw.ExpanderRow
Merge all sliders into one page, each category as a collapsible `Adw.ExpanderRow`.

**Verdict: ❌ Rejected.** Slider rows have complex layouts (step buttons, badges, edit popover, remove button) that don't nest cleanly inside expanders. The result would be cramped and visually broken. `Adw.ExpanderRow.add_row()` expects simple rows, not our multi-widget slider rows.

### Option B: Single long page with section headers
Merge all sliders onto one scrollable page with the existing section header pattern.

**Verdict: ❌ Rejected.** 30+ sliders on one page creates an overwhelming wall of controls. Users can't jump to a category. Scrolling fatigue is severe. No visual hierarchy beyond headers.

### Option C: Custom two-level sidebar (tree/hierarchical)
Build a custom sidebar with expandable category headers using `Gtk.ListBox` instead of `Adw.ViewSwitcherSidebar`.

**Verdict: ❌ Rejected.** `Adw.ViewSwitcherSidebar` is a flat list — it doesn't support nesting. Building a custom hierarchical sidebar is the highest-effort option, requires manually managing page switching, keyboard navigation, and selection state. Significant new code to maintain. Loses the polished libadwaita sidebar styling.

### Option D: Tuning overview page with jump links
Add a new "Tuning" overview page that links to the existing 5 slider pages.

**Verdict: ❌ Rejected.** Doesn't reduce sidebar count — actually increases it to 9. Redundant with the Dashboard's health summary.

### Option E: Hybrid — consolidate by usage frequency
Keep Power and Undervolt as separate pages (most common), merge Thermal + Current + Clocks into "Advanced."

**Verdict: ⚠️ Fallback.** Reduces from 8 to 6 items. The "Advanced" page would still have ~15 sliders. Simpler than Option F but doesn't fully solve the problem. The split between "common" and "advanced" is somewhat arbitrary.

### Option F: Tabbed sub-navigation within a "Tuning" page ✅
Merge all 5 slider pages into one "Tuning" sidebar entry with a nested `Adw.ViewStack` + `Adw.ViewSwitcherBar` for sub-navigation between categories.

**Verdict: ✅ Recommended.** See detailed analysis below.

### Option G: Search/filter within consolidated page
Merge all sliders onto one page with a `Gtk.SearchEntry` to filter by name/description.

**Verdict: ❌ Rejected.** Search requires knowing what to search for — doesn't help browsing/discovery. Doesn't solve the "wall of sliders" problem for users who don't know the parameter names. Adds filter logic complexity. Better as a complement to another approach, not a standalone solution.

## 3. Recommended Approach: Option F — Tabbed Sub-Navigation

### Why this is the best option

| Criterion | Option F performance |
|---|---|
| **Sidebar reduction** | 8 → 4 items (best result) |
| **Category preservation** | Categories preserved as sub-tabs |
| **Scrolling** | No change — each sub-tab shows only its category's sliders |
| **Standard patterns** | Uses `Adw.ViewSwitcherBar` + nested `Adw.ViewStack` — the exact pattern GNOME Settings uses for sub-navigation |
| **Implementation risk** | Low — slider row building/registration is unchanged |
| **Code impact** | Concentrated in `ui.py` (major) + `pages.py` (minor new function) |
| **Keyboard nav** | `Adw.ViewSwitcherBar` supports `Ctrl+Tab` natively |
| **Action bar compatibility** | `_SLIDER_PAGES = {"tuning"}` — action bar shows on tuning page regardless of sub-tab |

### Resulting sidebar

```
┌─────────────────────┐
│  Ryzenadj-gtk       │
│                     │
│  📊 Dashboard       │
│  🔧 Tuning          │  ← NEW (replaces 5 slider pages)
│  ⭐ Profiles        │
│  ⚙️ Settings        │
│                     │
└─────────────────────┘
```

### Resulting tuning page layout

```
┌─────────────────────────────────────────────────────┐
│  [sidebar toggle]  Tuning              [refresh]    │
│                                                     │
│  ┌─ Section Header: Power Limits ──────────────┐   │
│  │  --stapm-limit   [Live: 16.4W]  [Target: ▼] │   │
│  │  [−100][−10][−1] ═══●═══ [+1][+10][+100]    │   │
│  │  --fast-limit    [Live: 25.0W]  [Target: ▼] │   │
│  │  ...                                         │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─ Section Header: Time Constants ────────────┐   │
│  │  ...                                         │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  (scrollable content above)                         │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │ [🔋 Power] [⚙️ Clocks] [⚡ Current] [🌡️ Thermal] [💻 Undervolt] │
│  └──────────────────────────────────────────────┘  │
│  [⚡ Power Saving] [🚀 Max Performance] [Apply]     │
└─────────────────────────────────────────────────────┘
```

The `Adw.ViewSwitcherBar` sits at the bottom of the tuning content area, above the window-level action bar. It shows icons + labels for each category and automatically adapts to width (labels hide on narrow windows).

### Widget hierarchy

```
Adw.OverlaySplitView
├── Sidebar
│   └── Adw.ViewSwitcherSidebar → main view_stack
│       ├── Dashboard
│       ├── Tuning        ← NEW
│       ├── Profiles
│       └── Settings
└── Content (Adw.ToolbarView)
    ├── Header bar (sidebar toggle, title, refresh)
    ├── main view_stack
    │   ├── Dashboard page
    │   ├── Tuning page (Gtk.Box vertical)    ← NEW
    │   │   ├── nested Adw.ViewStack (vexpand=True)
    │   │   │   ├── Power sliders (ScrolledWindow)
    │   │   │   ├── Clocks sliders (ScrolledWindow)
    │   │   │   ├── Current sliders (ScrolledWindow)
    │   │   │   ├── Thermal sliders (ScrolledWindow)
    │   │   │   └── Undervolt sliders (ScrolledWindow)
    │   │   └── Adw.ViewSwitcherBar → nested ViewStack
    │   ├── Profiles page
    │   └── Settings page
    └── Action bar (presets + apply, page-aware)
```

## 4. Detailed Implementation Plan

### Step 1: New `_build_tuning_page` function in `pages.py`

```python
def _build_tuning_page(app) -> Gtk.Box:
    """Build the consolidated tuning page with tabbed sub-navigation."""
    tuning_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    # Nested ViewStack for category sub-pages
    tuning_stack = Adw.ViewStack()

    # Build each category's slider page and add to the nested stack
    # (reuse the existing _build_slider_page function unchanged)

    power_page = _build_slider_page(app, "Power", "battery-symbolic", "tuning-power", [
        ("Power Limits", "STAPM and PPT power envelope...", power_params),
        ("Time Constants", "STAPM and Slow PPT averaging windows...", timing_params),
    ])
    tuning_stack.add_titled_with_icon(power_page, "power", "Power", "battery-symbolic")

    clocks_page = _build_slider_page(app, "Clocks", "system-run-symbolic", "tuning-clocks", [
        ("Clockspeed Limits", "Manual overclock limits...", clocks_params),
    ])
    tuning_stack.add_titled_with_icon(clocks_page, "clocks", "Clocks", "system-run-symbolic")

    # ... same for current, thermal, undervolt

    # ViewSwitcherBar at the bottom for sub-navigation
    switcher_bar = Adw.ViewSwitcherBar()
    switcher_bar.set_stack(tuning_stack)
    switcher_bar.set_reveal(True)

    tuning_box.append(tuning_stack)      # Content (expands)
    tuning_box.append(switcher_bar)      # Tab bar (fixed at bottom)

    # Store references for title updates
    app.tuning_stack = tuning_stack
    app.tuning_switcher_bar = switcher_bar

    return tuning_box
```

**Key point:** `_build_slider_page` is called unchanged. It builds slider rows, registers them in `app._slider_rows`, and returns a `ScrolledWindow`. The only difference is WHERE the returned page goes — into the nested ViewStack instead of the main one.

### Step 2: Update `build_main_window` in `ui.py`

Replace the 5 individual slider page additions with a single tuning page:

```python
# BEFORE (5 separate pages):
power_page = _build_slider_page(app, "Power", ...)
view_stack.add_titled_with_icon(power_page, "power", "Power", "battery-symbolic")
# ... repeat for clocks, current, thermal, undervolt

# AFTER (1 consolidated page):
tuning_page = _build_tuning_page(app)
view_stack.add_titled_with_icon(tuning_page, "tuning", "Tuning", "preferences-system-symbolic")
```

The parameter filtering logic (currently in `ui.py` lines 56–113) moves into `_build_tuning_page` or stays in `ui.py` and is passed as arguments.

### Step 3: Update `_SLIDER_PAGES` for action bar visibility

```python
# BEFORE:
_SLIDER_PAGES = {"power", "clocks", "current", "thermal", "undervolt"}

# AFTER:
_SLIDER_PAGES = {"tuning"}
```

The action bar shows whenever the tuning page is visible, regardless of which sub-tab is active. This is correct — the user can apply settings from any sub-tab.

### Step 4: Update window title logic

The `update_header_title` function needs to show both the page and the active sub-tab:

```python
def update_header_title(stack, _paramspec):
    child = stack.get_visible_child()
    if child:
        title = ""
        subtitle = get_cpu_name()
        if hasattr(child, "get_title"):
            title = child.get_title() or ""
        elif isinstance(child, Gtk.ScrolledWindow) and child.get_name() == "dashboard":
            title = "Dashboard"

        # For the tuning page, include the active sub-tab in the subtitle
        if title == "Tuning" and hasattr(app, "tuning_stack"):
            active_sub = app.tuning_stack.get_visible_child_name()
            if active_sub:
                subtitle = f"{active_sub.title()} • {get_cpu_name()}"

        app.window_title.set_title(title)
        app.window_title.set_subtitle(subtitle)
```

Also connect the nested ViewStack's `notify::visible-child` to update the subtitle when sub-tabs change:

```python
if hasattr(app, "tuning_stack"):
    app.tuning_stack.connect("notify::visible-child",
        lambda *args: update_header_title(view_stack, None))
```

### Step 5: Remove old page references

Any code referencing `"power"`, `"clocks"`, `"current"`, `"thermal"`, or `"undervolt"` as main view_stack page names needs updating. References found:

- `_SLIDER_PAGES` in `ui.py` → updated in Step 3
- Test/verification scripts → disposable, not in the codebase
- The `scrolled.set_name(name)` calls in `_build_slider_page` → these set the name on the ScrolledWindow inside the tuning page; they can stay as-is since they're used for the page's own title, not for main-stack navigation

## 5. Files Changed

| File | Change scope | Risk |
|---|---|---|
| `src/pages.py` | Add `_build_tuning_page()` function (~40 lines) | Low — new function, existing code untouched |
| `src/ui.py` | Replace 5 page additions with 1; update `_SLIDER_PAGES`; update title logic | Medium — structural change to window building |
| `src/main.py` | No changes needed | — |
| `src/widgets.py` | No changes needed | — |
| `src/monitor.py` | No changes needed | — |
| `src/actions.py` | No changes needed | — |
| `src/styles.py` | Optional: minor CSS for ViewSwitcherBar styling | Low |

**Total: ~2 files changed, ~60 lines of new/modified code.** The risk is concentrated in `ui.py` where the window structure changes. The slider row logic, settings persistence, apply flow, conflict resolution, and telemetry refresh are all completely unaffected because they operate on `app._slider_rows` and `app.pending_settings` — both of which are page-agnostic.

## 6. Risk Assessment

### Low risk (won't break)
- **Slider row building** — `_build_slider_row` is called identically; it doesn't know or care which ViewStack its parent page lives in
- **Settings persistence** — `load_settings`/`save_settings` operate on JSON files, not UI structure
- **Apply flow** — `apply_settings` takes a dict of params, not UI references
- **Conflict resolution** — `_update_conflicts` iterates `self._slider_rows`, which is a flat dict
- **Profile management** — `load_profiles`/`save_profiles` and the apply/delete handlers iterate `_slider_rows`
- **Telemetry refresh** — `_update_dashboard_cards`, `_update_health_summary`, `_update_slider_badges` all operate on widget references stored on `app`, not on page structure
- **Persistence guard / sleep restore** — operate on `applied_settings`, not UI

### Medium risk (needs testing)
- **Widget tree depth** — The nested ViewStack adds a layer. Need to verify that `Adw.ViewSwitcherBar` behaves correctly (auto-hides labels on narrow windows, shows on wide)
- **Window title updates** — The subtitle now depends on the nested ViewStack's visible child. Need to verify the signal connection fires correctly
- **Scroll behavior** — Each sub-page is a `ScrolledWindow` inside the nested ViewStack. Need to verify scrolling works correctly when the ViewSwitcherBar is present
- **Initial sub-tab selection** — Need to set a sensible default (probably "power" or "undervolt" since those are most common)

### Mitigation strategy
1. Build the tuning page as a standalone function that can be tested independently
2. Run the existing verification scripts to confirm all slider rows are still registered
3. Test action bar visibility on the tuning page
4. Test sub-tab switching and title updates
5. Verify profile apply works across sub-tabs (apply a profile with Power + Undervolt settings while on the Clocks sub-tab)

## 7. Testing Plan

```
Verification checks:
1. Sidebar has exactly 4 items: Dashboard, Tuning, Profiles, Settings
2. Tuning page shows ViewSwitcherBar with 5 sub-tabs
3. Each sub-tab shows the correct sliders (same as before)
4. All slider rows are registered in app._slider_rows (count matches)
5. Action bar visible on Tuning page, hidden on Dashboard/Profiles/Settings
6. Apply button pending indicator works across sub-tabs
7. Window title shows "Tuning" with active sub-tab in subtitle
8. Profile apply updates sliders on all sub-tabs, not just visible one
9. Scrolling works correctly within each sub-tab
10. Keyboard navigation (Ctrl+Tab) cycles sub-tabs
```

## 8. Migration Path

This is a **non-breaking change** from the user's perspective:
- All settings, profiles, and configurations persist (stored in JSON, not UI)
- The same sliders exist, just organized differently
- The apply/preset/remove flows work identically
- No data migration needed

The only user-visible change is the navigation structure. Users who had muscle memory for "click Power in the sidebar" now need to "click Tuning → Power tab." This is a minor adjustment that the ViewSwitcherBar makes intuitive.

## 9. Future Considerations

### Interaction with C5 (Safety Guidance)
When C5 is implemented (plain-language descriptions, deviation indicators, revert buttons), the slider rows will have more content. The tabbed approach keeps each sub-tab's slider count manageable, so the additional per-row content won't create excessive scrolling.

### Potential search addition (Option G complement)
After consolidation, a search bar could be added to the tuning page that filters sliders across all categories. When the user types "STAPM" or "undervolt," the matching sliders would be shown regardless of which sub-tab is active. This is a natural future enhancement that the tabbed structure supports well — just add a search entry above the nested ViewStack and filter the `_slider_rows` dict.

### Sub-tab persistence
Currently, the app doesn't remember which page you were on. With the tuning page, it would be nice to remember the last active sub-tab (store in `ui_settings["tuning_tab"]`). This is a small addition once the tabbed structure is in place.

## 10. Effort Estimate

| Task | Effort |
|---|---|
| `_build_tuning_page` function | 1 hour |
| Update `ui.py` window building | 1 hour |
| Update title/action bar logic | 30 min |
| Testing and verification | 1 hour |
| CSS polish (optional) | 30 min |
| **Total** | **~4 hours** |

This is marked as "Large" effort in the review, but the actual implementation is moderate because:
- The `_build_slider_page` function is reused unchanged
- The slider row logic is completely untouched
- The standard `Adw.ViewSwitcherBar` pattern does the heavy lifting
- No data migration or backend changes
