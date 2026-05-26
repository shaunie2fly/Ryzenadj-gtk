#!/bin/bash
# uninstall

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./uninstall.sh)"
  exit 1
fi

echo "==> Removing ryzenadj-gtk..."

rm -rf /usr/share/ryzenadj-gtk
rm -f  /usr/bin/ryzenadj-gtk
rm -f  /usr/share/applications/com.marley.ryzenadj-gtk.desktop
for size in 256 512; do
    rm -f "/usr/share/icons/hicolor/${size}x${size}/apps/com.marley.ryzenadj-gtk.png"
done
rm -f  /usr/share/icons/hicolor/scalable/apps/com.marley.ryzenadj-gtk.svg 2>/dev/null || true

# Disable and remove systemd service
echo "  -> Removing systemd service..."
systemctl disable ryzenadj-gtk-apply.service 2>/dev/null || true
rm -f /usr/lib/systemd/system/ryzenadj-gtk-apply.service
systemctl daemon-reload

# Remove system settings
rm -rf /etc/ryzenadj-gtk

# Remove secure sudoers drop-in file (installed by install.sh or AUR package)
rm -f /etc/sudoers.d/ryzenadj-gtk
echo "     Sudoers rules removed (if present)."

update-desktop-database -q 2>/dev/null || true
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true

echo "==> Uninstall complete."
