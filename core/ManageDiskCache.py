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

import json
import os
import time
from pathlib import Path
from datetime import datetime
import hashlib  # hash function for 128bit encryption

from core.Logger import logger

class ManageDiskCache:
    """Service or helper that encapsulates manage disk cache behavior."""

    _KNOWN_EXTENSIONS = (".json", ".csv", ".png")

    def __init__(self, path_diskcache):
        """Initialize manage disk cache state."""
        self.base_diskcace = path_diskcache

    def _daily_cache_dir(self, day=None):
        """Internal helper for daily cache dir."""
        day = day or datetime.today()
        return Path(self.base_diskcace) / str(day.year) / str(day.month) / str(day.day)

    def _cache_key(self, request):
        """Return the stable disk-cache key derived from the request URL."""
        return hashlib.md5(request.url.encode('utf-8')).hexdigest()

    def _cache_file(self, request, extension, day=None):
        """Return the full cache-file path for a request and extension."""
        return self._daily_cache_dir(day) / f"{self._cache_key(request)}{extension}"

    def _find_cached_file(self, request):
        """Return the first existing cache file for the current day."""
        for extension in self._KNOWN_EXTENSIONS:
            candidate = self._cache_file(request, extension)
            if candidate.exists():
                return candidate
        return None
    
    def get(self, request, ttl, path_archive=None, flag_diskcache=True):
        """Implement get for manage disk cache."""
        if isinstance(path_archive, bool) and flag_diskcache is True:
            flag_diskcache = path_archive
            path_archive = None

        if not flag_diskcache:
            return None

        cached_file = self._find_cached_file(request)
        if cached_file is None:
            return None

        final_path = str(cached_file)

        if path_archive and os.path.exists(path_archive):
            if os.path.getmtime(path_archive) > os.path.getmtime(final_path):
                logger.info("DISK 1 : File '%s' older than archive source, deleting it", final_path)
                os.remove(final_path)
                return None

        if (time.time() - os.path.getmtime(final_path)) > ttl:
            logger.info("DISK 1 : File '%s' expired, deleting it", final_path)
            os.remove(final_path)
            return None

        if cached_file.suffix in {".json", ".csv"}:
            with open(cached_file, 'r', encoding='utf-8') as file:
                return json.load(file)

        with open(cached_file, 'rb') as file:
            return file.read()

    # type --> plot - json - csv
    def set(self, request, res, type_file='plot', flag_diskcache=True): 
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
        cache_file = self._cache_file(request, extension)

        if extension in {'.json', '.csv'}:
            with open(cache_file, 'w', encoding='utf-8') as file:
                json.dump(res, file)
            return

        payload = res.encode('utf-8') if isinstance(res, str) else res
        with open(cache_file, 'wb') as file:
            file.write(payload)
