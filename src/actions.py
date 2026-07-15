import logging
import subprocess
import threading
import time

from gi.repository import Adw, GLib

import ryzen

log = logging.getLogger(__name__)


class ActionsMixin:
    """App action callbacks and user event handlers"""

    def on_apply_clicked(self, _btn) -> None:
        """Apply button click handler.

        Shows an improved risk dialog (C5) that lists each changed parameter
        with its delta from current, inherent risk tag, and a one-line
        "what to watch for" hint. Includes a stability-test reminder when Curve
        Optimizer or manual overclock parameters are in the diff. Response
        appearance is tiered — DESTRUCTIVE for genuinely extreme changes.
        """
        # Check which settings changed since we last wrote to hardware
        diff_settings = {}
        for k, v in self.pending_settings.items():
            if self.applied_settings.get(k) != v:
                diff_settings[k] = v

        if not diff_settings:
            self._show_toast("No changes to apply.", is_error=False)
            return

        # Build the per-parameter risk summary and decide response tier.
        lines = []
        any_high_risk = False
        any_extreme_delta = False  # >200% power increase etc.
        any_co_or_oc = False  # triggers stability-test reminder
        for param, val in diff_settings.items():
            meta = self._lookup_param_meta(param)
            risk = (meta or {}).get("risk", "moderate")
            watch_for = (meta or {}).get("watch_for") or ""
            label = (meta or {}).get("label", param)
            display_divisor = (meta or {}).get("display_divisor", 1)
            display_unit = (meta or {}).get(
                "display_unit", (meta or {}).get("unit", "")
            )

            # Compute the delta from current (live or last-applied) value
            cur_raw = self._current_value_for_param(param, meta)
            delta_str = self._format_delta(val, cur_raw, display_divisor, display_unit)

            risk_marker = {
                "high": "🔴 High",
                "moderate": "🟡 Moderate",
                "low": "🟢 Low",
            }.get(risk, "🟡 Moderate")

            line = f"• {label}: {delta_str}   [{risk_marker}]"
            if watch_for:
                line += f"\n   ⚠ Watch for: {watch_for}"
            lines.append(line)

            if risk == "high":
                any_high_risk = True
                any_co_or_oc = True
            if param in ("oc-clk", "oc-volt", "gfx-clk"):
                any_co_or_oc = True
            # Flag extreme power/current/temp increases (>200% of current)
            if cur_raw is not None and cur_raw > 0:
                pct = abs(val - cur_raw) / abs(cur_raw) * 100.0
                if pct >= 200.0:
                    any_extreme_delta = True

        body_parts = ["The following changes will be written to hardware:"]
        body_parts.append("")
        body_parts.extend(lines)
        if any_co_or_oc:
            body_parts.append("")
            body_parts.append(
                "⚠ Test for stability: run a heavy workload (a game, video "
                "export, or benchmark) for 30+ minutes and watch for crashes, "
                "freezes, or visual artifacts. Curve Optimizer instability "
                "often appears hours later under specific workloads, not "
                "immediately."
            )
        body = "\n".join(body_parts)

        dialog = Adw.MessageDialog(
            transient_for=self.win,
            heading="Apply Hardware Settings?",
            body=body,
        )
        dialog.set_body_use_markup(True)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("apply", "Apply")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        # Tiered response: any high-risk param OR extreme delta forces a
        # destructive appearance so the user makes a conscious decision.
        if any_high_risk or any_extreme_delta:
            dialog.set_response_appearance("apply", Adw.ResponseAppearance.DESTRUCTIVE)
        else:
            dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)

        def on_response(d, response):
            if response == "apply":
                self._execute_apply(diff_settings)

        dialog.connect("response", on_response)
        dialog.present()

    def _lookup_param_meta(self, param: str) -> dict | None:
        """Find the SETTINGS_PARAMS entry for a param name (linear scan)."""
        for m in ryzen.SETTINGS_PARAMS:
            if m["param"] == param:
                return m
        return None

    def _current_value_for_param(self, param: str, meta: dict | None):
        """Best-effort current value for delta computation.

        Priority: applied_settings[param] → live telemetry (value_key) → None.
        Returns the value in NATIVE units (mW, mA, etc.) to match pending.
        """
        if param in self.applied_settings:
            return float(self.applied_settings[param])
        if meta is not None:
            vkey = meta.get("value_key")
            div = meta.get("display_divisor", 1)
            raw = self.current_info.get(vkey) if vkey else None
            if raw is not None:
                return float(raw) * float(div)
        return None

    def _format_delta(self, new_val, cur_val, div: float, unit: str) -> str:
        """Format a delta line: '25.0 W → 65.0 W (+160%)' or '0 → -15 (+15)'."""

        def _disp(v):
            if unit == "":
                return f"{int(v):+d}"
            v_disp = v / div if div else v
            if unit in ("W", "A"):
                return f"{v_disp:.1f} {unit}"
            if unit == "°C":
                return f"{v_disp:.0f}{unit}"
            if unit in ("mW", "mA"):
                return f"{v_disp:.0f} {unit}"
            return f"{v_disp:.0f} {unit}" if unit else f"{int(v):+d}"

        if cur_val is None:
            return f"→ {_disp(new_val)}"
        if cur_val == 0:
            return f"{_disp(cur_val)} → {_disp(new_val)}"
        pct = (new_val - cur_val) / cur_val * 100.0
        sign = "+" if pct >= 0 else ""
        return f"{_disp(cur_val)} → {_disp(new_val)} ({sign}{pct:.0f}%)"

    def on_revert_all_clicked(self, _btn) -> None:
        """Revert all pending changes back to the last applied state in one click."""
        if not self.pending_settings:
            self._show_toast("Nothing to revert.", is_error=False)
            return
        # Snapshot pending → applied for every param that differs
        reverted = []
        for param, row in self._slider_rows.items():
            applied_val = self.applied_settings.get(param)
            slider = getattr(row, "_slider", None)
            meta = getattr(row, "_param_meta", None)
            if slider is None or meta is None:
                continue
            lo = meta["min"]
            hi = meta["max"]
            if applied_val is not None:
                target = float(applied_val)
            else:
                # No applied value: use live hardware reading, else default
                vkey = meta.get("value_key")
                div = meta.get("display_divisor", 1)
                raw = self.current_info.get(vkey) if vkey else None
                if raw is not None:
                    target = float(raw) * float(div)
                else:
                    target = float(meta.get("default", lo))
            target = max(lo, min(hi, target))
            row._updating_programmatically = True
            slider.set_value(target)
            row._updating_programmatically = False
            # Mirror pending state
            if param in self.applied_settings:
                self.pending_settings[param] = int(target)
            elif param in self.pending_settings:
                del self.pending_settings[param]
            if hasattr(row, "_update_val_label"):
                row._update_val_label(slider, False)
            reverted.append(param)
        if hasattr(self, "_update_conflicts"):
            self._update_conflicts()
        if hasattr(self, "_update_apply_button_state"):
            self._update_apply_button_state()
        self._show_toast(
            f"Reverted {len(reverted)} setting(s) to last applied values.",
            is_error=False,
        )

    def _execute_apply(self, diff_settings: dict) -> None:
        if getattr(self, "_is_applying", False):
            return
        self._is_applying = True
        self._set_actions_sensitive(False)
        self.btn_apply.set_label("Applying…")

        # C5: capture pre-apply thermal baseline so the monitor can detect
        # post-apply temperature spikes against the user's own starting point,
        # not an arbitrary threshold. Also sets a 5-minute monitoring window
        # that _on_refresh_done checks on each refresh.
        import time as _time

        self._post_apply_monitor_until = _time.monotonic() + 300.0  # 5 minutes
        self._post_apply_temp_baseline = self.current_info.get("THM VALUE CORE")
        self._post_apply_temp_warned = False
        self._post_apply_read_failed_warned = False

        def do_apply():
            ok, msg = ryzen.apply_settings(
                diff_settings, self.supported_params, self.cpu_family
            )
            GLib.idle_add(self._on_apply_done, ok, msg, diff_settings)

        t = threading.Thread(target=do_apply, daemon=True)
        t.start()

    def _on_apply_done(self, ok: bool, msg: str, applied_diff: dict) -> bool:
        self._is_applying = False
        self._set_actions_sensitive(True)
        self.btn_apply.set_label("Apply Settings")
        self._show_toast(msg, is_error=not ok)
        if ok:
            # Update local successfully-applied state tracking upon success
            self.applied_settings.update(applied_diff)
            self._update_apply_button_state()
            # Refresh to reflect new state
            GLib.timeout_add(
                500, lambda: self._do_refresh_async(force_sync_sliders=False) or False
            )
        else:
            # Sync sliders and pending_settings back to actual hardware/saved values to clear poisoned/unsupported states
            GLib.timeout_add(
                500, lambda: self._do_refresh_async(force_sync_sliders=True) or False
            )
        return False

    # ── Presets ────────────────────────────────────────────────────────────────

    def on_power_saving_clicked(self, _btn) -> None:
        if getattr(self, "_is_applying", False):
            return
        self._is_applying = True
        self._set_actions_sensitive(False)

        def go():
            ok, msg = ryzen.apply_preset("power-saving")
            GLib.idle_add(self._on_preset_done, ok, msg)

        threading.Thread(target=go, daemon=True).start()

    def on_max_performance_clicked(self, _btn) -> None:
        if getattr(self, "_is_applying", False):
            return
        self._is_applying = True
        self._set_actions_sensitive(False)

        def go():
            ok, msg = ryzen.apply_preset("max-performance")
            GLib.idle_add(self._on_preset_done, ok, msg)

        threading.Thread(target=go, daemon=True).start()

    def _on_preset_done(self, ok: bool, msg: str) -> bool:
        self._is_applying = False
        self._set_actions_sensitive(True)
        self._show_toast(msg, is_error=not ok)
        if ok:
            GLib.timeout_add(
                500, lambda: self._do_refresh_async(force_sync_sliders=True) or False
            )
        return False

    # ── Startup Service Toggle ──────────────────────────────────────────────────

    def on_startup_switch_toggled(self, switch_row, _spec) -> None:
        if getattr(self, "_setting_service_switch", False):
            return
        active = switch_row.get_active()
        if active != ryzen.is_service_enabled():
            # Disable switch to prevent rapid clicking of systemctl commands
            switch_row.set_sensitive(False)

            def run_toggle():
                start_time = time.time()
                ok, msg = ryzen.set_service_enabled(active)

                # Sleep 1.5s to let systemd finish its tasks before user clicks again
                elapsed = time.time() - start_time
                cooldown = 1.5
                if elapsed < cooldown:
                    time.sleep(cooldown - elapsed)

                GLib.idle_add(self._on_startup_toggle_done, ok, msg, active, switch_row)

            threading.Thread(target=run_toggle, daemon=True).start()

    def _on_startup_toggle_done(
        self, ok: bool, msg: str, active: bool, switch_row
    ) -> bool:
        self._show_toast(msg, is_error=not ok)
        if not ok:
            self._setting_service_switch = True
            switch_row.set_active(not active)
            self._setting_service_switch = False
        # Turn the row back on after cool down
        switch_row.set_sensitive(True)
        return False

    # ── Factory Reset ──────────────────────────────────────────────────────────

    def on_factory_reset_clicked(self, _btn) -> None:
        dialog = Adw.MessageDialog(
            transient_for=self.win,
            heading="Factory Reset & Wipe?",
            body="This will:\n • Delete all saved settings\n • Disable the boot-apply service\n • Clear all overrides on the next reboot\n\nAre you sure you want to proceed?",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("reset", "Reset Everything")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(d, response):
            if response == "reset":
                self._execute_factory_reset()

        dialog.connect("response", on_response)
        dialog.present()

    def _execute_factory_reset(self) -> None:
        self._set_actions_sensitive(False)

        def do_reset():
            ok, msg = ryzen.factory_reset()
            GLib.idle_add(self._on_factory_reset_done, ok, msg)

        threading.Thread(target=do_reset, daemon=True).start()

    def _on_factory_reset_done(self, ok: bool, msg: str) -> bool:
        self._set_actions_sensitive(True)
        if ok:
            # Flag reboot if min/max graphics clocks were altered
            had_gfx = any(
                p in self.applied_settings
                for p in ("min-gfxclk", "max-gfxclk", "gfx-clk")
            )
            self.pending_settings.clear()
            self.applied_settings.clear()
            if had_gfx:
                self.gfx_reboot_required = True

            # Prompt user to reboot immediately
            reboot_dialog = Adw.MessageDialog(
                transient_for=self.win,
                heading="Reset Complete",
                body="Settings have been wiped. A system reboot is required to clear current hardware registers and return to stock behavior.\n\nWould you like to reboot now?",
            )
            reboot_dialog.add_response("later", "Later")
            reboot_dialog.add_response("reboot", "Reboot Now")
            reboot_dialog.set_default_response("reboot")
            reboot_dialog.set_response_appearance(
                "reboot", Adw.ResponseAppearance.SUGGESTED
            )

            def on_reboot_response(d, response):
                if response == "reboot":
                    subprocess.run(["pkexec", "systemctl", "reboot"], check=False)
                else:
                    self.on_refresh_clicked(None)

            reboot_dialog.connect("response", on_reboot_response)
            reboot_dialog.present()
        else:
            self._show_toast(f"Reset failed: {msg}", is_error=True)
        return False

    # ── Enthusiast Mode Toggle ──────────────────────────────────────────────────

    def on_enthusiast_toggled(self, switch_row, _spec) -> None:
        active = switch_row.get_active()
        if self.enthusiast_mode == active:
            return
        self.enthusiast_mode = active
        self.ui_settings["enthusiast_mode"] = active
        self._save_ui_settings()

        # High limits for Enthusiast Mode
        power_standard_max = 130000
        power_enthusiast_max = 250000  # 250W

        current_standard_max = 300000
        current_enthusiast_max = 500000  # 500A

        for param, row in self._slider_rows.items():
            meta = getattr(row, "_param_meta", None)
            if not meta:
                continue

            # Determine the new max range
            if meta["category"] == "power" or meta["param"] == "skin-temp-limit":
                new_max = power_enthusiast_max if active else power_standard_max
            elif meta["category"] == "current":
                if meta["param"] in ("vrm-current", "vrmmax-current"):
                    new_max = current_enthusiast_max if active else current_standard_max
                else:
                    new_max = 150000 if active else 100000
            else:
                continue

            # Set new upper boundaries on slider ranges
            slider = getattr(row, "_slider", None)
            if slider:
                adj = slider.get_adjustment()
                val = adj.get_value()
                if not active and val > new_max:
                    adj.set_value(new_max)
                adj.set_upper(new_max)
                slider.set_tooltip_text(
                    f"Range: {int(adj.get_lower())} – {new_max} {meta['unit']}"
                )

                # Sync range metadata so resets don't clamp settings
                meta["max"] = new_max

                row._updating_programmatically = True
                slider.set_value(slider.get_value())  # nudge to force badge refresh
                row._updating_programmatically = False
                if hasattr(row, "_update_val_label"):
                    row._update_val_label(slider, False)

        if active:
            # C5: one-time educational dialog when first enabling enthusiast
            # mode. A single toast is insufficient warning for unlocking 250W /
            # 500A limits. The dialog only fires once per user (persisted in
            # ui_settings["enthusiast_warned"]) — subsequent toggles still get
            # a toast so the user knows the toggle took effect.
            if not self.ui_settings.get("enthusiast_warned", False):
                self.ui_settings["enthusiast_warned"] = True
                self._save_ui_settings()
                dialog = Adw.MessageDialog(
                    transient_for=self.win,
                    heading="Enthusiast Mode Enabled",
                    body=(
                        "Enthusiast Mode raises the upper limits on power and "
                        "current sliders to extreme values (up to 250W / 500A).\n\n"
                        "These limits exist for desktop chips with heavy-duty "
                        "cooling and VRM hardware. Most laptops cannot safely "
                        "sustain anywhere near these values — setting them too "
                        "high can overheat the CPU, trip VRM protection, or "
                        "shorten hardware lifespan.\n\n"
                        "The higher limits simply allow you to explore further; "
                        "the hardware will still throttle itself when it hits "
                        "its thermal or electrical ceilings. Test any large "
                        "increases under load and watch your temperatures."
                    ),
                )
                dialog.add_response("ok", "I understand")
                dialog.set_default_response("ok")
                dialog.set_close_response("ok")
                dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
                dialog.connect("response", lambda d, r: d.destroy())
                dialog.present()
            else:
                self._show_toast(
                    "Enthusiast Mode: Extreme limits unlocked up to 250W!",
                    is_error=False,
                )
        else:
            self._show_toast(
                "Enthusiast Mode: Reset ranges back to standard bounds.",
                is_error=False,
            )

    def _update_conflicts(self) -> None:
        """Lock out conflicting settings (GFX min/max vs forced, CO all vs per-core)"""

        # 1. GFX Clocks
        if getattr(self, "gfx_reboot_required", False):
            # Lock everything if GFX was reset to stock and system needs a reboot
            for param in ("min-gfxclk", "max-gfxclk", "gfx-clk"):
                row = self._slider_rows.get(param)
                if not row:
                    continue
                meta = getattr(row, "_param_meta", None)
                desc_label = getattr(row, "_desc_label", None)
                if not meta or not desc_label:
                    continue

                hw_supported = ryzen.is_parameter_supported(
                    param, self.cpu_family, self.supported_params
                )
                if not hw_supported:
                    row.set_sensitive(False)
                    desc_label.set_markup(
                        f"<span style='italic' size='small'>{meta['desc']} <span color='#e01b24' weight='bold' size='small'>(Unsupported on this CPU)</span></span>"
                    )
                    continue

                row.set_sensitive(False)
                desc_label.set_markup(
                    f"<span style='italic' size='small'>{meta['desc']} <span color='#e01b24' weight='bold' size='small'>(Unsupported: reboot required to clear GFX conflicts)</span></span>"
                )
        else:
            has_min_max = ("min-gfxclk" in self.pending_settings) or (
                "max-gfxclk" in self.pending_settings
            )
            has_forced = "gfx-clk" in self.pending_settings

            for param in ("min-gfxclk", "max-gfxclk", "gfx-clk"):
                row = self._slider_rows.get(param)
                if not row:
                    continue
                meta = getattr(row, "_param_meta", None)
                desc_label = getattr(row, "_desc_label", None)
                if not meta or not desc_label:
                    continue

                hw_supported = ryzen.is_parameter_supported(
                    param, self.cpu_family, self.supported_params
                )
                if not hw_supported:
                    row.set_sensitive(False)
                    desc_label.set_markup(
                        f"<span style='italic' size='small'>{meta['desc']} <span color='#e01b24' weight='bold' size='small'>(Unsupported on this CPU)</span></span>"
                    )
                    continue

                is_conflicted = False
                conflict_msg = ""
                if param in ("min-gfxclk", "max-gfxclk") and has_forced:
                    is_conflicted = True
                    conflict_msg = "conflicts with Forced iGPU Clock"
                elif param == "gfx-clk" and has_min_max:
                    is_conflicted = True
                    conflict_msg = "conflicts with min/max iGPU Clock"

                if is_conflicted:
                    row._bottom_box.set_sensitive(False)
                    desc_label.set_markup(
                        f"<span style='italic' size='small'>{meta['desc']} <span color='#e01b24' weight='bold' size='small'>(Unsupported: {conflict_msg})</span></span>"
                    )
                else:
                    row.set_sensitive(True)
                    row._bottom_box.set_sensitive(True)
                    desc_text = meta["desc"]
                    if param in ("min-gfxclk", "max-gfxclk"):
                        ryzenadj_native = param in (self.supported_params or set())
                        if not ryzenadj_native and ryzen.is_sysfs_gfx_clk_available():
                            desc_text = f"{desc_text} <span color='#30d158' weight='bold' size='small'>(AMDGPU Sysfs Overdrive - fallback)</span>"
                    desc_label.set_markup(
                        f"<span style='italic' size='small'>{desc_text}</span>"
                    )

        # 2. Curve Optimizer (All Core vs Per Core)
        co_params = [
            p
            for p in self._slider_rows.keys()
            if p == "set-coall" or p.startswith("set-coper-")
        ]
        has_coall = "set-coall" in self.pending_settings
        has_coper = any(p.startswith("set-coper-") for p in self.pending_settings)

        for param in co_params:
            row = self._slider_rows.get(param)
            if not row:
                continue
            meta = getattr(row, "_param_meta", None)
            desc_label = getattr(row, "_desc_label", None)
            if not meta or not desc_label:
                continue

            hw_supported = ryzen.is_parameter_supported(
                param, self.cpu_family, self.supported_params
            )
            if not hw_supported:
                row.set_sensitive(False)
                desc_label.set_markup(
                    f"<span style='italic' size='small'>{meta['desc']} <span color='#e01b24' weight='bold' size='small'>(Unsupported on this CPU)</span></span>"
                )
                continue

            is_conflicted = False
            conflict_msg = ""
            if param.startswith("set-coper-") and has_coall:
                is_conflicted = True
                conflict_msg = "conflicts with All Core Offset"
            elif param == "set-coall" and has_coper:
                is_conflicted = True
                conflict_msg = "conflicts with Per Core Offsets"

            if is_conflicted:
                row._bottom_box.set_sensitive(False)
                desc_label.set_markup(
                    f"<span style='italic' size='small'>{meta['desc']} <span color='#e01b24' weight='bold' size='small'>(Unsupported: {conflict_msg})</span></span>"
                )
            else:
                row.set_sensitive(True)
                row._bottom_box.set_sensitive(True)
                desc_label.set_markup(
                    f"<span style='italic' size='small'>{meta['desc']}</span>"
                )
