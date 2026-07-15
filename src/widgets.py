"""UI elements, sliders, formatting helpers, and card structures"""

import logging
import platform
import subprocess

from gi.repository import Adw, Gtk

import ryzen

log = logging.getLogger(__name__)

# Cache to store CPU name so we don't read cpuinfo repeatedly
_cpu_name_cache: str | None = None


def get_cpu_name() -> str:
    """Get CPU name from cpuinfo and format it nicely"""
    global _cpu_name_cache
    if _cpu_name_cache is not None:
        return _cpu_name_cache
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    name = line.split(":", 1)[1].strip()
                    if " w/" in name:
                        name = name.split(" w/", 1)[0]
                    if " with " in name:
                        name = name.split(" with ", 1)[0]
                    name = name.replace("Processor", "")
                    if len(name) > 35:
                        name = name[:32] + "..."
                    _cpu_name_cache = name.strip()
                    return _cpu_name_cache
    except Exception:
        pass
    _cpu_name_cache = platform.processor() or "AMD Ryzen"
    return _cpu_name_cache


def _bar_class(fraction: float) -> str:
    """Determine color classification for monitor card progress bars"""
    if fraction < 0.5:
        return "low"
    elif fraction < 0.8:
        return "medium"
    return "high"


def _fmt(value: float, divisor: float, unit: str) -> str:
    """Format numbers for display with their correct units"""
    v = value / divisor
    if unit == "":
        return f"{v:+.0f}" if v != 0 else "0"
    if unit in ("mW", "mA"):
        return f"{v:.0f} {unit}"
    if unit in ("W", "A"):
        return f"{v:.1f} {unit}"
    if unit == "°C":
        return f"{v:.1f}{unit}"
    if unit == "s":
        return f"{v:.0f} {unit}"
    return f"{v:.1f} {unit}"


def _fmt_limit(limit: float | None, unit: str) -> str:
    """Format limit values for display (none or 0 means Auto)"""
    if limit is None or limit < 0:
        return "Auto"
    if limit == 0:
        return "Auto"
    if unit == "°C":
        return f"Limit: {limit:.0f}°C"
    if unit == "s":
        return f"Limit: {limit:.0f}s"
    return f"Limit: {limit:.1f} {unit}"


# ─────────────────────────────────────────────────────────────────────────────
# C5 safety guidance: deviation indicator helpers
# ─────────────────────────────────────────────────────────────────────────────
# These compute the magnitude of a slider change relative to a reference value.
# They never claim a value is safe or unsafe — only flag how big the change is.
# Reference priority: last applied value (known-good) → live reading → none.
# Curve Optimizer uses absolute offset (not %); everything else uses %.

# Thresholds
_DEVIATION_PCT_MODERATE = 20.0
_DEVIATION_PCT_MAJOR = 50.0
_CO_OFFSET_MODERATE = 5
_CO_OFFSET_MAJOR = 20


def _compute_deviation(param: str, pending_value: float, applied_value, live_value):
    """Return (tier, direction, magnitude, ref_label) or None.

    tier is "moderate" or "major".
    direction is "up", "down", or "co" (Curve Optimizer).
    magnitude is a float (percentage for most params, absolute offset for CO).
    ref_label is "last applied" or "current".
    """
    # Reference priority
    if applied_value is not None:
        ref, ref_label = float(applied_value), "last applied"
    elif live_value is not None:
        ref, ref_label = float(live_value), "current"
    else:
        return None

    # Curve Optimizer: absolute offset magnitude, direction-agnostic
    if param.startswith("set-co"):
        mag = abs(pending_value)
        if mag >= _CO_OFFSET_MAJOR:
            return ("major", "co", mag, ref_label)
        if mag >= _CO_OFFSET_MODERATE:
            return ("moderate", "co", mag, ref_label)
        return None

    # Percentage-based for everything else
    if ref == 0:
        return None
    pct = abs(pending_value - ref) / abs(ref) * 100.0
    if pct >= _DEVIATION_PCT_MAJOR:
        tier = "major"
    elif pct >= _DEVIATION_PCT_MODERATE:
        tier = "moderate"
    else:
        return None
    direction = "up" if pending_value > ref else "down"
    return (tier, direction, pct, ref_label)


