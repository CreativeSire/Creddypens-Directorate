from __future__ import annotations

import sys
from pathlib import Path


THIS_FILE = Path(__file__).resolve()
BACKEND_ROOT = THIS_FILE.parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402
