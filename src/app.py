#!/usr/bin/env python3
"""Application entry point"""
import sys
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import init_gi  # load correct library versions
from main import RyzenadjApp

# Initialize and run the app

if __name__ == "__main__":
    app = RyzenadjApp()
    sys.exit(app.run(sys.argv))

