# C5 — Safety Guidance: Enhanced Strategy

> Iterative review of the original 6-feature C5 plan, with enhancements and implementation order.

## Core Principle (unchanged)

**No absolute "safe zone" coloring.** Safe ranges are hardware-dependent (cooling, VRM quality, silicon lottery). False safety guidance is worse than no guidance. All features below are **honest, additive, and hardware-agnostic**.

## Review of Original Plan

| # | Original feature | Verdict | Enhancement |
|---|---|---|---|
| 1 | Plain-language descriptions | ✅ Keep | Add **risk tag** + **"watch-for" hint** per param; add category-level banners |
| 2 | Relative deviation indicator | ⚠️ Refine | Reference = `applied_settings` (not "current"); direction-aware; CO uses absolute offset not % |
| 3 | Revert button per slider | ✅ Keep | Smart target hierarchy; add **Revert All** in action bar |
| 4 | Stability test reminder | ✅ Keep | **Merge into risk dialog** (features 4+5 belong together) |
| 5 | Improved risk dialog | ✅ Keep | Show **delta from current** + per-param "what to watch for"; tiered response appearance |
| 6 | Temperature spike warning | ⚠️ Refine | Capture **pre-apply baseline**; warn on baseline+10°C OR >90°C; treat failed reads as instability signal |

## New Features Added by Review

| # | Feature | Why |
|---|---|---|
| N1 | **Inherent risk tag** (`low`/`moderate`/`high`) per param | Hardware-independent risk: `oc-clk` is always riskier than `stapm-time`. Foundational — other features reference it. |
| N2 | **Category-level safety banners** on tuning sub-tabs | One-time guidance per category without repeating per-row; complements plain_desc |
| N3 | **Enthusiast mode educational dialog** | Current behavior: a single toast when unlocking 250W. Insufficient — replacing with a one-time dialog explaining consequences |
| N4 | **Revert All button** in action bar | Single biggest confidence-builder; reverts all pending changes to `applied_settings` in one click |

## Deferred (out of scope for this iteration)

- First-time-touch tracking per param (adds state complexity, marginal value over risk dialog)
- Snapshot/undo history (too large for v1)
- Per-row keyboard shortcuts (GTK row-level focus is fragile)

## Inherent Risk Classification

Hardware-**independent**. Reflects "how likely is changing this to cause problems if you don't know what you're doing?"

| Risk | Params | Rationale |
|---|---|---|
| **HIGH** | `oc-clk`, `oc-volt`, `gfx-clk`, `set-coall`, `set-cogfx`, `set-coper-*` | Disables boost, can crash, silent data corruption risk (CO) |
| **MODERATE** | All `*-limit` (power), `vrm-*-current` (TDC/EDC), `tctl-temp`, `apu-skin-temp`, `skin-temp-limit`, all `max-*` clocks | Heat/VRM stress, but hardware protection exists |
| **LOW** | `*-time` (timing constants), `min-*` clocks, `psi*` currents, `vrmcvip-current`, `dgpu-skin-temp`, `prochot-deassertion-ramp` | Slow-acting, secondary rails, or harmless lowering |

Direction matters too: raising power/current/temp is generally riskier than lowering; CO magnitude matters regardless of direction.

## Deviation Indicator Logic

```python
def _compute_deviation(param, pending_value, applied_value, live_value):
    # Reference priority: applied (known good) → live (current) → none
    if applied_value is not None:
        ref, ref_label = applied_value, "last applied"
    elif live_value is not None:
        ref, ref_label = live_value, "current"
    else:
        return None

    # Curve Optimizer: absolute offset, not percentage
    if param.startswith("set-co"):
        mag = abs(pending_value)
        if mag >= 20: return ("major", "co", mag, ref_label)
        if mag >= 5:  return ("moderate", "co", mag, ref_label)
        return None

    # Percentage for everything else
    if ref == 0: return None
    pct = abs(pending_value - ref) / abs(ref) * 100
    if pct >= 50: tier = "major"
    elif pct >= 20: tier = "moderate"
    else: return None
    direction = "up" if pending_value > ref else "down"
    return (tier, direction, pct, ref_label)
```

Direction-aware messaging:
- Power/current/temp **↑ major**: "⚠ Large increase — verify cooling under load"
- Power/current/temp **↓ major**: "Large decrease — expect lower performance"
- **CO major**: "⚠ Large offset — test for stability (may crash hours later)"
- Clocks **↑ major**: "Large clock increase — test for stability"
- Clocks **↓ major**: "Large clock decrease — expect lower performance"

## Improved Risk Dialog

For each changed param, show:
```
STAPM Limit: 25W → 65W (+160%)
  Risk: moderate
  Watch for: sustained temps >90°C under load
```

Stability reminder merged into dialog body (only when CO/OC params in diff):
> ⚠ Test for stability — run a heavy workload (game, video export, benchmark) for 30+ minutes and watch for crashes or freezes. Curve Optimizer instability often appears hours later under specific loads.

Response appearance tiers:
- No high-risk params, all deltas <100%: `Apply` = SUGGESTED
- Any high-risk param OR any delta >200%: `Apply` = DESTRUCTIVE (forces conscious decision)

## Temperature Spike Warning

1. Before `_execute_apply`, snapshot `pre_apply_temp = current_info.get("THM VALUE CORE")`
2. Set `post_apply_monitor_until = now + 300s` (5 minutes — longer than original 60s)
3. In `_on_refresh_done`, if `now < post_apply_monitor_until`:
   - read `temp = current_info.get("THM VALUE CORE")`
   - if `temp > 90` OR (`pre_apply_temp` exists AND `temp > pre_apply_temp + 10`): show toast once
   - if `info` is empty/None (read failed): show toast "Hardware read failed after apply — system may be unstable"

## Implementation Phases

### Phase A — Data layer (`params.py`) — FOUNDATIONAL
- Add `risk`, `plain_desc`, `watch_for` to every entry in `SETTINGS_PARAMS`
- Pure data, no UI risk

### Phase B — Per-row UI (`widgets.py`, `styles.py`)
- Render `plain_desc` (always visible, muted) and `watch_for` (smaller, only if non-empty)
- Add risk pill next to title (`low`/`moderate`/`high` colors — informational, not safe-zone)
- Add **revert button** with smart-target tooltip
- Add **deviation badge** that appears/updates on slider change

### Phase C — Category banners (`pages.py`)
- One dismissible info banner per tuning sub-tab (Power, Clocks, Current, Thermal, Undervolt)
- Persist dismissal in `ui_settings["category_banners_dismissed"]`

### Phase D — Apply flow (`actions.py`, `ui.py`)
- Improved risk dialog with deltas, watch-for, stability reminder, tiered appearance
- **Revert All** button in action bar → reverts all pending to `applied_settings`
- **Enthusiast mode educational dialog** (replaces toast)

### Phase E — Reactive monitoring (`monitor.py`, `actions.py`)
- Pre-apply baseline capture in `_execute_apply`
- Post-apply temp spike + failed-read detection in `_on_refresh_done`

## Verification Plan

For each phase, a programmatic test that:
1. Loads the app, applies phase changes
2. Asserts new fields/widgets exist
3. Triggers deviations, reverts, risk dialogs
4. Confirms no regressions in slider registration / apply flow / conflicts
