"""Support list loader for proxy area codes."""
from __future__ import annotations

from pathlib import Path
from typing import Set, Tuple

_DATA_PATH = Path(__file__).with_name("area.txt")


def load_supported_area_codes() -> Tuple[Set[str], bool]:
    """Return supported area codes from area.txt and whether it contains 'all'."""
    codes: Set[str] = set()
    has_all = False
    try:
        lines = _DATA_PATH.read_text(encoding="utf-8").splitlines()
    except Exception:
        return codes, has_all

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        code = str(parts[-1]).strip()
        if not code:
            continue
        if code.lower() == "all":
            has_all = True
            continue
        if code.isdigit() and len(code) == 6:
            codes.add(code)
    return codes, has_all
