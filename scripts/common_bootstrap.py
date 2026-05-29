from __future__ import annotations

import sys
from pathlib import Path


def bootstrap_project_root(levels_up: int = 2) -> Path:
    root = Path(__file__).resolve().parents[levels_up]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root
