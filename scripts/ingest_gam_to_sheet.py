#!/usr/bin/env python3
"""CLI entry: run from repo root as `python scripts/ingest_gam_to_sheet.py`."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gam_ingestion.run import main

if __name__ == "__main__":
    raise SystemExit(main())
