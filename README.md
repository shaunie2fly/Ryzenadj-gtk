# ryzenadj-gtk

Just a basic GTK4/Libadwaita GUI wrapper for [ryzenadj](https://github.com/FlyGoat/RyzenAdj). If you want to use it, go ahead.

![ryzenadj-gtk screenshot](ryzenadj-gtk.png)

---

## What it does

*   **Dashboard**: Shows power limits, currents, and temperatures.
*   **Undervolting**: Core and iGPU Curve Optimizer sliders (-30 to +30).
*   **Power limits**: Sliders for STAPM, PPT, TDC, and EDC.
*   **Sleep restore**: Automatically re-applies your settings 3 seconds after waking from sleep.
*   **Battery/AC profiles**: Swaps profiles when you plug/unplug the charger.
*   **Lockdown detection**: Shows a warning card if Secure Boot or Kernel Lockdown is blocking ryzenadj.
*   **Persistence**: Periodically re-writes settings in the background so system limits don't overwrite them.
*   **Real-time clocks**: Shows CPU averages and GPU clock speeds in the badges.

---

## Simple Settings Guide (Examples)

If you don't know what these are, here are some quick examples:

*   **STAPM (Sustained Power)**: How much power (in Watts) your CPU uses. Setting it to `15W` keeps the laptop quiet on battery, `28W` gives more performance on charger.
*   **Tctl Temperature Limit**: Thermal limit. Setting it to `85°C` keeps the laptop cool, letting it hit `95°C` gives more speed but gets hotter.
*   **Curve Optimizer (Undervolting)**: Uses less voltage. Setting it to `-15` saves battery and reduces heat.
*   **iGPU Clock**: Graphics speed. Lock it to `800 MHz` to save power, or run it at `1800 MHz` for gaming.

---

## 🔒 Security & Sudo Access

`ryzenadj` requires root privileges to read and write directly to your motherboard's memory registers. To prevent the GUI from constantly interrupting you with password prompts every 1 second while monitoring, **Ryzenadj-gtk automatically configures passwordless sudo for the ryzenadj command during installation.**

When you install via `makepkg -si` or `./install.sh`, a strict, locked-down rule is added to `/etc/sudoers.d/ryzenadj-gtk`. This rule *only* allows the execution of `ryzenadj` and specific `systemctl` commands (for the boot-apply service) without a password. The GUI application itself continues to run securely under your normal, unprivileged user account.

---

## Requirements

*   Python 3.11+
*   GTK 4 & Libadwaita
*   `python-gobject`
*   `ryzenadj` installed and set up with passwordless sudo

---

## Installation & Running

### Arch Linux (PKGBUILD)
Clone the repository and build the package:
```bash
git clone https://github.com/marleylinux/Ryzenadj-gtk
cd Ryzenadj-gtk
makepkg -si
```

### Manual Installation (Other Distributions)
Run the script to install:
```bash
sudo ./install.sh
```
Launch **Ryzenadj-gtk** from your desktop applications menu, or run `ryzenadj-gtk`.

---

## Uninstall

```bash
sudo ./uninstall.sh
```

---

## License

GPL-3.0
