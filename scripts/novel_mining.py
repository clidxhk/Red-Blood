#!/usr/bin/env python3
"""
Novel Mining CLI entrypoint wrapper.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from scripts.novel_mining.cli import main

if __name__ == "__main__":
    main()
