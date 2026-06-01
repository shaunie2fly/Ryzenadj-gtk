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

# stop and remove the boot service if it was running
echo "  -> Removing systemd service..."
systemctl disable ryzenadj-gtk-apply.service 2>/dev/null || true
rm -f /usr/lib/systemd/system/ryzenadj-gtk-apply.service
systemctl daemon-reload

# delete the config folder (this removes their saved settings and profiles)
echo "  -> Removing system settings directory (/etc/ryzenadj-gtk)..."
echo "     WARNING: This will delete any saved boot-apply settings."
rm -rf /etc/ryzenadj-gtk

# remove passwordless sudo access
rm -f /etc/sudoers.d/ryzenadj-gtk
echo "     Sudoers rules removed (if present)."

update-desktop-database -q 2>/dev/null || true
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true

echo "==> Uninstall complete."
