"""High-throughput request popularity tracking for cache-aware product routes."""

from __future__ import annotations

import contextlib
import json
import threading
import time
from pathlib import Path

from core.atomic_io import write_atomic

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX development hosts
    fcntl = None


class RequestPopularityTracker:
    """Track and persist the most frequently requested forecast and time-series signatures.

    Every worker process owns one tracker but all of them share one file. A
    process therefore keeps only the increments it has not persisted yet and
    adds them to the file's current contents on flush, so the persisted counts
    are the totals across workers rather than those of the last writer.
    """

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
        # Merged view: the last state read from disk plus this process's
        # pending increments.
        self._records = {}
        # Increments recorded since the last flush, keyed like _records.
        self._pending = {}
        self._loaded_mtime_ns = None
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

    @contextlib.contextmanager
    def _file_lock(self):
        """Serialize the read-merge-write cycle across worker processes."""
        if fcntl is None:
            yield
            return
        with open(self.path.with_name(self.path.name + ".lock"), "a") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def _read_disk(self):
        """Return the persisted records keyed by signature, tolerating a bad file."""
        try:
            self._loaded_mtime_ns = self.path.stat().st_mtime_ns
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            records = payload.get("records", [])
        except FileNotFoundError:
            self._loaded_mtime_ns = None
            return {}
        except (OSError, ValueError, AttributeError):
            return {}

        loaded = {}
        for record in records:
            try:
                key = self._signature_key(
                    record["endpoint"],
                    record["prod"],
                    record["place"],
                    record["params"],
                )
                record["count"] = int(record["count"])
            except (KeyError, TypeError, ValueError, AttributeError):
                continue
            loaded[key] = record
        return loaded

    def _with_pending(self, records):
        """Add this process's unpersisted increments to a set of disk records."""
        for key, delta in self._pending.items():
            record = records.get(key)
            if record is None:
                records[key] = dict(delta)
                continue
            record["count"] += delta["count"]
            record["first_seen"] = min(record.get("first_seen", delta["first_seen"]), delta["first_seen"])
            record["last_seen"] = max(record.get("last_seen", delta["last_seen"]), delta["last_seen"])
        return records

    def _load(self):
        """Replace the merged view with the persisted state plus pending increments."""
        self._records = self._with_pending(self._read_disk())

    def _refresh_unlocked(self):
        """Pick up counters flushed by other worker processes since the last read."""
        try:
            current_mtime_ns = self.path.stat().st_mtime_ns
        except OSError:
            current_mtime_ns = None
        if current_mtime_ns != self._loaded_mtime_ns:
            self._load()

    def _flush_unlocked(self):
        """Merge pending increments into the shared file and publish it atomically."""
        with self._file_lock():
            merged = self._with_pending(self._read_disk())
            payload = {
                "records": sorted(
                    merged.values(),
                    key=lambda item: (-item["count"], -item["last_seen"]),
                )
            }
            serialized = json.dumps(payload, sort_keys=True)
            write_atomic(self.path, lambda file: file.write(serialized))
            try:
                self._loaded_mtime_ns = self.path.stat().st_mtime_ns
            except OSError:
                self._loaded_mtime_ns = None
        self._records = merged
        self._pending = {}
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
            for store in (self._records, self._pending):
                record = store.get(key)
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
                    store[key] = record

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
            self._refresh_unlocked()
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
            self._refresh_unlocked()
            return [
                dict(record)
                for record in self._records.values()
                if (prod is None or record["prod"] == prod)
                and (endpoint is None or record["endpoint"] == endpoint)
                and (place is None or record["place"] == place)
            ]
