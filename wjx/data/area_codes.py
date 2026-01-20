"""Administrative area code data loader."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from wjx.data.area_support import load_supported_area_codes

_DATA_PATH = Path(__file__).with_name("area_codes_2022.json")


def load_area_codes(supported_only: bool = False) -> List[Dict[str, Any]]:
    """Load province/city area codes from bundled JSON."""
    try:
        with _DATA_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return []
    provinces = payload.get("provinces")
    if not isinstance(provinces, list):
        return []
    if not supported_only:
        return provinces

    supported_codes, _ = load_supported_area_codes()
    if not supported_codes:
        return []

    filtered: List[Dict[str, Any]] = []
    for province in provinces:
        if not isinstance(province, dict):
            continue
        province_code = str(province.get("code") or "")
        cities = province.get("cities") or []
        if not isinstance(cities, list):
            cities = []
        supported_cities = [
            city
            for city in cities
            if isinstance(city, dict) and str(city.get("code") or "") in supported_codes
        ]
        if province_code not in supported_codes and not supported_cities:
            continue
        filtered.append({**province, "cities": supported_cities})
    return filtered