def _deviation_text_for(param: str, meta: dict, result) -> str | None:
    """Turn a _compute_deviation result into a human-readable badge string."""
    if result is None:
        return None
    tier, direction, magnitude, ref_label = result
    category = meta.get("category", "")
    is_co = direction == "co"

    # Direction-aware wording by category
    if is_co:
        prefix = "⚠ Large offset" if tier == "major" else "Offset"
        return f"{prefix} ({magnitude:+.0f}) — test for stability"

    arrow = "↑" if direction == "up" else "↓"
    verb = "increase" if direction == "up" else "decrease"
    qualifier = "Large " if tier == "major" else ""
    if category in ("power", "current", "thermal"):
        if direction == "up":
            hint = "verify cooling"
        else:
            hint = "expect lower performance"
    elif category == "clocks":
        hint = "test for stability"
    else:
        hint = "observe behaviour"
    return f"{arrow} {qualifier}{verb} — {hint}"


def _compute_deviation_text(param: str, pending_value: float, live_value=None):
    """Convenience wrapper: returns (badge_text, css_class) or None.

    Reads applied_settings and the live telemetry value via the module-global
    app reference. The `live_value` argument is a fallback only — used when the
    app reference is unavailable (e.g. in standalone tests).
    """
    applied_value = None
    actual_live_value = live_value
    _app = _current_app_ref[0]
    if _app is not None:
        applied_value = getattr(_app, "applied_settings", {}).get(param)
        # Fetch a fresh live reading from current_info rather than relying on
        # the stale cur_cli closure captured at row-build time (before telemetry
        # was available). This is what makes the deviation indicator reliable.
        _row = getattr(_app, "_slider_rows", {}).get(param)
        if _row is not None:
            _meta = getattr(_row, "_param_meta", None)
            if _meta is not None:
                vkey = _meta.get("value_key")
                div = _meta.get("display_divisor", 1)
                raw = getattr(_app, "current_info", {}).get(vkey)
                if raw is not None:
                    actual_live_value = float(raw) * float(div)
    result = _compute_deviation(param, pending_value, applied_value, actual_live_value)
    if result is None:
        return None
    _meta = None
    if _app is not None:
        _row = getattr(_app, "_slider_rows", {}).get(param)
        if _row is not None:
            _meta = getattr(_row, "_param_meta", None)
    if _meta is None:
        _meta = {"category": "undervolt" if param.startswith("set-co") else ""}
    text = _deviation_text_for(param, _meta, result)
    css_class = "deviation-major" if result[0] == "major" else "deviation-moderate"
    return text, css_class


# Mutable single-element list used as a nonlocal-free way for helpers above to
# reach the running app (set by RyzenadjApp at startup). Avoids threading the
# app through every helper signature.
_current_app_ref: list = [None]


def set_current_app(app) -> None:
    """Register the running app so deviation helpers can read applied_settings."""
    _current_app_ref[0] = app


