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
from datetime import datetime, timedelta
import hashlib  # hash function for 128bit encryption

from core.Logger import logger

class ManageDiskCache:
    """Service or helper that encapsulates manage disk cache behavior."""

    def __init__(self, path_diskcache):
        """Initialize manage disk cache state."""
        self.base_diskcace = path_diskcache

    def _daily_cache_dir(self, day=None):
        """Internal helper for daily cache dir."""
        day = day or datetime.today()
        return Path(self.base_diskcace) / str(day.year) / str(day.month) / str(day.day)
    
    def get(self, request, ttl, path_archive=None, flag_diskcache=True):
        """Implement get for manage disk cache."""
        res_out = None

        if not flag_diskcache:
            return res_out

        path = self._daily_cache_dir()

        m = hashlib.md5(request.url.encode('utf-8'))

        if m is not None:
            hex_file = f"{m.hexdigest()}.*"
            cached_file = next(path.glob(hex_file), None)

            if cached_file is not None:
                final_path = str(cached_file)

                # Check if is valid respect to the date of ARCHIVE file 
                if path_archive is not None: 
                    if os.path.getmtime(path_archive) > os.path.getmtime(final_path):
                        logger.info(f"DISK 1 : File '{final_path}' not consistent respect to ARCHIVE file !")
                        os.remove(final_path)
                        logger.info(f"DISK 1 : File '{final_path}' deleted !")
                        return res_out

                # Check ttl of file , if file is old then ttl hours , must be re-created
                # logger.info(f"DISK 1 : delta time expired {(time.time() - os.path.getmtime(final_path))} !")
                if (time.time() - os.path.getmtime(final_path)) > ttl: 
                    logger.info(f"DISK 1 : File '{final_path}' expired !")
                    os.remove(final_path)
                    logger.info(f"DISK 1 : File '{final_path}' deleted !")
                    return res_out

                if cached_file.suffix in {".json", ".csv"}:
                    with open(cached_file, 'r') as file:
                        res_out = json.load(file)
                else:
                    # .png case  or .csv case
                    with open(cached_file, 'rb') as file:
                        res_out = file.read()
        return res_out

    # type --> plot - json - csv
    def set(self, request, res, type_file='plot'): 
        """Implement set for manage disk cache."""
        res_out = None
        m = hashlib.md5(request.url.encode('utf-8'))

        if m is not None:

            if type_file == 'plot':
                extension = '.png'
            elif type_file == 'csv':
                extension = '.csv'
            else:
                extension = '.json'
            
            cache_dir = self._daily_cache_dir()
            cache_dir.mkdir(parents=True, exist_ok=True)

            with open(cache_dir / f"{m.hexdigest()}{extension}", 'w') as file:
                file.write(json.dumps(res))
