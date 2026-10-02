from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from csvguard.cli import main

raise SystemExit(main(sys.argv[1:]))