def _build_slider_row(
    meta: dict, current_info: dict, pending: dict, app=None, is_supported: bool = True
) -> Gtk.ListBoxRow:
    """Build a slider row with +/- buttons and live telemetry labels"""
    param = meta["param"]
    desc = meta["desc"]
    lo = meta["min"]
    hi = meta["max"]

    is_sysfs_fallback = False
    if param in ("min-gfxclk", "max-gfxclk"):
        if app and hasattr(app, "supported_params"):
            ryzenadj_native = param in (app.supported_params or set())
            if not ryzenadj_native and ryzen.is_sysfs_gfx_clk_available():
                is_sysfs_fallback = True
                sysfs_range = ryzen.get_sysfs_gfx_clk_hardware_range()
                lo = sysfs_range[0]
                hi = sysfs_range[1]

    div = meta["display_divisor"]
    dunit = meta["display_unit"]
    vkey = meta["value_key"]

    row = Gtk.ListBoxRow()
    row.add_css_class("slider-row-item")
    row.set_selectable(False)
    row.set_activatable(False)

    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    main_box.set_margin_start(16)
    main_box.set_margin_end(16)
    main_box.set_margin_top(12)
    main_box.set_margin_bottom(12)

    top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

    text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    text_box.set_hexpand(True)

    flag_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

    title_label = Gtk.Label(xalign=0)
    title_label.set_markup(
        f"<span font_family='monospace' weight='bold' size='medium'>--{param}</span>"
    )
    title_label.add_css_class("slider-row-flag")
    # Tooltip with the parameter's full label and description for quick reference
    title_label.set_tooltip_text(f"{desc}\nFull name: {meta['label']}")
    flag_box.append(title_label)

    if meta.get("is_gpu", False):
        gpu_tag_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        gpu_tag_box.add_css_class("gpu-badge")
        gpu_tag_box.set_valign(Gtk.Align.CENTER)

        gpu_icon = Gtk.Image.new_from_icon_name("video-display-symbolic")
        gpu_icon.set_pixel_size(12)
        gpu_tag_box.append(gpu_icon)

        gpu_label = Gtk.Label(label="GPU")
        gpu_tag_box.append(gpu_label)

        flag_box.append(gpu_tag_box)
    elif meta.get("is_cpu", False):
        cpu_tag_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cpu_tag_box.add_css_class("cpu-badge")
        cpu_tag_box.set_valign(Gtk.Align.CENTER)

        cpu_icon = Gtk.Image.new_from_icon_name("system-run-symbolic")
        cpu_icon.set_pixel_size(12)
        cpu_tag_box.append(cpu_icon)

        cpu_label = Gtk.Label(label="CPU")
        cpu_tag_box.append(cpu_label)

        flag_box.append(cpu_tag_box)

    # ── C5 risk pill: inherent (hardware-independent) risk tag ──────────────
    # NOT a safe-zone colour — it conveys inherent risk that doesn't depend on
    # cooling/VRM/silicon. "oc-clk" is always riskier than "stapm-time".
    risk_level = meta.get("risk")
    if risk_level in ("low", "moderate", "high"):
        risk_pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        risk_pill.add_css_class(f"risk-pill")
        risk_pill.add_css_class(f"risk-{risk_level}")
        risk_pill.set_valign(Gtk.Align.CENTER)
        risk_lbl = Gtk.Label(label=risk_level.title())
        risk_lbl.add_css_class("risk-pill-label")
        risk_pill.append(risk_lbl)
        risk_pill.set_tooltip_text(
            "Inherent risk of changing this parameter (hardware-independent). "
            "Not a safe-zone indicator — actual stability depends on your cooling, "
            "VRM, and silicon quality."
        )
        flag_box.append(risk_pill)

    text_box.append(flag_box)

    desc_text = desc
    if not is_supported:
        desc_text = f"{desc} <span color='#e01b24' weight='bold' size='small'>(Unsupported on this CPU)</span>"
    elif is_sysfs_fallback:
        desc_text = f"{desc} <span color='#30d158' weight='bold' size='small'>(AMDGPU Sysfs Overdrive - fallback)</span>"

    desc_label = Gtk.Label(xalign=0)
    desc_label.set_markup(f"<span style='italic' size='small'>{desc_text}</span>")
    desc_label.add_css_class("slider-row-desc")

    text_box.append(desc_label)

    # ── C5 safety guidance: plain-language description + risk pill ─────────
    # Plain-language description (always visible, never claims a value is safe).
    plain_desc = meta.get("plain_desc")
    watch_for = meta.get("watch_for")
    if plain_desc:
        plain_label = Gtk.Label(xalign=0)
        plain_label.set_wrap(True)
        plain_label.set_xalign(0)
        plain_label.set_markup(f"<span size='small'>{plain_desc}</span>")
        plain_label.add_css_class("slider-row-plain-desc")
        text_box.append(plain_label)
        row._plain_label = plain_label
    if watch_for:
        watch_label = Gtk.Label(xalign=0)
        watch_label.set_wrap(True)
        watch_label.set_xalign(0)
        watch_label.set_markup(f"<span size='small'>Watch for: {watch_for}</span>")
        watch_label.add_css_class("slider-row-watch-for")
        text_box.append(watch_label)

    top_box.append(text_box)

    cur_raw = current_info.get(vkey)
    if cur_raw is not None:
        cur_text = f"Live: {_fmt(cur_raw, 1, dunit)}"
        cur_cli = cur_raw * div
    else:
        cur_text = "Live: —"
        cur_cli = None

    cur_badge = Gtk.Label(label=cur_text)
    cur_badge.add_css_class("live-badge")
    cur_badge.set_tooltip_text("Live reading from hardware")
    cur_badge.set_valign(Gtk.Align.CENTER)
    top_box.append(cur_badge)

    # ── C5 deviation badge: appears when the slider value deviates significantly
    # from a reference point (last applied value, else current live reading).
    # Honest signal: tells the user "you've made a big change", never "this is
    # safe/unsafe". Direction-aware; Curve Optimizer uses absolute offset not %.
    deviation_badge = Gtk.Label(label="")
    deviation_badge.add_css_class("deviation-badge")
    deviation_badge.set_valign(Gtk.Align.CENTER)
    deviation_badge.set_visible(False)
    top_box.append(deviation_badge)
    row._deviation_badge = deviation_badge

    if param in pending:
        init_val = float(pending[param])
    elif cur_cli is not None:
        init_val = max(lo, min(hi, cur_cli))
    else:
        init_val = float(meta.get("default", lo))

    calc_step = float(max(int(div), 1))

    adj = Gtk.Adjustment(
        value=init_val,
        lower=lo,
        upper=hi,
        step_increment=calc_step,
        page_increment=calc_step * 10,
        page_size=0,
    )
    slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
    slider.set_hexpand(True)
    slider.set_valign(Gtk.Align.CENTER)
    slider.set_draw_value(False)
    slider.set_round_digits(0)
    slider.set_tooltip_text(f"Range: {lo} – {hi} {meta['unit']}")

    scroll_controller = Gtk.EventControllerScroll.new(
        Gtk.EventControllerScrollFlags.BOTH_AXES
    )
    scroll_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
    scroll_controller.connect("scroll", lambda *args: True)
    slider.add_controller(scroll_controller)

    btn_remove = Gtk.Button(icon_name="edit-clear-symbolic")
    btn_remove.add_css_class("flat")
    btn_remove.set_tooltip_text(
        "Remove this setting from startup/boot service (may require reboot to fully clear)"
    )
    btn_remove.set_valign(Gtk.Align.CENTER)
    btn_remove.set_margin_start(4)

    def on_remove(_b, p=param, m=meta, c_cli=cur_cli, sli=slider, low_val=lo):
        is_gfx = p in ("min-gfxclk", "max-gfxclk", "gfx-clk")
        is_co = p == "set-coall" or p.startswith("set-coper-") or p == "set-cogfx"

        if is_gfx:
            params_to_remove = ["min-gfxclk", "max-gfxclk", "gfx-clk"]
        elif p == "set-cogfx":
            params_to_remove = ["set-cogfx"]
        elif p == "set-coall" or p.startswith("set-coper-"):
            if app:
                params_to_remove = [
                    k
                    for k in app._slider_rows.keys()
                    if k == "set-coall" or k.startswith("set-coper-")
                ]
            else:
                params_to_remove = [p]
        else:
            params_to_remove = [p]

        was_configured = False
        if app:
            was_configured = any(
                x in getattr(app, "pending_settings", {})
                or x in getattr(app, "applied_settings", {})
                for x in params_to_remove
            )

        success, msg = ryzen.remove_settings_from_startup(params_to_remove)

        if success:
            if app:
                for x in params_to_remove:
                    if x in getattr(app, "pending_settings", {}):
                        del app.pending_settings[x]
                    if x in getattr(app, "applied_settings", {}):
                        del app.applied_settings[x]
                if is_gfx and was_configured:
                    app.gfx_reboot_required = True

            for x in params_to_remove:
                row_widget = app._slider_rows.get(x) if app else None
                if row_widget:
                    sli_widget = getattr(row_widget, "_slider", None)
                    meta_widget = getattr(row_widget, "_param_meta", None)
                    if sli_widget and meta_widget:
                        c_cli_widget = None
                        vkey = meta_widget["value_key"]
                        cur_raw = app.current_info.get(vkey) if app else None
                        if cur_raw is not None:
                            c_cli_widget = cur_raw * meta_widget["display_divisor"]

                        row_widget._updating_programmatically = True
                        if c_cli_widget is not None:
                            sli_widget.set_value(c_cli_widget)
                        else:
                            sli_widget.set_value(
                                float(meta_widget.get("default", meta_widget["min"]))
                            )
                        row_widget._updating_programmatically = False

                        if hasattr(row_widget, "_update_val_label"):
                            row_widget._update_val_label(sli_widget, False)

            if app and hasattr(app, "_update_conflicts"):
                app._update_conflicts()
            if app and hasattr(app, "_update_apply_button_state"):
                app._update_apply_button_state()

            if app and app.win:
                if was_configured:
                    if is_gfx:
                        heading = "Graphics Clock Overrides Cleared"
                        body = "All graphics clock options have been cleared from startup settings.\n\nA reboot is recommended to fully return the graphics system to stock firmware behavior."
                    elif is_co:
                        heading = "Curve Optimizer Cleared"
                        body = "All Curve Optimizer settings (Global & Per Core) have been cleared.\n\nA reboot is recommended to fully clear these settings from hardware."
                    else:
                        heading = "Setting Removed from Startup"
                        body = f"{msg}\n\nA reboot is recommended to fully clear this setting from hardware."

                    reboot_dialog = Adw.MessageDialog(
                        transient_for=app.win,
                        heading=heading,
                        body=body,
                    )
                    reboot_dialog.add_response("later", "Later")
                    reboot_dialog.add_response("reboot", "Reboot Now")
                    reboot_dialog.set_default_response("reboot")
                    reboot_dialog.set_response_appearance(
                        "reboot", Adw.ResponseAppearance.SUGGESTED
                    )

                    def on_reboot_response(d, response):
                        if response == "reboot":
                            subprocess.run(
                                ["pkexec", "systemctl", "reboot"], check=False
                            )

                    reboot_dialog.connect("response", on_reboot_response)
                    reboot_dialog.present()
                else:
                    if hasattr(app, "_show_toast"):
                        app._show_toast(
                            f"{param} was not configured in startup settings.",
                            is_error=False,
                        )
            else:
                if app and hasattr(app, "_show_toast"):
                    app._show_toast(
                        msg
                        + "\nYou may need to reboot for the hardware to fully clear this setting.",
                        is_error=False,
                    )
        else:
            if app and hasattr(app, "_show_toast"):
                app._show_toast(msg, is_error=True)

    btn_remove.connect("clicked", on_remove)
    top_box.append(btn_remove)

    # ── C5 revert button: per-row undo back to last applied value, or live
    # hardware reading if never applied. Single biggest confidence-builder —
    # users experiment more freely when they know they can undo. Tooltip shows
    # exactly what value will be restored.
    btn_revert = Gtk.Button(icon_name="edit-undo-symbolic")
    btn_revert.add_css_class("flat")
    btn_revert.set_valign(Gtk.Align.CENTER)
    btn_revert.set_margin_start(4)

    def _resolve_revert_target():
        """Return (value, label) describing what revert will restore."""
        if app is not None:
            applied = getattr(app, "applied_settings", {}).get(param)
            if applied is not None:
                return float(applied), f"last applied ({_fmt(applied, div, dunit)})"
        if cur_cli is not None:
            return float(
                cur_cli
            ), f"live hardware reading ({_fmt(cur_cli, div, dunit)})"
        return float(meta.get("default", lo)), "parameter default"

    def _update_revert_tooltip(*_args):
        _val, label = _resolve_revert_target()
        btn_revert.set_tooltip_text(f"Revert to {label}")

    _update_revert_tooltip()

    def on_revert(_b, p=param, sli=slider):
        target_val, _label = _resolve_revert_target()
        target_val = max(lo, min(hi, target_val))
        row._updating_programmatically = True
        sli.set_value(target_val)
        row._updating_programmatically = False
        # Mirror update_val_label's bookkeeping so pending state stays consistent
        if app is not None:
            # If never configured, drop from pending; otherwise snap pending to target
            applied_map = getattr(app, "applied_settings", {})
            if p in applied_map:
                app.pending_settings[p] = int(target_val)
            elif p in app.pending_settings:
                del app.pending_settings[p]
            if hasattr(app, "_update_conflicts"):
                app._update_conflicts()
            if hasattr(app, "_update_apply_button_state"):
                app._update_apply_button_state()
        update_val_label(sli, False)
        if app and hasattr(app, "_show_toast"):
            app._show_toast(
                f"Reverted {p} to {_fmt(target_val, div, dunit)}.", is_error=False
            )

    btn_revert.connect("clicked", on_revert)
    top_box.append(btn_revert)
    row._btn_revert = btn_revert
    row._update_revert_tooltip = _update_revert_tooltip

    main_box.append(top_box)

    bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    bottom_box.set_margin_top(10)

    unit_label = dunit if dunit else meta["unit"]

    def adjust_slider(direction: int, steps: int):
        delta = max(int(div), 1) * steps
        adj = slider.get_adjustment()
        slider.set_value(
            max(
                adj.get_lower(),
                min(adj.get_upper(), slider.get_value() + direction * delta),
            )
        )

    def make_step_btn(
        label: str, direction: int, steps: int, tooltip: str
    ) -> Gtk.Button:
        b = Gtk.Button(label=label)
        b.add_css_class("step-btn")
        b.set_tooltip_text(tooltip)
        b.set_valign(Gtk.Align.CENTER)
        b.connect("clicked", lambda _b: adjust_slider(direction, steps))
        return b

    btn_minus = Gtk.Button(icon_name="list-remove-symbolic")
    btn_minus.add_css_class("circular")
    btn_minus.add_css_class("flat")
    btn_minus.add_css_class("adj-btn")
    btn_minus.set_tooltip_text(f"−1 {unit_label}")
    btn_minus.set_valign(Gtk.Align.CENTER)
    btn_minus.connect("clicked", lambda _b: adjust_slider(-1, 1))

    btn_plus = Gtk.Button(icon_name="list-add-symbolic")
    btn_plus.add_css_class("circular")
    btn_plus.add_css_class("flat")
    btn_plus.add_css_class("adj-btn")
    btn_plus.set_tooltip_text(f"+1 {unit_label}")
    btn_plus.set_valign(Gtk.Align.CENTER)
    btn_plus.connect("clicked", lambda _b: adjust_slider(1, 1))

    # Range-aware step buttons: small ranges (e.g. Curve Optimizer −30..+30, temperature)
    # use ±1/±5 since ±10/±100 would be useless or instantly clamp. Large ranges
    # (power, current, clocks) keep the full ±1/±10/±100 set.
    range_size = hi - lo
    step_buttons_before: list[Gtk.Button] = []  # buttons left of ±1
    step_buttons_after: list[Gtk.Button] = []  # buttons right of ±1
    if range_size <= 100:
        step_buttons_before.append(make_step_btn("−5", -1, 5, f"−5 {unit_label}"))
        step_buttons_after.append(make_step_btn("+5", 1, 5, f"+5 {unit_label}"))
    else:
        step_buttons_before.append(make_step_btn("−100", -1, 100, f"−100 {unit_label}"))
        step_buttons_before.append(make_step_btn("−10", -1, 10, f"−10 {unit_label}"))
        step_buttons_after.append(make_step_btn("+10", 1, 10, f"+10 {unit_label}"))
        step_buttons_after.append(make_step_btn("+100", 1, 100, f"+100 {unit_label}"))

    target_badge = Gtk.Label(label="Target: Auto")
    target_badge.add_css_class("target-badge")
    target_badge.set_valign(Gtk.Align.CENTER)
    target_badge.set_size_request(100, -1)

    # Wrap target badge in a MenuButton so clicking it opens an edit popover
    # for typing a specific value (H2: allow typing specific values)
    target_btn = Gtk.MenuButton()
    target_btn.set_child(target_badge)
    target_btn.set_tooltip_text("Click to type a specific value")
    target_btn.set_valign(Gtk.Align.CENTER)
    target_btn.add_css_class("target-btn")
    target_btn.set_has_frame(False)

    # Build the edit popover with a SpinButton in display units
    edit_popover = Gtk.Popover()
    edit_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    edit_box.set_margin_start(12)
    edit_box.set_margin_end(12)
    edit_box.set_margin_top(12)
    edit_box.set_margin_bottom(12)

    # SpinButton works in display units (e.g. W instead of mW)
    # Convert slider native range to display range
    display_lower = lo / div if div else lo
    display_upper = hi / div if div else hi
    display_step = max(
        float(meta.get("step", 1)) / div if div else float(meta.get("step", 1)), 0.01
    )
    display_value = slider.get_value() / div if div else slider.get_value()

    spin_adj = Gtk.Adjustment(
        value=display_value,
        lower=display_lower,
        upper=display_upper,
        step_increment=display_step,
        page_increment=display_step * 10,
        page_size=0,
    )
    spin_btn = Gtk.SpinButton(adjustment=spin_adj, digits=1 if display_step < 1 else 0)
    spin_btn.set_valign(Gtk.Align.CENTER)
    edit_box.append(spin_btn)

    unit_lbl = Gtk.Label(label=unit_label)
    unit_lbl.set_valign(Gtk.Align.CENTER)
    edit_box.append(unit_lbl)

    btn_confirm = Gtk.Button(label="Set")
    btn_confirm.add_css_class("suggested-action")
    btn_confirm.set_valign(Gtk.Align.CENTER)
    edit_box.append(btn_confirm)

    edit_popover.set_child(edit_box)
    target_btn.set_popover(edit_popover)

    def on_edit_confirm(_btn):
        display_val = spin_btn.get_value()
        native_val = display_val * div if div else display_val
        native_val = max(lo, min(hi, native_val))
        row._updating_programmatically = True
        slider.set_value(native_val)
        row._updating_programmatically = False
        update_val_label(slider, True)
        edit_popover.popdown()

    btn_confirm.connect("clicked", on_edit_confirm)

    # When popover opens, sync the SpinButton to the current slider value
    def on_popover_show(_popover):
        current = slider.get_value()
        display_current = current / div if div else current
        spin_btn.set_value(display_current)

    edit_popover.connect("map", on_popover_show)

    row._updating_programmatically = False

    def update_val_label(scale, user_triggered=False):
        if getattr(row, "_updating_programmatically", False):
            return
        v = scale.get_value()
        if user_triggered or param in pending:
            target_badge.set_text(f"Target: {_fmt(v, div, dunit)}")
            pending[param] = int(v)
        else:
            target_badge.set_text("Target: Auto")

        # ── C5 deviation badge update ──────────────────────────────────────
        # Compute how far the current slider value is from a reference point.
        # Reference priority: last applied value (known-good) → live reading →
        # none. Never claims a value is safe; only flags the magnitude of the
        # change. Curve Optimizer uses absolute offset, everything else uses %.
        _dev = _compute_deviation_text(param, v, cur_cli)
        if _dev is not None:
            text, css_class = _dev
            deviation_badge.set_text(text)
            # Reset CSS classes then re-apply
            for cls in ("deviation-moderate", "deviation-major"):
                deviation_badge.remove_css_class(cls)
            deviation_badge.add_css_class(css_class)
            deviation_badge.set_visible(True)
        else:
            deviation_badge.set_visible(False)
            deviation_badge.set_text("")

        if app and hasattr(app, "_update_conflicts"):
            app._update_conflicts()
        if app and hasattr(app, "_update_apply_button_state"):
            app._update_apply_button_state()

    slider.connect("value-changed", lambda s: update_val_label(s, True))
    row._update_val_label = update_val_label
    update_val_label(slider, False)

    for btn in step_buttons_before:
        bottom_box.append(btn)
    bottom_box.append(btn_minus)
    bottom_box.append(slider)
    bottom_box.append(btn_plus)
    for btn in step_buttons_after:
        bottom_box.append(btn)
    bottom_box.append(target_btn)

    main_box.append(bottom_box)
    row.set_child(main_box)

    if not is_supported:
        row.set_sensitive(False)

    row._slider = slider
    row._cur_badge = cur_badge
    row._param_meta = meta
    row._desc_label = desc_label
    row._bottom_box = bottom_box

    return row


