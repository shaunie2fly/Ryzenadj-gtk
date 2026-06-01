#!/bin/bash
# ryzenadj-gtk installer
# this installs the app the same way the arch pkgbuild does
# run with: sudo ./install.sh

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./install.sh)"
  exit 1
fi

echo "==> Installing ryzenadj-gtk..."

INSTALL_DIR="/usr/share/ryzenadj-gtk"
BIN_DIR="/usr/bin"
APP_DIR="/usr/share/applications"

# make the folders we need
mkdir -p "$INSTALL_DIR"
mkdir -p "$APP_DIR"

# copy python files and assets and set up permissions so they can run
echo "  -> Copying Python files and assets..."
cp src/*.py "$INSTALL_DIR/"
cp -r src/assets "$INSTALL_DIR/"
chmod 644 "$INSTALL_DIR"/*.py
chmod 755 "$INSTALL_DIR/app.py"
find "$INSTALL_DIR/assets" -type d -exec chmod 755 {} +
find "$INSTALL_DIR/assets" -type f -exec chmod 644 {} +

# copy the app icons to the system icon folder
for size in 256 512; do
    ICON_DIR="/usr/share/icons/hicolor/${size}x${size}/apps"
    mkdir -p "$ICON_DIR"
    cp src/assets/com.marley.ryzenadj-gtk.png "$ICON_DIR/com.marley.ryzenadj-gtk.png"
    chmod 644 "$ICON_DIR/com.marley.ryzenadj-gtk.png"
done

# Install desktop entry
echo "  -> Installing .desktop file..."
cp com.marley.ryzenadj-gtk.desktop "$APP_DIR/com.marley.ryzenadj-gtk.desktop"
chmod 644 "$APP_DIR/com.marley.ryzenadj-gtk.desktop"

# create the /usr/bin launcher so we can run the app with 'ryzenadj-gtk'
echo "  -> Creating launcher..."
cat > "$BIN_DIR/ryzenadj-gtk" << EOF
#!/bin/sh
export PYTHONPATH="$INSTALL_DIR:\$PYTHONPATH"
exec python3 "$INSTALL_DIR/app.py" "\$@"
EOF
chmod 755 "$BIN_DIR/ryzenadj-gtk"

# update desktop databases so the app shows up in menus
update-desktop-database -q 2>/dev/null || true
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true

# put the systemd service file in place for applying settings on boot
echo "  -> Installing systemd service..."
cp ryzenadj-gtk-apply.service /usr/lib/systemd/system/ryzenadj-gtk-apply.service
chmod 644 /usr/lib/systemd/system/ryzenadj-gtk-apply.service
systemctl daemon-reload

# add passwordless sudo entries so the app can change power settings without asking for password
# (per-user rules for manual installs; PKGBUILD uses %wheel group for packaged multi-user setups)
echo "  -> Configuring secure passwordless sudo for ryzenadj & systemctl..."
SUDOERS_FILE="/etc/sudoers.d/ryzenadj-gtk"
TEMP_SUDOERS=$(mktemp)

if [ -n "$SUDO_USER" ]; then
    cat <<EOF > "$TEMP_SUDOERS"
$SUDO_USER ALL=(ALL) NOPASSWD: /usr/bin/ryzenadj
$SUDO_USER ALL=(ALL) NOPASSWD: /usr/local/bin/ryzenadj
$SUDO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl enable ryzenadj-gtk-apply.service
$SUDO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl disable ryzenadj-gtk-apply.service
$SUDO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl enable --now ryzenadj-gtk-apply.service
$SUDO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl disable --now ryzenadj-gtk-apply.service
$SUDO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-enabled ryzenadj-gtk-apply.service
$SUDO_USER ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/class/drm/card*/device/pp_od_clk_voltage
$SUDO_USER ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/class/drm/card*/device/power_dpm_force_performance_level
EOF
else
    rm -f "$TEMP_SUDOERS"
    echo "" >&2
    echo "  ERROR: Could not determine the target user (\$SUDO_USER is unset)." >&2
    echo "  Please run this script with 'sudo ./install.sh' as your normal user," >&2
    echo "  not as root directly or via 'su -'." >&2
    echo "  Sudoers rules were NOT installed. You can run install.sh again, or" >&2
    echo "  use the 'Grant Background Access' button inside the app." >&2
    echo "" >&2
fi

# make sure the sudoers file is formatted right before writing it (so we don't break sudo!)
if [ -f "$TEMP_SUDOERS" ]; then
    if visudo -cf "$TEMP_SUDOERS" >/dev/null 2>&1; then
        mv "$TEMP_SUDOERS" "$SUDOERS_FILE"
        chmod 440 "$SUDOERS_FILE"
        chown root:root "$SUDOERS_FILE"
        echo "     Sudoers drop-in configured successfully. Changes usually take effect immediately."
        echo "     If you still get prompted for a password, a reboot will ensure everything is active."
    else
        rm -f "$TEMP_SUDOERS"
        echo "     WARNING: Sudoers rule validation failed! Passwordless sudo was not configured." >&2
    fi
fi

# make /etc/ryzenadj-gtk writable by the user so we can save settings without root
echo "  -> Creating system config directory..."
mkdir -p /etc/ryzenadj-gtk
if [ -n "$SUDO_USER" ]; then
    chown -R "$SUDO_USER:" /etc/ryzenadj-gtk
fi
chmod 755 /etc/ryzenadj-gtk

echo ""
echo "==> Installation complete!"
echo "    Launch 'Ryzenadj-gtk' from your application menu, or run: ryzenadj-gtk"
echo ""
# Only prompt for Enter when running interactively (not in AUR helpers / CI)
if [ -t 0 ]; then
    read -p "Press Enter to exit..."
fi
