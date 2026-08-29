"""Read and filter the bundled NEA e-waste collection-point dataset."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATASET_URL = "https://data.gov.sg/datasets/d_db40d004afeb5a7f0f555fdcc34934cc/view"

CATEGORY_LABELS = (
    "All e-waste points",
    "ICT equipment, batteries & lamps",
    "Small household appliances & electronics",
    "Batteries & lamps",
)


@dataclass(frozen=True)
class EwastePoint:
    name: str
    address: str
    building: str | None
    postal_code: str | None
    accepted_items: str
    official_url: str | None
    latitude: float
    longitude: float

    @property
    def display_name(self) -> str:
        return self.building or self.name

    @property
    def openstreetmap_url(self) -> str:
        return (
            "https://www.openstreetmap.org/"
            f"?mlat={self.latitude:.6f}&mlon={self.longitude:.6f}"
            f"#map=17/{self.latitude:.6f}/{self.longitude:.6f}"
        )


@lru_cache
def load_ewaste_points() -> tuple[EwastePoint, ...]:
    path = Path(__file__).parent / "data" / "nea_ewaste_points.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    return tuple(EwastePoint(**row) for row in rows)


def _matches_category(point: EwastePoint, category: str) -> bool:
    description = point.accepted_items.lower()
    if category == "ICT equipment, batteries & lamps":
        return "ict" in description or "all regulated" in description
    if category == "Small household appliances & electronics":
        return "non-regulated" in description
    if category == "Batteries & lamps":
        return "batter" in description or "lamp" in description
    return True


def find_ewaste_points(category: str, search: str = "", limit: int = 5) -> list[EwastePoint]:
    """Return collection points filtered by accepted items and optional location text."""
    query = search.casefold().strip()
    matches = [point for point in load_ewaste_points() if _matches_category(point, category)]
    if query:
        matches = [
            point
            for point in matches
            if query
            in " ".join(
                filter(None, (point.name, point.building, point.address, point.postal_code))
            ).casefold()
        ]
    return sorted(matches, key=lambda point: (point.display_name, point.address))[:limit]
