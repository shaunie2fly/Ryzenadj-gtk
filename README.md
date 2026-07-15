<p align="center">
  <img src="src/assets/com.marley.ryzenadj-gtk.png" width="128" height="128" alt="Ryzenadj-gtk logo" />
</p>

# Ryzenadj-gtk

GTK4 frontend for ryzenadj. Change power limits, currents, temps, and curve optimizer without living in the terminal.

Powered by [RyzenAdj](https://github.com/flygoat/ryzenadj) ❤️

![Ryzenadj-gtk Demo](ryzen.gif)

## What it does

- **Dashboard** with live power, current, temperature, and clock speed telemetry
- **System Health Summary** — a plain-language status card at the top of the dashboard that tells you at a glance whether your system is optimal, power-limited, current-limited, or thermal-limited
- **Tuning page** with tabbed sub-navigation (Power, Clocks, Current, Thermal, Undervolt) — all tuning controls in one place instead of cluttering the sidebar
- **Curve Optimizer** with all-core, iGPU, and per-core sliders (−30 to +30)
- **Power limits** (STAPM, fast PPT, slow PPT, APU PPT) and time constants
- **Current limits** (TDC and EDC for CPU, SoC, and iGPU)
- **Temperature limits** and skin temperature controls
- **iGPU clock limits** with automatic AMDGPU sysfs fallback when ryzenadj can't change them directly
- **SoC clock** and low-level options (FCLK, VCN, LCLK)
- **Type exact values** — click the "Target:" badge on any slider to type a precise value in natural units (W, A, °C, MHz) instead of dragging
- **Save and switch profiles** — auto-switch when you plug or unplug the charger
- **Works after sleep** — re-applies settings automatically when the machine wakes up
- **Persistence Guard** — keeps applying settings in the background so firmware doesn't reset them
- **Light/dark theme** — follows your system theme automatically
- **Enthusiast mode** — unlocks extreme limits (up to 250W / 500A) behind a one-time educational dialog

## Safety guidance

The app provides honest, additive safety guidance without pretending to know what's "safe" for your specific hardware (safe ranges depend on cooling, VRM quality, and silicon lottery — false safety guidance is worse than no guidance):

- **Risk pills** on every parameter (🟢 Low / 🟡 Moderate / 🔴 High) — inherent, hardware-independent risk classification
- **Plain-language descriptions** under every parameter — what it does and what happens if you push it too far, in non-technical terms
- **"Watch for" hints** — concrete symptoms to monitor after changing each parameter
- **Category safety banners** — one-time guidance at the top of each tuning sub-tab
- **Deviation indicator** — a badge appears when you've made a significant change from the last applied value, showing direction (↑ increase / ↓ decrease) and magnitude. Never claims a value is safe or unsafe
- **Revert button** on every slider — undo back to the last applied value or live hardware reading. Tooltip shows exactly what will be restored
- **Revert All button** in the action bar — undo all pending changes in one click
- **Improved risk dialog** — shows each changed parameter with its delta from current (e.g. "25W → 65W, +160%"), risk tag, and what to watch for. Includes a stability-test reminder when Curve Optimizer or overclock changes are detected
- **Temperature spike warning** — after applying settings, monitors temperatures for 5 minutes and warns if they spike (baseline +10°C or absolute >90°C). Also flags failed hardware reads as a potential instability signal

## Accessibility

- **WCAG AA contrast** — all text meets the 4.5:1 contrast ratio on both light and dark themes
- **Keyboard focus indicators** — visible `:focus-visible` outlines on all buttons, sliders, sidebar items, and input fields (mouse users don't see them, keyboard users do)
- **Touch target sizes** — step buttons and adjustment buttons are 36×36px; icon buttons are 32×32px minimum
- **Reduced motion** — respects `prefers-reduced-motion` to disable animations and transitions for users with vestibular disorders

## Curve optimizer

Separate sliders for each core instead of just one global offset. Negative numbers reduce voltage (undervolt — cooler, may be unstable). Positive numbers increase voltage (overvolt — hotter, rarely useful).

The app clamps to the −30 to +30 range. It also shows a risk dialog before applying anything that looks risky, with per-parameter explanations and a stability-test reminder.

## iGPU Clock Controls & Sysfs Fallback

Some chips or RyzenAdj builds don't support maximum and minimum graphics clocks. If that's the case, the app will try writing directly to the AMDGPU driver under `/sys/class/drm` instead.

The installer sets up sudo rules for `tee` to handle this. If you change these values and want to fully reset them back to normal, you'll need to reboot your system so the GPU driver goes back to stock.

## Warnings

`ryzenadj` needs root access to the hardware. The install script and AUR package drop a sudoers file so you don't get spammed with password prompts every second. It's pretty narrow (only ryzenadj and the service commands).

If that file isn't there, the app will just show a page telling you to reboot or grant access.

Be careful with this tool. Too much power or too aggressive undervolting can make the machine unstable or hotter than expected. The risk dialogs and deviation indicators are there for a reason — pay attention to them, test for stability after changes, and use the revert button if something goes wrong.

## Requirements

- Python 3.11+
- gtk4 + libadwaita + python-gobject
- ryzenadj installed
- The sudoers rule (added by the installer)
- `ryzen_smu` kernel module (for telemetry — without it, the dashboard shows "—" and a diagnostic banner explains why)

## Install

**Arch (easiest):**

```bash
yay -S ryzenadj-gtk
```

Or build from this repo:

```bash
git clone https://github.com/marleylinux/Ryzenadj-gtk
```

```bash
cd Ryzenadj-gtk
makepkg -si
```

**Other distros:**

```bash
git clone https://github.com/marleylinux/Ryzenadj-gtk
```

```bash
cd Ryzenadj-gtk
sudo ./install.sh
```

Then launch "Ryzenadj-gtk" from your menu or just run `ryzenadj-gtk`.

### ryzen_smu (for telemetry)

The dashboard needs the `ryzen_smu` kernel module to read live telemetry from your CPU. Without it, the dashboard shows "—" for all values and a diagnostic banner explains why.

**Arch:**

```bash
sudo pacman -S ryzen_smu-dkms linux-headers
```

Reboot after installing. If you're on a custom kernel, make sure the headers package matches your kernel version.

## Troubleshooting

### "Cannot get portal... Could not activate remote peer" / Startup lag

If you see warnings like this in your terminal when launching the application:

```
(app.py:7341): Gdk-WARNING **: Cannot get portal org.freedesktop.portal.Settings version: GDBus.Error:org.freedesktop.DBus.Error.NameHasNoOwner: Could not activate remote peer 'org.freedesktop.portal.Desktop': startup job failed
```

This is a common system configuration issue on systemd-based distributions (like Arch Linux) when using a custom window manager (such as i3, Sway, or Hyprland) that does not automatically notify systemd that the `graphical-session.target` has started.

To fix this for all GTK applications on your system:

1. Copy the system portal service file to your user configuration directory:
   ```bash
   mkdir -p ~/.config/systemd/user/
   cp /usr/lib/systemd/user/xdg-desktop-portal.service ~/.config/systemd/user/xdg-desktop-portal.service
   ```
2. Open `~/.config/systemd/user/xdg-desktop-portal.service` in your preferred text editor and remove the following line from the `[Unit]` section:
   ```ini
   Requisite=graphical-session.target
   ```
3. Reload systemd and restart the portal service:
   ```bash
   systemctl --user daemon-reload
   systemctl --user restart xdg-desktop-portal.service
   ```

### Dashboard shows "—" for all values

This means the app can't read telemetry from your CPU. The most common cause is the `ryzen_smu` kernel module not being loaded. See the [ryzen_smu](#ryzen_smu-for-telemetry) section above.

If `ryzen_smu` is loaded but values are still empty, check whether Secure Boot or kernel lockdown is active — these block access to the SMU. The diagnostic banner on the dashboard will tell you which issue you're hitting.

## Documentation

All project documentation lives in the [`docs/`](docs/) folder:

| File                                               | Description                                                                                        |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| [`docs/agents.md`](docs/agents.md)                 | Architecture guide — module structure, design patterns, gotchas, and common tasks for contributors |
| [`docs/UI_UX_REVIEW.md`](docs/UI_UX_REVIEW.md)     | Comprehensive UI/UX review with prioritized issues, implementation details, and status table       |
| [`docs/M1_STRATEGY.md`](docs/M1_STRATEGY.md)       | Deep-dive strategy for sidebar consolidation (Option F: tabbed sub-navigation)                     |
| [`docs/C5_STRATEGY.md`](docs/C5_STRATEGY.md)       | Deep-dive strategy for safety guidance (iterative review + enhanced plan)                          |
| [`docs/L1_L3_STRATEGY.md`](docs/L1_L3_STRATEGY.md) | Deep-dive strategy for accessibility fixes (contrast, focus, touch targets, reduced motion)        |

## Uninstall

```bash
sudo ./uninstall.sh
```

## License

GPL-3.0

---

### Check out my other apps:

| [<img src="https://raw.githubusercontent.com/marleylinux/cpupower-gtk/main/src/assets/com.marley.cpupower-gtk.png" width="48" height="48" /><br/>cpupower-gtk](https://github.com/marleylinux/cpupower-gtk) | [<img src="https://raw.githubusercontent.com/marleylinux/Ryzenadj-gtk/main/src/assets/com.marley.ryzenadj-gtk.png" width="48" height="48" /><br/>Ryzenadj-gtk](https://github.com/marleylinux/Ryzenadj-gtk) | [<img src="https://raw.githubusercontent.com/marleylinux/FastFlowLM-gtk/main/src/assets/com.marley.FastFlowLM-gtk.png" width="48" height="48" /><br/>FastFlowLM-gtk](https://github.com/marleylinux/FastFlowLM-gtk) | [<img src="https://raw.githubusercontent.com/marleylinux/fetch-gtk/main/src/assets/com.marley.fetch-gtk.png" width="48" height="48" /><br/>fetch-gtk](https://github.com/marleylinux/fetch-gtk) |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
