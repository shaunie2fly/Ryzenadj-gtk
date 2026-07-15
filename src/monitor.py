import logging
import threading
import time

from gi.repository import GLib

import ryzen
from widgets import (
    _bar_class,
    _compute_deviation_text,
    _fmt,
    _fmt_limit,
    get_cpu_name,
)

log = logging.getLogger(__name__)

# Constants
REFRESH_INTERVAL_MS = 1000


class MonitorMixin:
    """Background hardware monitoring and periodic UI refresh loop"""

    def _start_refresh_timer(self) -> None:
        self._refresh_timer_id = GLib.timeout_add(
            REFRESH_INTERVAL_MS, self._auto_refresh
        )

    def _auto_refresh(self) -> bool:
        """Timer callback that schedules background hardware stats refresh"""
        if self._auth_granted is not True:
            return True  # Keep timer alive; fires again after retry succeeds

        # Monitor power source transition
        self._check_power_source()

        # Check and re-apply settings periodically to make sure they stick
        if self.ui_settings.get("persistence_enabled", False) and self.applied_settings:
            self._persistence_ticks += 1
            interval = int(self.ui_settings.get("persistence_interval", 30))
            if self._persistence_ticks >= interval:
                self._persistence_ticks = 0
                log.info(
                    "Persistence Guard: Verifying and re-applying settings: %s",
                    self.applied_settings,
                )

                def run_persistence():
                    ok, msg = ryzen.apply_settings(
                        self.applied_settings, self.supported_params, self.cpu_family
                    )
                    if not ok:
                        log.error(
                            "Persistence Guard: Failed to re-apply settings: %s", msg
                        )

                threading.Thread(target=run_persistence, daemon=True).start()
        else:
            self._persistence_ticks = 0

        if not self._refreshing:
            self._do_refresh_async(force_sync_sliders=False)
        return True  # Keep timer alive

    def on_prepare_for_sleep(
        self,
        connection,
        sender_name,
        object_path,
        interface_name,
        signal_name,
        parameters,
        user_data,
    ):
        """D-Bus signal callback for system sleep and wake events (researched how systemd triggers sleep/wake to make this work)"""
        try:
            is_about_to_sleep = parameters.get_child_value(0).get_boolean()
            if not is_about_to_sleep:
                log.info(
                    "System resumed from sleep. Triggering automatic hardware register restoration..."
                )
                GLib.timeout_add(3000, self._restore_after_sleep)
        except Exception as e:
            log.error("Failed to parse PrepareForSleep parameters: %s", e)

    def _restore_after_sleep(self) -> bool:
        """Restore last applied settings on hardware resume from sleep"""
        if self.ui_settings.get("auto_switch", False):
            current_ac = ryzen.is_on_ac_power()
            self.last_ac_state = current_ac
            log.info(
                "System waking up from sleep. Re-applying auto-switch power profile..."
            )
            self._apply_auto_power_profile(current_ac)
            return False

        if not self.applied_settings:
            log.info("No active settings to restore after sleep.")
            return False

        log.info(
            "Re-applying saved configuration to hardware: %s", self.applied_settings
        )

        def reapply():
            ok, msg = ryzen.apply_settings(
                self.applied_settings, self.supported_params, self.cpu_family
            )
            if ok:
                log.info("Successfully restored hardware registers after system sleep.")
                GLib.idle_add(
                    self._show_toast,
                    "Hardware settings automatically restored after sleep.",
                    False,
                )
            else:
                log.error("Failed to restore hardware registers: %s", msg)
                GLib.idle_add(
                    self._show_toast,
                    "Failed to restore hardware settings after sleep.",
                    True,
                )

        threading.Thread(target=reapply, daemon=True).start()
        return False

    def _check_power_source(self) -> None:
        """Check if power source changed (AC vs Battery) and update profile if it did"""
        current_ac = ryzen.is_on_ac_power()
        if self.last_ac_state is None:
            self.last_ac_state = current_ac
            return

        if current_ac != self.last_ac_state:
            self.last_ac_state = current_ac
            log.info("Power supply state changed: connected_to_ac=%s", current_ac)

            if self.ui_settings.get("auto_switch", False):
                self._apply_auto_power_profile(current_ac)

    def _apply_auto_power_profile(self, is_ac: bool) -> None:
        """Apply the profile configured for AC or Battery (researched how to parse power source transitions)"""
        profile_key = "ac_profile" if is_ac else "battery_profile"
        profile_name = self.ui_settings.get(profile_key, "")

        if not profile_name:
            log.info(
                "No profile configured for %s automation.", "AC" if is_ac else "Battery"
            )
            return

        profiles = ryzen.load_profiles()
        source_label = "AC power" if is_ac else "battery"

        if profile_name == "__power_saving__":
            self._show_toast(
                f"Switched to {source_label}. Applying 'Power Saving' preset...",
                is_error=False,
            )
            self.on_power_saving_clicked(None)
        elif profile_name == "__max_performance__":
            self._show_toast(
                f"Switched to {source_label}. Applying 'Max Performance' preset...",
                is_error=False,
            )
            self.on_max_performance_clicked(None)
        elif profile_name in profiles:
            target_settings = profiles[profile_name]
            self._show_toast(
                f"Switched to {source_label}. Applying '{profile_name}' profile...",
                is_error=False,
            )
            self._set_actions_sensitive(False)

            for param, val in target_settings.items():
                self.pending_settings[param] = val
                if param in self._slider_rows:
                    row_widget = self._slider_rows[param]
                    slider = getattr(row_widget, "_slider", None)
                    if slider:
                        row_widget._updating_programmatically = True
                        slider.set_value(float(val))
                        row_widget._updating_programmatically = False
                        if hasattr(row_widget, "_update_val_label"):
                            row_widget._update_val_label(slider, True)

            def run_write():
                ok, msg = ryzen.apply_settings(
                    target_settings, self.supported_params, self.cpu_family, save=False
                )
                GLib.idle_add(self._on_apply_done, ok, msg, target_settings)

            threading.Thread(target=run_write, daemon=True).start()
        else:
            log.warning(
                "Configured automation profile '%s' was not found in profiles database.",
                profile_name,
            )

    def on_refresh_clicked(self, _btn) -> None:
        if self._refreshing:
            return
        if self.btn_refresh:
            self.btn_refresh.set_sensitive(False)
        self._do_refresh_async(force_sync_sliders=True)

    def _do_refresh_async(self, force_sync_sliders: bool = False) -> None:
        self._refreshing = True

        def fetch():
            info = ryzen.get_current_info()
            GLib.idle_add(self._on_refresh_done, info, force_sync_sliders)

        t = threading.Thread(target=fetch, daemon=True)
        t.start()

    def _on_refresh_done(self, info: dict, force_sync_sliders: bool = False) -> bool:
        if info:
            self.current_info = info
            if force_sync_sliders:
                self.pending_settings.clear()
                saved = ryzen.load_settings()
                if saved:
                    self.pending_settings.update(saved)
                self._sync_sliders_to_hardware_or_pending(info, use_pending=True)
                self.applied_settings = dict(self.pending_settings)

        self._refreshing = False

        if self.btn_refresh:
            self.btn_refresh.set_sensitive(True)

        self._update_dashboard_cards()
        self._update_health_summary()
        self._update_slider_badges()
        self._update_status_label()
        self._update_conflicts()
        self._update_apply_button_state()

        # C5: post-apply reactive monitoring. For 5 minutes after an apply,
        # watch for temperature spikes (vs the pre-apply baseline) and for
        # failed hardware reads (a strong instability signal). Each warning
        # fires at most once per apply.
        self._post_apply_temp_check(info)

        return False

    def _post_apply_temp_check(self, info) -> None:
        """Check for temperature spikes or failed reads after an apply."""
        if time.monotonic() > getattr(self, "_post_apply_monitor_until", 0.0):
            return
        # Failed hardware read = strong instability signal
        if info is None:
            if not getattr(self, "_post_apply_read_failed_warned", False):
                self._post_apply_read_failed_warned = True
                if hasattr(self, "_show_toast"):
                    self._show_toast(
                        "⚠ Hardware read failed after apply — system may be "
                        "unstable. Consider reverting your changes or rebooting.",
                        is_error=True,
                    )
            return
        temp = info.get("THM VALUE CORE")
        if temp is None:
            return
        baseline = getattr(self, "_post_apply_temp_baseline", None)
        already_warned = getattr(self, "_post_apply_temp_warned", False)
        if already_warned:
            return
        spike_vs_baseline = baseline is not None and temp >= baseline + 10.0
        absolute_high = temp >= 90.0
        if spike_vs_baseline or absolute_high:
            self._post_apply_temp_warned = True
            if hasattr(self, "_show_toast"):
                if spike_vs_baseline and baseline is not None:
                    detail = (
                        f"Temperature rose from {baseline:.0f}°C to {temp:.0f}°C "
                        "after your tuning change."
                    )
                else:
                    detail = f"Temperature reached {temp:.0f}°C under load."
                self._show_toast(
                    f"⚠ {detail} Consider reverting or improving cooling.",
                    is_error=True,
                )

    def _update_dashboard_cards(self) -> None:
        for card in self._dashboard_cards:
            val_key = getattr(card, "_val_key", None)
            lim_key = getattr(card, "_lim_key", None)
            if not val_key:
                continue
            val = self.current_info.get(val_key)
            limit = self.current_info.get(lim_key) if lim_key else None

            val_str = f"{val:.1f}" if val is not None else "—"
            card._val_lbl.set_text(val_str)

            if val is not None and limit and limit > 0:
                frac = min(1.0, val / limit)
            else:
                frac = 0.0

            if hasattr(card, "_lim_lbl") and card._lim_lbl:
                card._lim_lbl.remove_css_class("bottleneck")
                limit_str = _fmt_limit(limit, card._unit)
                if frac >= 0.95:
                    limit_str = f"⚠️ CAPPED ({limit_str.replace('Limit: ', '')})"
                    card._lim_lbl.add_css_class("bottleneck")
                card._lim_lbl.set_text(limit_str)

            bar = card._bar
            for cls in ("low", "medium", "high", "bottleneck"):
                bar.remove_css_class(cls)
            bar.add_css_class(_bar_class(frac))
            if frac >= 0.95:
                bar.add_css_class("bottleneck")
            bar.set_fraction(frac)

    # Value keys used by each health category
    _THERMAL_VAL_KEYS = {"THM VALUE CORE", "STT VALUE APU", "STT VALUE dGPU"}
    _CURRENT_VAL_KEYS = {
        "TDC VALUE VDD",
        "TDC VALUE SOC",
        "EDC VALUE VDD",
        "EDC VALUE SOC",
    }
    _POWER_VAL_KEYS = {
        "STAPM VALUE",
        "PPT VALUE FAST",
        "PPT VALUE SLOW",
        "PPT VALUE APU",
    }

    def _update_health_summary(self) -> None:
        """Compute a human-readable system health verdict from telemetry data.

        Scans all dashboard card metrics, categorizes them into thermal / current /
        power, finds the highest utilization in each category, and derives a
        single priority-based status that's displayed as plain language.
        """
        if not hasattr(self, "health_status_pill"):
            return

        thermal_max = 0.0
        current_max = 0.0
        power_max = 0.0
        overall_max = 0.0

        headline_temp = None
        headline_temp_limit = None
        headline_power = None
        headline_power_limit = None

        for card in self._dashboard_cards:
            val_key = getattr(card, "_val_key", None)
            if not val_key:
                continue

            val = self.current_info.get(val_key)
            lim_key = getattr(card, "_lim_key", None)
            limit = self.current_info.get(lim_key) if lim_key else None

            # Track headline metrics for the stat badges
            if val_key == "THM VALUE CORE":
                headline_temp = val
                headline_temp_limit = limit
            elif val_key == "STAPM VALUE":
                headline_power = val
                headline_power_limit = limit

            # Compute fraction (0..1) — how close to the limit
            if val is not None and limit and limit > 0:
                frac = min(1.0, val / limit)
            else:
                frac = 0.0

            overall_max = max(overall_max, frac)

            if val_key in self._THERMAL_VAL_KEYS:
                thermal_max = max(thermal_max, frac)
            elif val_key in self._CURRENT_VAL_KEYS:
                current_max = max(current_max, frac)
            elif val_key in self._POWER_VAL_KEYS:
                power_max = max(power_max, frac)

        # --- Determine status (priority: thermal > current > power > idle > optimal) ---
        CAPPED = 0.95
        IDLE = 0.30

        # CSS class names must match styles.py
        _STATUS_CSS = {
            "optimal": "optimal",
            "power": "power-limited",
            "current": "current-limited",
            "thermal": "thermal-limited",
            "idle": "idle",
        }

        if not self.current_info:
            status_key = "idle"
            pill_text = "⚫ No Data"
            desc = "Telemetry unavailable. Install/load the ryzen_smu kernel module for live monitoring."
        elif thermal_max >= CAPPED:
            status_key = "thermal"
            pill_text = "🔴 Thermal Limited"
            if headline_temp is not None:
                desc = f"Heat is limiting performance at {headline_temp:.0f}°C. Lowering power limits or improving cooling will help stability."
            else:
                desc = "Temperature has reached its limit. Lowering power limits or improving cooling will help stability."
        elif current_max >= CAPPED:
            status_key = "current"
            pill_text = "🟠 Current Limited"
            desc = "VRM current delivery is maxed out. Raising TDC/EDC limits may unlock more boost."
        elif power_max >= CAPPED:
            status_key = "power"
            pill_text = "🟡 Power Limited"
            if headline_power is not None:
                desc = f"Power budget is the bottleneck at {headline_power:.1f}W. Raising STAPM/PPT limits may improve performance."
            else:
                desc = "Power budget is the bottleneck. Raising STAPM/PPT limits may improve performance."
        elif overall_max < IDLE:
            status_key = "idle"
            pill_text = "⚫ Light Load"
            desc = "System is lightly loaded — open a game or benchmark for meaningful readings."
        else:
            status_key = "optimal"
            pill_text = "🟢 Optimal"
            headroom_pct = int((1.0 - overall_max) * 100)
            desc = f"Running freely with {headroom_pct}% headroom remaining. No bottlenecks detected."

        # --- Update status pill ---
        self.health_status_pill.set_text(pill_text)
        for cls in _STATUS_CSS.values():
            self.health_status_pill.remove_css_class(cls)
        self.health_status_pill.add_css_class(_STATUS_CSS[status_key])

        # --- Update description ---
        self.health_description.set_text(desc)

        # --- Update headline stat badges ---
        # Temperature
        if headline_temp is not None:
            self.health_temp_value.set_text(f"{headline_temp:.0f}°C")
            if headline_temp_limit is not None and headline_temp_limit > 0:
                self.health_temp_sub.set_text(f"Limit: {headline_temp_limit:.0f}°C")
            else:
                self.health_temp_sub.set_text("Limit: Auto")
        else:
            self.health_temp_value.set_text("—")
            self.health_temp_sub.set_text("")

        # Power
        if headline_power is not None:
            if headline_power_limit is not None and headline_power_limit > 0:
                pct = int(headline_power / headline_power_limit * 100)
                self.health_power_value.set_text(f"{headline_power:.1f}W")
                self.health_power_sub.set_text(
                    f"{pct}% of {headline_power_limit:.0f}W budget"
                )
            else:
                self.health_power_value.set_text(f"{headline_power:.1f}W")
                self.health_power_sub.set_text("Budget: Auto")
        else:
            self.health_power_value.set_text("—")
            self.health_power_sub.set_text("")

        # Headroom
        headroom_pct = int((1.0 - overall_max) * 100) if overall_max > 0 else 100
        self.health_headroom_value.set_text(f"{headroom_pct}%")
        if not self.current_info:
            self.health_headroom_sub.set_text("No data")
        elif thermal_max >= CAPPED:
            self.health_headroom_sub.set_text("Heat is the bottleneck")
        elif current_max >= CAPPED:
            self.health_headroom_sub.set_text("Current is the bottleneck")
        elif power_max >= CAPPED:
            self.health_headroom_sub.set_text("Power is the bottleneck")
        elif overall_max < IDLE:
            self.health_headroom_sub.set_text("System idle")
        else:
            self.health_headroom_sub.set_text("Room to boost")

    def _update_slider_badges(self) -> None:
        for param, row in self._slider_rows.items():
            meta = getattr(row, "_param_meta", None)
            if not meta:
                continue
            vkey = meta["value_key"]
            raw = self.current_info.get(vkey)
            if raw is not None:
                cur_text = _fmt(raw, 1, meta["display_unit"])
            else:
                cur_text = "—"
            badge = getattr(row, "_cur_badge", None)
            if badge:
                badge.set_text(f"Live: {cur_text}")

            # C5: refresh the deviation badge too, since the reference value
            # (applied_settings) may have changed after an apply. Re-derive
            # the live value in native units to match the pending value.
            slider = getattr(row, "_slider", None)
            deviation_badge = getattr(row, "_deviation_badge", None)
            if slider is None or deviation_badge is None:
                continue
            div = meta.get("display_divisor", 1)
            live_native = float(raw) * float(div) if raw is not None else None
            _dev = _compute_deviation_text(param, slider.get_value(), live_native)
            if _dev is not None:
                text, css_class = _dev
                deviation_badge.set_text(text)
                for cls in ("deviation-moderate", "deviation-major"):
                    deviation_badge.remove_css_class(cls)
                deviation_badge.add_css_class(css_class)
                deviation_badge.set_visible(True)
            else:
                deviation_badge.set_visible(False)
                deviation_badge.set_text("")

            # Also refresh the revert tooltip since applied_settings may have
            # changed (the revert target moves to the new applied value).
            update_revert = getattr(row, "_update_revert_tooltip", None)
            if update_revert is not None:
                update_revert()

    def _update_status_label(self) -> None:
        if not self.window_title:
            return
        # Preserve the sub-tab subtitle on the tuning page (set by ui.py's
        # update_header_title). Only reset to the bare CPU name on other pages,
        # where there is no sub-tab to display.
        if getattr(self, "view_stack", None) is not None:
            page_name = self.view_stack.get_visible_child_name() or ""
            if (
                page_name == "tuning"
                and getattr(self, "tuning_stack", None) is not None
            ):
                active_sub = self.tuning_stack.get_visible_child_name()
                if active_sub:
                    self.window_title.set_subtitle(
                        f"{active_sub.title()} • {get_cpu_name()}"
                    )
                    return
        self.window_title.set_subtitle(get_cpu_name())
