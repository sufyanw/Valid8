from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from app.config import PROJECT_ROOT


class LocationRecord(BaseModel):
    id: str
    code: str
    name: str
    city: str
    state: str
    type: str
    lat: float
    lng: float
    aliases: list[str] = []

    def search_blob(self) -> str:
        return " ".join(
            [
                self.code,
                self.name,
                self.city,
                self.state,
                self.type,
                *self.aliases,
            ]
        ).lower()


@lru_cache
def load_locations() -> tuple[LocationRecord, ...]:
    path = PROJECT_ROOT / "app" / "data" / "locations.json"
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    return tuple(LocationRecord.model_validate(item) for item in data["locations"])


def search_locations(query: str, limit: int = 8) -> list[LocationRecord]:
    normalized = query.strip().lower()
    locations = load_locations()

    if not normalized:
        popular_codes = {"NYC", "LAX", "ORD", "ATL", "DFW", "SFO", "SEA", "DEN"}
        return [location for location in locations if location.code in popular_codes][:limit]

    scored: list[tuple[int, LocationRecord]] = []
    for location in locations:
        code = location.code.lower()
        city = location.city.lower()
        name = location.name.lower()
        blob = location.search_blob()
        if code == normalized:
            score = 100
        elif code.startswith(normalized):
            score = 90
        elif city.startswith(normalized):
            score = 80
        elif name.startswith(normalized):
            score = 70
        elif normalized in blob:
            score = 50
        else:
            continue
        scored.append((score, location))

    scored.sort(key=lambda item: (-item[0], item[1].city, item[1].code))
    return [location for _, location in scored[:limit]]