def _build_monitor_card(
    val_key: str,
    lim_key: str | None,
    label: str,
    unit: str,
    icon_name: str,
    current_info: dict,
) -> Gtk.Box:
    """Build a monitor statistics card with progress bar"""
    val = current_info.get(val_key)
    limit = current_info.get(lim_key) if lim_key else None

    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    card.add_css_class("monitor-card")
    card.set_hexpand(True)

    top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    top_row.set_hexpand(True)

    icon = Gtk.Image.new_from_icon_name(icon_name)
    icon.add_css_class("monitor-icon")
    top_row.append(icon)

    name_lbl = Gtk.Label(label=label)
    name_lbl.add_css_class("monitor-name-label")
    name_lbl.set_halign(Gtk.Align.START)
    name_lbl.set_hexpand(True)
    top_row.append(name_lbl)

    limit_str = _fmt_limit(limit, unit)
    lim_lbl = Gtk.Label(label=limit_str)
    lim_lbl.add_css_class("monitor-limit-badge")
    lim_lbl.set_halign(Gtk.Align.END)
    top_row.append(lim_lbl)

    card.append(top_row)

    val_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    val_row.set_halign(Gtk.Align.START)
    val_row.set_margin_top(8)

    val_str = f"{val:.1f}" if val is not None else "—"
    val_lbl = Gtk.Label(label=val_str)
    val_lbl.add_css_class("monitor-value-label")
    val_row.append(val_lbl)

    unit_lbl = Gtk.Label(label=unit)
    unit_lbl.add_css_class("monitor-unit-label")
    unit_lbl.set_valign(Gtk.Align.END)
    unit_lbl.set_margin_bottom(6)
    val_row.append(unit_lbl)
    card.append(val_row)

    fraction = 0.0
    if val is not None and limit and limit > 0:
        fraction = min(1.0, val / limit)

    bar = Gtk.ProgressBar()
    bar.add_css_class("usage-bar")
    bar.set_fraction(fraction)
    bar.add_css_class(_bar_class(fraction))
    card.append(bar)

    card._val_lbl = val_lbl
    card._lim_lbl = lim_lbl
    card._bar = bar
    card._val_key = val_key
    card._lim_key = lim_key
    card._unit = unit

    return card


