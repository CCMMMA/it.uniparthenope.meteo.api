"""Disk-cache management helpers for generated API resources."""

#################################################
#   
#   Università Degli Studi di Napoli Parthenope 
#
#
# Author: 
#    Dario Caramiello   
#
#################################################

from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import time

from core.cache_keys import make_cache_key
from core.Logger import logger

class ManageDiskCache:
    """Service or helper that encapsulates manage disk cache behavior."""

    _KNOWN_EXTENSIONS = (".json", ".csv", ".png")

    def __init__(self, path_diskcache):
        """Initialize manage disk cache state."""
        self.base_diskcache = Path(path_diskcache)
        # Preserve the historical misspelled attribute for external callers.
        self.base_diskcace = path_diskcache

    def _daily_cache_dir(self, day=None):
        """Internal helper for daily cache dir."""
        day = day or datetime.today()
        return self.base_diskcache / str(day.year) / str(day.month) / str(day.day)

    def _iter_daily_cache_dirs(self):
        """Yield every existing daily cache directory."""
        if not self.base_diskcache.exists():
            return

        for year_dir in self.base_diskcache.iterdir():
            if not year_dir.is_dir():
                continue
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                for day_dir in month_dir.iterdir():
                    if day_dir.is_dir():
                        yield day_dir

    def _cache_key(self, request=None, cache_key_source=None):
        """Return the stable disk-cache key derived from a request URL or explicit source."""
        return make_cache_key(request, cache_key_source)

    def _cache_file(self, request, extension, day=None, cache_key_source=None):
        """Return the full cache-file path for a request and extension."""
        return self._daily_cache_dir(day) / f"{self._cache_key(request, cache_key_source=cache_key_source)}{extension}"

    def _find_cached_file(self, request, cache_key_source=None):
        """Return the first existing cache file for the current day."""
        for extension in self._KNOWN_EXTENSIONS:
            candidate = self._cache_file(request, extension, cache_key_source=cache_key_source)
            if candidate.exists():
                return candidate
        return None
    
    def get(self, request, ttl, path_archive=None, flag_diskcache=True, cache_key_source=None):
        """Implement get for manage disk cache."""
        if isinstance(path_archive, bool) and flag_diskcache is True:
            flag_diskcache = path_archive
            path_archive = None

        if not flag_diskcache:
            return None

        cached_file = self._find_cached_file(request, cache_key_source=cache_key_source)
        if cached_file is None:
            return None

        try:
            cached_mtime = cached_file.stat().st_mtime
        except FileNotFoundError:
            # Another worker may invalidate an entry between lookup and stat.
            return None

        if path_archive:
            try:
                archive_mtime = Path(path_archive).stat().st_mtime
            except FileNotFoundError:
                archive_mtime = None
            if archive_mtime is not None and archive_mtime > cached_mtime:
                logger.info("Disk cache file '%s' predates its archive source", cached_file)
                cached_file.unlink(missing_ok=True)
                return None

        if (time.time() - cached_mtime) > ttl:
            logger.info("Disk cache file '%s' expired", cached_file)
            cached_file.unlink(missing_ok=True)
            return None

        try:
            if cached_file.suffix in {".json", ".csv"}:
                with cached_file.open("r", encoding="utf-8") as file:
                    return json.load(file)
            return cached_file.read_bytes()
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            # Treat truncated or concurrently removed entries as ordinary misses.
            logger.warning("Unable to read disk cache file '%s': %s", cached_file, exc)
            cached_file.unlink(missing_ok=True)
            return None

    @staticmethod
    def _write_atomic(cache_file, payload, *, binary):
        """Write a complete cache entry before atomically publishing its path."""
        mode = "wb" if binary else "w"
        kwargs = {} if binary else {"encoding": "utf-8"}
        descriptor, temporary_name = tempfile.mkstemp(
            dir=cache_file.parent,
            prefix=f".{cache_file.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(descriptor, mode, **kwargs) as file:
                if binary:
                    file.write(payload)
                else:
                    json.dump(payload, file)
            os.replace(temporary_name, cache_file)
        except BaseException:
            Path(temporary_name).unlink(missing_ok=True)
            raise

    # type --> plot - json - csv
    def set(self, request, res, type_file='plot', flag_diskcache=True, cache_key_source=None): 
        """Implement set for manage disk cache."""
        if not flag_diskcache:
            return

        if type_file == 'plot':
            extension = '.png'
        elif type_file == 'csv':
            extension = '.csv'
        else:
            extension = '.json'

        cache_dir = self._daily_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_file(request, extension, cache_key_source=cache_key_source)

        if extension in {'.json', '.csv'}:
            self._write_atomic(cache_file, res, binary=False)
            return

        payload = res.encode('utf-8') if isinstance(res, str) else res
        self._write_atomic(cache_file, payload, binary=True)

    def delete(self, request=None, flag_diskcache=True, cache_key_source=None):
        """Delete cached files matching a request URL or canonical cache key."""
        if not flag_diskcache:
            return 0

        deleted = 0
        for cache_dir in self._iter_daily_cache_dirs() or []:
            for extension in self._KNOWN_EXTENSIONS:
                candidate = cache_dir / f"{self._cache_key(request, cache_key_source=cache_key_source)}{extension}"
                if candidate.exists():
                    candidate.unlink()
                    deleted += 1
        return deleted
