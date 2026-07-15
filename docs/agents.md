# agents.md — Ryzenadj-gtk

A guide for AI agents (and humans) working in this codebase. Documents the architecture, key modules, non-obvious behaviors, and gotchas worth knowing before making changes.

## Project Overview

**Ryzenadj-gtk** is a GTK4 / libadwaita graphical front-end for the [`ryzenadj`](https://github.com/flygoat/ryzenadj) CLI tool. It exposes AMD Ryzen power, current, thermal, clock, and Curve Optimizer tuning through a polished UI, and adds several features ryzenadj itself doesn't provide (profiles, AC/battery automation, persistence guard, sleep/wake restoration, sysfs fallback for iGPU clocks).

- **Language:** Python 3.11+ (no build step — pure modules shipped to `/usr/share/ryzenadj-gtk`)
- **UI toolkit:** GTK 4 + libadwaita (via PyGObject `gi`)
- **Packaging:** Arch `PKGBUILD` for AUR + distro-agnostic `install.sh`
- **License:** GPL-3.0
- **App ID:** `com.marley.ryzenadj-gtk`
- **Current version:** `1.8.4` (defined in `src/main.py` as `APP_VER`, mirrored in `PKGBUILD` / `.SRCINFO` / `src/pages.py` fallback)

## Repository Layout

````
:```
Ryzenadj-gtk/
├── src/                              # All Python source (installed to /usr/share/ryzenadj-gtk)
│   ├── app.py                        # Entry point — bootstrap + xdg-desktop-portal auto-fix
│   ├── init_gi.py                    # PyGObject version requirements (Gtk 4, Gdk 4, Adw 1)
│   ├── main.py                       # RyzenadjApp (Adw.Application) — coordinator class
│   ├── ryzen.py                      # Backend facade — re-exports + ryzenadj CLI wrapping
│   ├── settings.py                   # JSON persistence + systemd service + sudo elevation
│   ├── system.py                     # Sysfs reads (power, clocks, lockdown) + AMDGPU writes
│   ├── params.py                     # SETTINGS_PARAMS table + CPU capability detection + safety metadata
│   ├── monitor.py                    # MonitorMixin — background refresh + sleep/wake + AC swap + post-apply monitoring
│   ├── actions.py                    # ActionsMixin — apply/preset/startup/reset/enthusiast/revert-all/risk-dialog
│   ├── pages.py                      # Window pages (dashboard, tuning sub-tabs, settings, profiles, errors)
│   ├── widgets.py                    # Reusable widgets: slider rows, monitor cards, formatters, deviation helpers
│   ├── ui.py                         # Main window assembly + menu + theme menu + action bar
│   ├── styles.py                     # Application CSS as a Python string (includes accessibility styles)
│   └── assets/                       # Icons, logo, demo gif stills
├── docs/                             # All project documentation
│   ├── agents.md                    # This file — architecture guide for agents
│   ├── UI_UX_REVIEW.md              # UI/UX review with prioritized implementation plan + status table
│   ├── M1_STRATEGY.md               # Deep-dive strategy for sidebar consolidation
│   ├── C5_STRATEGY.md               # Deep-dive strategy for safety guidance
│   └── L1_L3_STRATEGY.md            # Deep-dive strategy for accessibility fixes
├── com.marley.ryzenadj-gtk.desktop   # Launcher entry
├── ryzenadj-gtk-apply.service        # systemd oneshot that re-applies settings on boot
├── ryzenadj-gtk.install              # pacman pre/post remove hooks
├── install.sh / uninstall.sh         # Distro-agnostic install/uninstall
├── PKGBUILD / .SRCINFO               # Arch package
├── README.md
└── ryzenadj.gif                     # Demo GIF for README
````

## Architecture

### Mixin-based composition for `RyzenadjApp`

`RyzenadjApp(Adw.Application, MonitorMixin, ActionsMixin)` in `src/main.py` is the central object. Functionality is split into two mixins to keep the class manageable:

- **`MonitorMixin`** (`src/monitor.py`) — periodic refresh loop, D-Bus sleep listener, AC-power profile automation, dashboard card updates.
- **`ActionsMixin`** (`src/actions.py`) — user-triggered actions: apply, presets, startup toggle, factory reset, enthusiast mode, conflict resolution.

State on the app instance is shared freely between mixins and pages: `pending_settings`, `applied_settings`, `current_info`, `_slider_rows`, `_dashboard_cards`, `supported_params`, `cpu_family`, `ui_settings`, etc. Page builders in `pages.py` attach widgets back onto the app (e.g. `app.btn_apply`, `app.diagnostic_banner`, `app.profiles_listbox`).

### Threading model

GTK is main-thread-only. All hardware calls go through `subprocess` / file IO and are dispatched to background threads, then results are returned via `GLib.idle_add(...)`. Key patterns:

- `_do_initial_load_async` / `_do_refresh_async` spawn a daemon thread, then `GLib.idle_add` the `_on_*_done` callback.
- All ryzenadj invocations funnel through `settings._run_elevated()` which holds a `_hardware_lock` (a `threading.Lock`) to serialize access to the SMU.
- The persistence guard runs `ryzen.apply_settings` on a daemon thread from the GLib timer callback — never block the main thread.

### Module: `ryzen.py` (backend facade)

This is the single import surface used by UI code (`import ryzen`). It re-exports heavily from `settings`, `system`, and `params`, and adds:

- `is_ryzenadj_installed()` — `shutil.which` check
- `get_initial_data()` / `get_current_info()` — invoke `ryzenadj -i`, parse the table
- `_parse_info_output()` / `_parse_supported_params()` — regex parsing of ryzenadj's pipe-formatted output
- `_build_ryzenadj_args()` — **the most important low-level detail**: encodes Curve Optimizer offsets the way ryzenadj expects
- `apply_settings()` — orchestrates native ryzenadj apply + sysfs GFX fallback, filters unsupported params, optionally saves
- `apply_preset()` — wraps `ryzenadj --power-saving` / `--max-performance`
- `__main__` block — when run as `ryzen.py --apply-saved`, used by the systemd boot service

### Curve Optimizer encoding (critical, non-obvious)

ryzenadj takes Curve Optimizer offsets as packed 32-bit integers, not signed decimal. `_build_ryzenadj_args` in `src/ryzen.py` handles this — **don't apply Curve Optimizer values without going through it**:

- **`set-coall` / `set-cogfx`**: negative offsets are encoded as `0x100000 - abs(value)`; positives are passed through. Range clamped to `[-30, +30]`.
- **`set-coper-N`** (per-core): `(core_index << 20) | encoded_offset`.
- **`oc-volt`**: millivolts are converted to a VID via `int((1.55 - volts) / 0.00625)`, clamped to `[0, 127]`.
- **`oc-clk` / `oc-volt`**: implicitly prepends `--enable-oc` to the ryzenadj command.

### Module: `settings.py` (persistence + elevation)

- `_run_elevated(cmd, **kwargs)` — wraps `sudo -n <cmd>` and **resolves the absolute binary path with `shutil.which`** before invoking sudo (sudoers rules match on `/usr/bin/ryzenadj` etc., so this is required). Holds `_hardware_lock` to serialize.
- File paths (single source of truth):
  - `~/.config/ryzenadj-gtk/settings.json` — user-saved live settings (`CONFIG_FILE`)
  - `~/.config/ryzenadj-gtk/profiles.json` — named profiles (`PROFILES_FILE`)
  - `~/.config/ryzenadj-gtk/ui.json` — UI prefs (theme, automation, persistence, enthusiast) — managed in `main.py`, not here
  - `/etc/ryzenadj-gtk/settings.json` — system-wide copy read by the boot service (`SYSTEM_CONFIG_FILE`)
  - `/etc/sudoers.d/ryzenadj-gtk` — the sudoers drop-in
- `set_service_enabled()` — also writes the system copy and deletes it on disable.
- `factory_reset()` — wipes user config + ui.json + disables service. Does **not** delete `/etc/ryzenadj-gtk` (system file).

### Module: `system.py` (sysfs + sensors)

- `is_on_ac_power()` — scans `/sys/class/power_supply` for `type=Mains` (or names starting with `ac`/`adp`/containing `charger`). Returns `True` if no mains PSU is detected (assumes desktop).
- `check_system_lockdown_status()` — reads Secure Boot efivar, `/sys/kernel/security/lockdown`, `/proc/cmdline` for `iomem=relaxed`, and checks `/sys/module/ryzen_smu`. Drives the diagnostic banner.
- `get_live_cpu_clock()` / `get_live_gpu_clock()` — multiple fallbacks through `/sys/devices/system/cpu/.../scaling_cur_freq`, `/proc/cpuinfo`, AMDGPU `hwmon`/`pp_dpm_sclk`.
- `apply_gfx_clk_sysfs()` — the AMDGPU sysfs fallback for `min-gfxclk`/`max-gfxclk`. Writes `power_dpm_force_performance_level=manual`, then `s 0/1 <mhz>` then `c` to commit, using `sudo tee`. **Once used, the only way to fully reset is a reboot** — the app tracks this with `gfx_reboot_required`.
- `_find_amdgpu_od_card()` scans `card0..card3` for one with `pp_od_clk_voltage`.

### Module: `params.py` (capability detection + safety metadata)

- `SETTINGS_PARAMS` — list of dicts, each describing a tunable: `param` (CLI name), `label`, `desc`, `min`/`max`/`step` (in ryzenadj's native unit, e.g. mW / mA / MHz), `unit` vs `display_unit` / `display_divisor` (e.g. native mW with `display_divisor=1000` to show W), `category`, `value_key` (the matching `ryzenadj -i` metric name), and `is_cpu`/`is_gpu` flags for badges.
- **Safety metadata** (C5): Every entry also carries `risk` (`low`/`moderate`/`high` — hardware-independent inherent risk), `plain_desc` (one-sentence non-technical explanation), and `watch_for` (concrete symptom to monitor). These are defined in `_SAFETY_METADATA` and merged into `SETTINGS_PARAMS` by `_merge_safety_metadata()` (called after Curve Optimizer params are appended). Never claim a value is "safe" or "unsafe" — they describe inherent characteristics and observable consequences only.
- Per-core Curve Optimizer rows (`set-coper-0..N`) are appended at import time based on `_get_physical_core_count()` (reads `/sys/devices/system/cpu/cpu*/topology/core_cpus_list`).
- `is_parameter_supported(param, cpu_family, supported_params)` — multi-source capability check:
  - Curve Optimizer requires Zen 3+ (`cpu family >= 25`); `set-cogfx` and skin-temp are disabled on Strix/Phoenix/Hawk and 370/365/375 model strings
  - `oc-clk`/`oc-volt` require unlocked HX/HK parts (not AI series)
  - `min-gfxclk`/`max-gfxclk` are supported if either ryzenadj reports them OR the sysfs fallback path is available
  - Falls back to ryzenadj's own reported supported parameter list

### UI layer

- `ui.py :: build_main_window()` — constructs the `Adw.ApplicationWindow`, sidebar (`Adw.OverlaySplitView` + `Adw.ViewSwitcherSidebar`), header bar, action bar (preset + apply + revert-all buttons), menu (theme switcher, reload, about), and adds 4 pages to the main `Adw.ViewStack`: Dashboard, Profiles, **Tuning** (consolidated — M1), Settings. The header subtitle shows the active sub-tab on the Tuning page.
- `pages.py` — one builder per page: dashboard (live telemetry cards + System Health Summary + diagnostic banner + first-run welcome), profiles (save/apply/delete), settings (automation, persistence, startup, enthusiast, factory reset), **`_build_tuning_page()`** (M1 — nested `Adw.ViewStack` + `Adw.ViewSwitcherBar` with 5 sub-tabs: Power, Clocks, Current, Thermal, Undervolt), `_build_slider_page()` (generic, reused by tuning sub-tabs), category safety banners (C5), plus error/auth pages.
- `widgets.py :: _build_slider_row()` — large (~500 line) function building a single slider row. Includes: the title (`--param-name` style), GPU/CPU tag badges, **risk pill** (C5 — low/moderate/high), technical description, **plain-language description + watch-for hint** (C5), live/target badges, **target-value popover with SpinButton** (H2 — type exact values in display units), range-aware step buttons (±1/±5 for small ranges, ±1/±10/±100 for large), the slider itself, **deviation badge** (C5 — appears on significant changes, direction-aware), **revert button** (C5 — per-row undo to last applied or live value), and a per-row "remove from startup" button with reboot-prompt logic. Attaches private attrs (`_slider`, `_param_meta`, `_desc_label`, `_plain_label`, `_deviation_badge`, `_btn_revert`, `_cur_badge`, `_update_val_label`, `_update_revert_tooltip`) used elsewhere.
- `widgets.py` also exports deviation helpers: `_compute_deviation()`, `_compute_deviation_text()`, `_deviation_text_for()`, and `set_current_app()` (registers the running app so helpers can read `applied_settings` and `current_info`).
- `widgets.py :: _build_monitor_card()` / `_make_card_grid()` — dashboard stat cards with progress bars that auto-color (low/medium/high/bottleneck) and animate a "CAPPED" pulse at >=95% of limit.
- `styles.py` — single CSS string loaded into a `Gtk.CssProvider` at `APPLICATION` priority; theme overrides go into a separate provider at `USER` priority so they win. Includes C5 safety element styles (risk pills, deviation badges, category banners, plain-desc/watch-for labels) and L1-L3 accessibility styles (contrast fixes, `:focus-visible` indicators, touch target sizes, reduced-motion media query).

### Themes

Seven built-in accent themes (default, ryzen, geforce, intel, arch, saints, noctua) defined inline in `main.py :: on_theme_color_changed`. Switching regenerates CSS redefining `@accent_*`, `@cpu_badge_*`, `@gpu_badge_*` and reloads the user-priority provider. Choice persists in `ui.json` under the `theme` key.

## Notable Behaviors

### 1. Boot-time apply (systemd)

`ryzenadj-gtk-apply.service` is a `Type=oneshot` `RemainAfterExit=yes` unit running as root on `multi-user.target`. It invokes `python3 /usr/share/ryzenadj-gtk/ryzen.py --apply-saved`, which:

- Reads `/etc/ryzenadj-gtk/settings.json`
- Retries up to **5 times** with a 3-second backoff (the SMU may not be ready immediately at boot)
- Exits `0` on success, `1` if all attempts fail

`settings.set_service_enabled(True)` writes the current user settings into `/etc/ryzenadj-gtk/settings.json` so the service has something to apply.

### 2. AC / Battery profile automation

When `ui_settings["auto_switch"]` is `True`:

- `_check_power_source()` runs every refresh tick (1s) and compares against `last_ac_state`
- On transition, calls `_apply_auto_power_profile(is_ac)` which looks up `ac_profile` or `battery_profile` from `ui_settings`
- Special sentinels `"__power_saving__"` / `"__max_performance__"` map to the ryzenadj presets; otherwise the name is treated as a saved profile

### 3. Persistence Guard

If `ui_settings["persistence_enabled"]`, the refresh loop counts ticks and re-runs `ryzen.apply_settings(self.applied_settings, ...)` every N seconds (5/10/30/60). Used to fight firmware/BIOS resetting registers behind the user's back.

### 4. Sleep / wake restoration

`do_activate` subscribes to `org.freedesktop.login1.Manager.PrepareForSleep` on the system bus. On `active=False` (resume), schedules `_restore_after_sleep` after a 3-second grace period (to let devices re-initialize), then re-applies either the auto-switch profile or `applied_settings`.

### 5. Conflict locking

`ActionsMixin._update_conflicts()` disables mutually-exclusive controls:

- `min-gfxclk`/`max-gfxclk` vs `gfx-clk` (Forced iGPU Clock)
- `set-coall` vs any `set-coper-N` (all-core vs per-core)
- Anything GFX-related is hard-locked if `gfx_reboot_required` is True

The function also re-renders the description label with red "(Unsupported: ...)" / green "(AMDGPU Sysfs Overdrive - fallback)" annotations.

### 6. Enthusiast Mode

`ActionsMixin.on_enthusiast_toggled` expands slider upper bounds at runtime: power limits from 130W > 250W, VDD current from 300A > 500A, other currents from 100A > 150A. The `meta["max"]` is mutated on the row so subsequent badge math matches. **C5 enhancement:** The first time a user enables Enthusiast Mode, a one-time educational `Adw.MessageDialog` replaces the previous toast, explaining that the limits exist for desktop chips and most laptops cannot safely sustain these values. Persisted in `ui_settings["enthusiast_warned"]`. Subsequent toggles get a toast.

### 7. Risk confirmation (C5-improved)

`on_apply_clicked` builds a per-parameter risk summary showing each changed setting with its **delta from current** (e.g. "25.0 W → 65.0 W (+160%)"), inherent risk tag (🔴/🟡/🟢), and a one-line "what to watch for" hint. Response appearance is tiered: **DESTRUCTIVE** for high-risk params or extreme deltas (>200%), **SUGGESTED** otherwise. When Curve Optimizer or manual overclock params are in the diff, a stability-test reminder is included in the dialog body. Also includes `on_revert_all_clicked()` — reverts all pending changes to last applied values in one click. `_execute_apply` captures a pre-apply thermal baseline and sets a 5-minute monitoring window for post-apply temperature spike detection.

### 8. xdg-desktop-portal auto-fix (`src/app.py`)

On startup, `app.py` checks whether `xdg-desktop-portal.service` has a `Requisite=graphical-session.target` and whether that target is inactive (common on standalone WMs like sway/i3/Hyprland). If so, it copies the fragment to `~/.config/systemd/user/`, strips the `graphical-session.target` token, runs `daemon-reload`, and restarts the service. **All failures are swallowed** — this must never block app startup. See README "Troubleshooting" for the manual version.

### 9. Auth retry page

If `ryzenadj -i` fails with sudo/auth errors on initial load, the app swaps to `build_auth_required_page` (`pages.py`). The "Grant Background Access" button runs an inline shell script via `pkexec` that writes the same sudoers drop-in as `install.sh` (per-user scoped via `$USER`). **This script must stay in sync with `install.sh` and `PKGBUILD`** — three copies of the sudoers body exist.

## Security Model

The app needs to invoke `ryzenadj` and write to AMDGPU sysfs as root without prompting on every action. The narrow sudoers policy grants `NOPASSWD` for exactly:

- `/usr/bin/ryzenadj` and `/usr/local/bin/ryzenadj`
- `systemctl {enable,disable,is-enabled}{, --now} ryzenadj-gtk-apply.service`
- `tee /sys/class/drm/card*/device/pp_od_clk_voltage`
- `tee /sys/class/drm/card*/device/power_dpm_force_performance_level`

**Two scoping strategies:**

- `install.sh` (manual installs): rules are per-`$SUDO_USER`
- `PKGBUILD` (AUR/package): rules use `%wheel` group

All sudoers files are validated with `visudo -cf` before being moved into place, and chmod'd `0440 root:root`.

`settings._run_elevated` uses `sudo -n` (non-interactive) — if the rules aren't installed, calls fail fast rather than hanging on a prompt.

## Installation Paths (what gets created)

| Path                                                                            | Purpose                                                              |
| ------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `/usr/share/ryzenadj-gtk/*.py`                                                  | Python source (installed by both `PKGBUILD` and `install.sh`)        |
| `/usr/share/ryzenadj-gtk/assets/`                                               | Icons + graphics                                                     |
| `/usr/share/icons/hicolor/{256,512}x{256,512}/apps/com.marley.ryzenadj-gtk.png` | Launcher icons                                                       |
| `/usr/share/applications/com.marley.ryzenadj-gtk.desktop`                       | Menu entry                                                           |
| `/usr/bin/ryzenadj-gtk`                                                         | Shell wrapper: sets `PYTHONPATH` and execs `python3 .../app.py`      |
| `/usr/lib/systemd/system/ryzenadj-gtk-apply.service`                            | Boot-apply oneshot                                                   |
| `/etc/sudoers.d/ryzenadj-gtk`                                                   | Passwordless sudo drop-in                                            |
| `/etc/ryzenadj-gtk/`                                                            | System-wide settings dir (mode 775, root:wheel or root:$SUDO_USER)   |
| `~/.config/ryzenadj-gtk/`                                                       | Per-user settings, profiles, UI prefs (created on demand at runtime) |

## Common Tasks

### Bumping the version

Update in **three** places (they're not linked):

1. `src/main.py` → `APP_VER`
2. `PKGBUILD` → `pkgver` (and `pkgrel` if needed) + update `source` URL + `sha256sums`
3. `src/pages.py` → `APP_VER` fallback string (only used if `from main import APP_VER` fails)
4. `.SRCINFO` → regenerate with `makepkg --printsrcinfo > .SRCINFO`

### Adding a new tunable parameter

1. Add an entry to `SETTINGS_PARAMS` in `src/params.py` with all required keys (`param`, `label`, `desc`, `min`/`max`/`step`, `unit`, `display_divisor`, `display_unit`, `category`, `value_key`).
2. Add safety metadata to `_SAFETY_METADATA` in the same file: `risk` (`low`/`moderate`/`high`), `plain_desc` (one-sentence non-technical explanation), `watch_for` (concrete symptom to monitor). This is merged automatically by `_merge_safety_metadata()`.
3. Add capability logic to `is_parameter_supported()` if it's conditional.
4. If the CLI encoding is non-trivial (like Curve Optimizer), extend `_build_ryzenadj_args()` in `src/ryzen.py`.
5. The new param will automatically appear on the appropriate tuning sub-tab (categorized by `category`) and be picked up by apply/save/profile/revert/conflict flows — no other wiring needed.

### Modifying the dashboard

Edit the `_make_card_grid` calls in `pages.py :: _build_dashboard_page`. Each card is a `(val_key, lim_key, label, unit, icon_name)` tuple where keys come from the parsed `ryzenadj -i` output. Cards are always visible (missing data shows "—" with a diagnostic banner explaining why).

The dashboard also has a **System Health Summary** card (`_build_health_summary` in `pages.py`, updated by `_update_health_summary` in `monitor.py`) that computes a plain-language status verdict (Optimal / Power Limited / Current Limited / Thermal Limited / Light Load) from the telemetry fractions. It uses priority logic (thermal > current > power > idle > optimal) and shows three headline stats (temperature, power, headroom). The value-key sets `_THERMAL_VAL_KEYS`, `_CURRENT_VAL_KEYS`, `_POWER_VAL_KEYS` on `MonitorMixin` control which metrics feed into each category.

## Gotchas

- **Don't edit `applied_settings` from outside the apply flow.** It's the source of truth for "what's currently in hardware" — used by persistence guard, sleep restore, the "no changes to apply" short-circuit, and the C5 deviation indicator (reference point for "how far have you changed from known-good").
- **Don't bypass `_run_elevated`.** Subprocess calls to `ryzenadj` need the absolute-path resolution and the lock.
- **Reboot requirement after GFX sysfs changes.** Once `apply_gfx_clk_sysfs` runs, AMDGPU holds the override until driver reload. The app sets `gfx_reboot_required` and locks the sliders — preserve this behavior if you touch GFX logic.
- **Per-core CO is generated at import time.** Adding/removing CPU cores requires restarting the app; the row count is fixed when `params.py` loads.
- **`ryzen.py` `__main__` block runs as root from systemd.** Don't import GTK or anything user-session-aware there.
- **UI settings file (`ui.json`) is read/written by `main.py`, not `settings.py`.** `settings.py` only manages `settings.json` / `profiles.json`. Don't conflate them.
- **`_update_conflicts()` is called from many places** (initial load, slider value-changed, profile apply, settings remove). Keep it idempotent.
- **`init_gi.py` must be imported before `gi.repository`.** `app.py` imports it first; preserve ordering if you refactor.
- **`widgets.set_current_app(app)` must be called in `do_activate`** before any slider row is built or `update_val_label` is called. The deviation helpers (`_compute_deviation_text`) read `applied_settings` and `current_info` via this module-global reference. Without it, the deviation badge will silently never appear (the reference point is `None`).
- **The deviation helper fetches live telemetry fresh from `current_info`**, not from the `cur_cli` closure variable captured at row-build time (which is `None` before telemetry loads). Don't revert to using the closure — it's stale.
- **GTK CSS is NOT web CSS.** Does not support `!important`, `::before`/`::after` pseudo-elements, or many web-only properties. `:focus-visible` IS supported (GTK 4.2+). `@media (prefers-reduced-motion: reduce)` IS supported (GTK 4.12+). Test CSS changes with `Gtk.CssProvider.load_from_data()` and check stderr for "Theme parser error" warnings.
- **`Adw.ViewStack.add_titled_with_icon`** IS a real method (libadwaita 1.4+), despite Pyright type stubs being missing. Don't be fooled by "unknown import symbol" errors.
- **`_SLIDER_PAGES = {"tuning"}`** controls action bar visibility. The action bar shows whenever the consolidated Tuning page is visible, regardless of which sub-tab is active. Don't add individual sub-tab names here.

## UI/UX Improvement Plan

The file `UI_UX_REVIEW.md` contains a comprehensive UI/UX review with prioritized issues. The implementation status table is at the bottom of that file. Key design decisions implemented so far:

### Completed (P0 — Critical)

- **Range-aware step buttons** (`src/widgets.py`): Sliders with small ranges (Curve Optimizer −30..+30, temperature 40..105°C) now show ±1/±5 step buttons instead of the hardcoded ±1/±10/±100 set that was useless for small ranges. Uses `step_buttons_before`/`step_buttons_after` lists.
- **Optimistic support detection** (`src/params.py`): When `ryzenadj -i` fails to report supported params (e.g. SMU unavailable), `is_parameter_supported()` now returns `True` for standard params instead of `False`. Family-specific checks (CO Zen3+, OC HX/HK, etc.) still run first.
- **Always-visible dashboard cards** (`src/main.py`, `src/pages.py`): Cards are no longer hidden when telemetry data is missing — they show "—" instead. The diagnostic banner now also fires when telemetry is unavailable and `ryzen_smu` isn't loaded, with a dynamic title distinguishing lockdown vs missing-module causes.
- **System Health Summary** (`src/pages.py`, `src/monitor.py`, `src/styles.py`): A prominent health card at the top of the dashboard computes a status verdict from telemetry fractions using priority logic (thermal > current > power > idle > optimal). Shows a plain-language explanation sentence, three headline stats (temperature, power, headroom), and color-coded status pill. Makes the dashboard actionable for non-experts.

### Completed (C5 — Safety Guidance)

Safety guidance for beginners. Deliberately avoids absolute "safe zone" coloring — safe ranges are hardware-dependent (cooling, VRM, silicon lottery) and false safety guidance is worse than no guidance. See `C5_STRATEGY.md` for the full iterative review and enhanced plan.

Ten additive features implemented:

- **Inherent risk tag per param** (`src/params.py`): Every parameter carries a `risk` field (`low`/`moderate`/`high`) — hardware-independent inherent risk. Displayed as a colour-coded pill next to the title. NOT a safe-zone indicator.
- **Plain-language descriptions** (`src/params.py`, `src/widgets.py`): `plain_desc` field on every param — one-sentence non-technical explanation, always visible under the technical description.
- **"What to watch for" hints** (`src/params.py`, `src/widgets.py`): `watch_for` field with a concrete symptom to monitor per param.
- **Category-level safety banners** (`src/pages.py`): Dismissible info banner at the top of each tuning sub-tab with category-level guidance. Persisted in `ui_settings["category_banners_dismissed"]`.
- **Relative deviation indicator** (`src/widgets.py`, `src/styles.py`): Badge appears on significant deviation from last applied value or live reading. Direction-aware; CO uses absolute offset. Two tiers (moderate/major). Never claims safe/unsafe.
- **Revert button per slider** (`src/widgets.py`): Revert icon resets slider to last applied value or live reading. Tooltip shows the target value.
- **Revert All button** (`src/actions.py`, `src/ui.py`): Action bar button reverts all pending changes to last applied values in one click.
- **Improved risk dialog** (`src/actions.py`): Per-parameter delta from current, risk tag, watch-for hint. Tiered response appearance (DESTRUCTIVE for high-risk/extreme, SUGGESTED otherwise). Stability-test reminder merged in.
- **Temperature spike warning** (`src/monitor.py`, `src/actions.py`): 5-minute post-apply monitoring window. Warns on baseline+10°C OR absolute >90°C. Also flags failed hardware reads as instability signal. Each warning fires once per apply.
- **Enthusiast mode educational dialog** (`src/actions.py`): One-time dialog replacing the toast when first enabling Enthusiast Mode. Persisted in `ui_settings["enthusiast_warned"]`.

Key implementation detail: `widgets.set_current_app(app)` is called in `do_activate` to register the running app so deviation helpers can read `applied_settings` and `current_info` without threading the app through every helper signature. The deviation helper fetches live telemetry values fresh from `current_info` (not the stale `cur_cli` closure captured at row-build time before telemetry was available).

### Completed (P1 — High Priority)

- **Page-aware action bar** (`src/ui.py`): Action bar is hidden on Dashboard/Profiles/Settings; only visible on the consolidated Tuning page. Uses `notify::visible-child` signal + `_SLIDER_PAGES = {"tuning"}` set.

- **Unsaved changes indicator** (`src/main.py`, `src/widgets.py`, `src/monitor.py`, `src/actions.py`, `src/styles.py`): Apply button has two CSS states — idle (flat/subdued) and `.pending` (accent-colored with glow). Driven by `_update_apply_button_state()` called wherever settings change.
- **Longer toast timeout for errors** (`src/main.py`): Error toasts use 8s timeout + "Dismiss" button; success toasts stay at 2s.

### Completed (P2 — Medium Priority)

- **Type specific values** (`src/widgets.py`, `src/styles.py`): The "Target:" badge is now a MenuButton that opens a popover with a SpinButton for typing exact values in display units (W, A, °C, etc.). Clicking "Set" converts to native units and updates the slider.
- **Onboarding / first-run guidance** (`src/main.py`, `src/pages.py`, `src/widgets.py`): A `first_run` flag in `ui_settings` controls a dismissible welcome banner on the dashboard with getting-started tips. Parameter title labels have tooltips with full descriptions.
- **Broadened diagnostic banner** (`src/main.py`): Banner now detects three failure states: lockdown (Secure Boot), missing telemetry (ryzen_smu), and parameter detection failure (empty supported_params). Each with distinct title/message.

### Completed (P3a — M1 Sidebar Consolidation)

- **Tabbed sub-navigation** (`src/pages.py`, `src/ui.py`): The five separate sidebar entries (Power, Clocks, Current, Thermal, Undervolt) have been consolidated into a single **Tuning** entry. Each former page becomes a sub-tab driven by a nested `Adw.ViewStack` + `Adw.ViewSwitcherBar` — the standard GNOME Settings sub-navigation pattern. The sidebar now has 4 items (Dashboard, Profiles, Tuning, Settings) instead of 8.
  - `_build_tuning_page()` in `pages.py` builds the consolidated page, reusing `_build_slider_page()` unchanged for each category. Slider rows are still registered in `app._slider_rows`, so refresh / apply / conflict / preset / profile logic is completely unaffected.
  - `_SLIDER_PAGES` in `ui.py` is now `{"tuning"}`; the page-aware action bar shows whenever the tuning page is visible, regardless of which sub-tab is active.
  - The window title's subtitle shows the active sub-tab on the tuning page (e.g. `Power • AMD Ryzen 7 PRO 6850U`) and reverts to just the CPU name on other pages.
  - `app.tuning_stack` and `app.tuning_switcher_bar` are exposed for future enhancements (sub-tab persistence, search/filter).

See `M1_STRATEGY.md` for the full design rationale and `UI_UX_REVIEW.md` for the full list of remaining items.

### Completed (P3b — L1–L3 Accessibility)

CSS-only accessibility fixes in `src/styles.py`. See `L1_L3_STRATEGY.md` for the full deep-dive audit.

- **L1 (contrast)**: Bumped 8 text opacity values to meet WCAG AA (4.5:1) — hero subtitle (0.45→0.65), monitor card names (0.45→0.65), step button labels (0.45→0.7), health stat labels (0.4→0.6), health stat sub-values (0.4→0.6), monitor unit labels (0.4→0.6), idle status pill (0.5→0.65), idle apply button (0.5→0.65). Decorative icons left at 0.4.
- **L2 (focus indicators)**: Added `:focus-visible` rules for all buttons (2px outline + 2px offset), sliders (`scale:focus-visible trough`), sidebar navigation rows, step/adjustment buttons (3px outline for emphasis), and SpinButton. Uses `@accent_bg_color` for dark-background visibility. `:focus-visible` (not `:focus`) so mouse users don't see rings.
- **L3 (touch targets)**: Step buttons `34×26px → 36×36px`; adjustment buttons `32×32px → 36×36px`; added `min-width/min-height: 32px` for flat icon buttons (revert, remove).
- **Bonus (reduced motion)**: `@media (prefers-reduced-motion: reduce)` block disabling all animations and transitions. Note: GTK CSS does NOT support `!important` or `::before`/`::after` pseudo-elements — removed during implementation.

### Completed (P3c — M5 Light Theme)

Changed `Adw.ColorScheme.PREFER_DARK` to `Adw.ColorScheme.DEFAULT` in `src/main.py :: do_activate`. The app now follows the system theme (light or dark). All CSS uses `@window_fg_color` / `@window_bg_color` / `@accent_bg_color` semantic variables that adapt automatically to both themes. No CSS changes were needed.

---

## All UI/UX Review Items Complete

Every item in `UI_UX_REVIEW.md` is now marked ✅ Done. The implementation spans:

- **P0 (Critical):** C1–C5 — dashboard fixes, step buttons, support detection, health summary, safety guidance
- **P1 (High):** H1, H3, H4 — page-aware action bar, unsaved changes indicator, toast timeout
- **P2 (Medium):** H2, M2, M4 — type specific values, onboarding, diagnostic banner
- **P3 (Low):** M1, M5, L1–L3 — sidebar consolidation, light theme, accessibility (contrast, focus, touch targets, reduced motion)

Strategy documents: `M1_STRATEGY.md`, `C5_STRATEGY.md`, `L1_L3_STRATEGY.md`
