"""Typed container for process-wide services initialized with the Flask app."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.GribServices import GribServices
from core.ManageDiskCache import ManageDiskCache
from core.MeteoServices import MeteoServices
from core.RequestPopularityTracker import RequestPopularityTracker
from core.Tiles import Tiles


@dataclass(frozen=True)
class RuntimeServices:
    """Collect reusable runtime dependencies behind one application extension."""

    memory_cache: Any
    memory_cache_enabled: bool
    disk_cache: ManageDiskCache
    disk_cache_enabled: bool
    disk_cache_ttl: int
    meteo: MeteoServices
    grib: GribServices
    tiles: Tiles
    popularity: RequestPopularityTracker
