#!/usr/bin/env python3
"""Application entry point"""
import sys
import warnings

# Auto-fix xdg-desktop-portal graphical-session dependency if it blocks GUI startup
try:
    import os
    import subprocess
    if os.path.exists('/run/systemd/container') or os.path.exists('/run/systemd/system'):
        res = subprocess.run(
            ["systemctl", "--user", "show", "xdg-desktop-portal.service", "-p", "FragmentPath", "-p", "Requisite"],
            capture_output=True, text=True, check=True
        )
        props = {}
        for line in res.stdout.strip().split('\n'):
            if '=' in line:
                k, v = line.split('=', 1)
                props[k] = v
        
        fragment_path = props.get("FragmentPath")
        requisite = props.get("Requisite", "")
        
        if fragment_path and os.path.exists(fragment_path) and "graphical-session.target" in requisite:
            res_active = subprocess.run(
                ["systemctl", "--user", "is-active", "graphical-session.target"],
                capture_output=True, text=True
            )
            if res_active.stdout.strip() != "active":
                user_config_dir = os.path.expanduser("~/.config/systemd/user")
                os.makedirs(user_config_dir, exist_ok=True)
                target_path = os.path.join(user_config_dir, "xdg-desktop-portal.service")
                
                with open(fragment_path, 'r') as f:
                    lines = f.readlines()
                
                new_lines = []
                modified = False
                for line in lines:
                    if line.strip().startswith("Requisite="):
                        parts = line.split("=", 1)
                        targets = parts[1].split()
                        filtered = [t for t in targets if t != "graphical-session.target"]
                        if len(filtered) < len(targets):
                            modified = True
                            if filtered:
                                new_lines.append(f"Requisite={' '.join(filtered)}\n")
                            continue
                    new_lines.append(line)
                
                if modified:
                    with open(target_path, 'w') as f:
                        f.writelines(new_lines)
                    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
                    subprocess.run(["systemctl", "--user", "restart", "xdg-desktop-portal.service"], capture_output=True)
except Exception:
    pass

warnings.filterwarnings("ignore", category=DeprecationWarning)

import init_gi  # noqa: F401, E402
from main import RyzenadjApp  # noqa: E402

# Initialize and run the app

if __name__ == "__main__":
    app = RyzenadjApp()
    sys.exit(app.run(sys.argv))


