"""Path builders for forecast archive and storage locations."""

#################################################
#   
#   Università Degli Studi di Napoli Parthenope 
#
#
# Authors: 
#    Prof. Raffaele Montella
#    Dario Caramiello   
#
#################################################

from core.Places import Places

import os
from datetime import datetime, timezone

class MakeArchivePaths: 
    """Service or helper that encapsulates make archive paths behavior."""

    
    def makePath(
        prod, place=None, date=None, history=None, lat=None, lon=None, *, config
    ):
        """Build an archive path using the caller's explicit application config."""

        if date is None:
            date = datetime.now(timezone.utc)
            year = date.year
            month = date.month
            day = date.day
            hour = 0
            minute = 0
        else :
            year = (int(date[:4]))
            month = int(date[4:6])
            day = int(date[6:8])
            hour = int(date[9:11])
            if len(date) == 13:
                minute = int(date[11:13])

        date = datetime(year, month, day, hour, minute)

        if lat is not None and lon is not None:
            domain = Places(config).get_domain_by_product_and_ll(prod, lat, lon)
        else:
            domain_indeces = Places(config).get_domain_and_indeces_by_product_and_place(prod, place, date.strftime("%Y%m%dZ%H00"))
        

        dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + format(date.minute, '02')
        dateTimePath = format(date.year, '04') + "/" + format(date.month, '02') + "/" + format(date.day, '02')

        if lat is None and lon is  None:
            (domain, Jmin, Jmax, Imin, Imax) = domain_indeces

        if history == True:
            path = config['BASE_PATH_HISTORY'] + os.path.sep + prod + os.path.sep + domain + os.path.sep + config['HISTORY'] + os.path.sep + dateTimePath + os.path.sep + prod + "_" + domain + "_" + dateTime + ".nc"
        elif history is None:
            path = config['BASE_PATH'] + os.path.sep + prod + os.path.sep + domain + os.path.sep + config['ARCHIVE'] + os.path.sep + dateTimePath + os.path.sep + prod + "_" + domain + "_" + dateTime + ".nc"
        
        return path

 
