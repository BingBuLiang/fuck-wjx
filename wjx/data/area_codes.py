"""Administrative area code data loader."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

_DATA_PATH = Path(__file__).with_name("area_codes_2022.json")


def load_area_codes() -> List[Dict[str, Any]]:
    """Load province/city area codes from bundled JSON."""
    try:
        with _DATA_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return []
    provinces = payload.get("provinces")
    return provinces if isinstance(provinces, list) else []
