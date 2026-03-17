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

    def __init__(self, path_diskcache):
        self.base_diskcace = path_diskcache
    
    def get(self, request, ttl, path_archive=None, flag_diskcache=True):
        res_out = None

        if not flag_diskcache:
            return res_out

        today = datetime.today()
        path = Path(f"{self.base_diskcace}{os.path.sep}{today.year}{os.path.sep}{today.month}{os.path.sep}{today.day}{os.path.sep}")

        m = hashlib.md5(request.url.encode('utf-8'))

        if m is not None:

            hex_file = f"{m.hexdigest()}.*"
            files = list(path.glob(hex_file))

            if files:


                file_name = files[0].name
                final_path = f"{path}{os.path.sep}{file_name}"                

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

                if ".json" in file_name or ".csv" in file_name:
                    with open(f"{path}{os.path.sep}{file_name}", 'r') as file:
                        res_out = json.load(file)
                else:
                    # .png case  or .csv case
                    with open(f"{path}{os.path.sep}{file_name}", 'rb') as file:
                        res_out = file.read()
        return res_out

    # type --> plot - json - csv
    def set(self, request, res, type_file='plot'): 
        res_out = None
        m = hashlib.md5(request.url.encode('utf-8'))

        if m is not None:

            if type_file == 'plot':
                extension = '.png'
            elif type_file == 'csv':
                extension = '.csv'
            else:
                extension = '.json'
            
            today = datetime.today()

            if not os.path.exists(f"{self.base_diskcace}{os.path.sep}{today.year}{os.path.sep}{today.month}{os.path.sep}{today.day}{os.path.sep}"):
                os.makedirs(f"{self.base_diskcace}{os.path.sep}{today.year}{os.path.sep}{today.month}{os.path.sep}{today.day}{os.path.sep}")
            
            with open(f"{self.base_diskcace}{os.path.sep}{today.year}{os.path.sep}{today.month}{os.path.sep}{today.day}{os.path.sep}{m.hexdigest()}{extension}", 'w') as file:
                file.write(json.dumps(res))