def _make_card_grid(app, defs: list[tuple]) -> Gtk.Grid:
    """Arrange monitor cards inside a grid layout"""
    grid = Gtk.Grid()
    grid.set_column_homogeneous(True)
    grid.set_row_homogeneous(False)
    grid.set_column_spacing(16)
    grid.set_row_spacing(16)
    grid.set_margin_bottom(12)

    count = len(defs)

    for i, (val_key, lim_key, label, unit, icon_name) in enumerate(defs):
        card = _build_monitor_card(
            val_key, lim_key, label, unit, icon_name, app.current_info
        )
        app._dashboard_cards.append(card)

        if count == 4:
            col = i % 2
            row = i // 2
            grid.attach(card, col, row, 1, 1)
        elif count == 3:
            if i < 2:
                grid.attach(card, i, 0, 1, 1)
            else:
                grid.attach(card, 0, 1, 2, 1)
        elif count == 2:
            grid.attach(card, 0, i, 2, 1)
        else:
            grid.attach(card, 0, i, 2, 1)

    return grid


def _build_section_header(title: str, icon_name: str) -> Gtk.Box:
    """Create a section header with an icon"""
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    box.add_css_class("section-title-box")

    icon = Gtk.Image.new_from_icon_name(icon_name)
    icon.add_css_class("category-icon")
    box.append(icon)

    label = Gtk.Label(label=title)
    label.add_css_class("section-title-label")
    box.append(label)

    return box
