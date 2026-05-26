#!/usr/bin/env python3
"""entry"""
import sys
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import init_gi  # sets gi.require_version calls
from gi.repository import GLib
from main import RyzenadjApp

# Run application

if __name__ == "__main__":
    app = RyzenadjApp()
    sys.exit(app.run(sys.argv))
