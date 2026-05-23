#!/bin/bash
# Quick test runner for ryzenadj-gtk
# Tests imports without launching the full GUI

set -e
cd "$(dirname "$0")"

echo "==> Testing Python imports..."
python3 -c "
import sys
sys.path.insert(0, '.')
import init_gi
from gi.repository import Gtk, Adw, Gdk, Pango
print('  GTK4/Adwaita OK')
import ryzen
print(f'  ryzen.py OK - {len(ryzen.SETTINGS_PARAMS)} settable params')
import styles
print(f'  styles.py OK - CSS length: {len(styles.CSS)} chars')
import ui
print('  ui.py OK')
import main
print('  main.py OK')
print('')
print('==> All imports passed!')
"

echo ""
echo "==> To run the full app:"
echo "    python3 app.py"
echo "    (ryzenadj needs sudo access)"
