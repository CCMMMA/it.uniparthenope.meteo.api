"""High-throughput request popularity tracking for cache-aware product routes."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path


class RequestPopularityTracker:
    """Track and persist the most frequently requested forecast and time-series signatures."""

    def __init__(
        self,
        path,
        top_limit=25,
        flush_every=100,
        flush_interval_seconds=10.0,
    ):
        """Initialize in-memory counters and load any persisted state."""
        self.path = Path(path)
        self.top_limit = int(top_limit)
        self.flush_every = max(1, int(flush_every))
        self.flush_interval_seconds = float(flush_interval_seconds)
        self._lock = threading.RLock()
        self._records = {}
        self._dirty_count = 0
        self._last_flush = time.time()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    @staticmethod
    def _signature_key(endpoint, prod, place, normalized_params):
        """Return a stable unique key for one normalized request signature."""
        return "|".join(
            [
                endpoint,
                str(prod),
                str(place),
                str(normalized_params.get("date") or ""),
                str(int(normalized_params.get("hours", 0))),
                str(int(normalized_params.get("step", 1))),
                str(normalized_params.get("opt") or ""),
                str(normalized_params.get("filter") or ""),
            ]
        )

    def _load(self):
        """Load persisted popularity counters from disk when available."""
        if not self.path.exists():
            return

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return

        records = payload.get("records", [])
        for record in records:
            key = self._signature_key(
                record["endpoint"],
                record["prod"],
                record["place"],
                record["params"],
            )
            self._records[key] = record

    def _flush_unlocked(self):
        """Persist the current counters atomically."""
        payload = {
            "records": sorted(
                self._records.values(),
                key=lambda item: (-item["count"], -item["last_seen"]),
            )
        }
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        temp_path.replace(self.path)
        self._dirty_count = 0
        self._last_flush = time.time()

    def flush(self):
        """Persist any dirty counters to disk."""
        with self._lock:
            if self._dirty_count:
                self._flush_unlocked()

    def record(self, endpoint, prod, place, normalized_params):
        """Record one forecast or time-series request."""
        key = self._signature_key(endpoint, prod, place, normalized_params)
        now = time.time()

        with self._lock:
            record = self._records.get(key)
            if record is None:
                record = {
                    "endpoint": endpoint,
                    "prod": prod,
                    "place": place,
                    "params": dict(normalized_params),
                    "count": 0,
                    "first_seen": now,
                    "last_seen": now,
                }
                self._records[key] = record

            record["count"] += 1
            record["last_seen"] = now

            self._dirty_count += 1
            if (
                self._dirty_count >= self.flush_every
                or (now - self._last_flush) >= self.flush_interval_seconds
            ):
                self._flush_unlocked()

    def top_requests(self, prod=None, endpoint=None, place=None, limit=None):
        """Return the most popular normalized request signatures."""
        with self._lock:
            items = [
                dict(record)
                for record in self._records.values()
                if (prod is None or record["prod"] == prod)
                and (endpoint is None or record["endpoint"] == endpoint)
                and (place is None or record["place"] == place)
            ]

        items.sort(key=lambda item: (-item["count"], -item["last_seen"]))
        return items[: limit or self.top_limit]

    def matching_requests(self, prod=None, endpoint=None, place=None):
        """Return all normalized request signatures matching the provided filters."""
        with self._lock:
            return [
                dict(record)
                for record in self._records.values()
                if (prod is None or record["prod"] == prod)
                and (endpoint is None or record["endpoint"] == endpoint)
                and (place is None or record["place"] == place)
            ]
