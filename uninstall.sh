#!/bin/bash
# ryzenadj-gtk Uninstall Script
# Run with: sudo ./uninstall.sh

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./uninstall.sh)"
  exit 1
fi

echo "==> Removing ryzenadj-gtk..."

rm -rf /usr/share/ryzenadj-gtk
rm -f  /usr/bin/ryzenadj-gtk
rm -f  /usr/share/applications/com.marley.ryzenadj-gtk.desktop
rm -f  /usr/share/icons/hicolor/256x256/apps/com.marley.ryzenadj-gtk.png
rm -f  /usr/share/icons/hicolor/scalable/apps/com.marley.ryzenadj-gtk.svg

# Disable and remove systemd service
echo "  -> Removing systemd service..."
systemctl disable ryzenadj-gtk-apply.service 2>/dev/null || true
rm -f /usr/lib/systemd/system/ryzenadj-gtk-apply.service
systemctl daemon-reload

# Remove system settings
rm -rf /etc/ryzenadj-gtk

# Remove secure sudoers drop-in file
rm -f /etc/sudoers.d/ryzenadj-gtk

update-desktop-database -q 2>/dev/null || true
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true

echo "==> Uninstall complete."
