"""Meteorological formatting and conversion helpers used by product endpoints."""

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

import json
import math
import sys
import calendar
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import netCDF4
import numpy as np
import requests
import simplejson
import os.path
import xmltodict
import urllib.parse as urllib
import urllib.request as urllib_request
from flask import make_response
import time
import app

from PIL import ImageFont
from PIL import ImageDraw 
from PIL import Image
from influxdb_client import InfluxDBClient


from core.Places import Places
from core.Plotter import Plotter
from datetime import datetime, timedelta
from core.Logger import logger
from core.Models import Instrument
from core.MakeArchivePaths import MakeArchivePaths
from core.SkewTServices import SkewTServices


#### Logging ####
# logger = logging.getLogger('main_logger')
################

WEATHER_TEXTS = [
    {"it-IT": "Sereno", "en-US": "Clear"},
    {"it-IT": "Poco nuvoloso", "en-US": "Partly Cloudy"},
    {"it-IT": "Nuvoloso", "en-US": "Cloudy"},
    {"it-IT": "Molto nuvoloso", "en-US": "Very Cloudy"},
    {"it-IT": "Coperto", "en-US": "Covered"},
    {"it-IT": "Rovesci", "en-US": "Showers"},
    {"it-IT": "Pioggia", "en-US": "Rain"},
    {"it-IT": "Forti piogge", "en-US": "Heavy Rains"}
]


_TIMESERIES_PROCESS_SERVICE = None


def _build_timeseries_process_service(config):
    """Create a lightweight service instance suitable for process workers."""
    service = MeteoServices.__new__(MeteoServices)
    service.config = config
    service.maps = None
    service.legal = None
    service._numpy_method_cache = {}

    with open(config["MAPS"]) as maps_file:
        service.maps = simplejson.load(maps_file)

    service.places = Places(config)
    service.plotter = None
    return service


def _init_timeseries_process_pool(config):
    """Initialize one shared MeteoServices-like helper inside each worker process."""
    global _TIMESERIES_PROCESS_SERVICE
    _TIMESERIES_PROCESS_SERVICE = _build_timeseries_process_service(config)


def _process_pool_model_output(item):
    """Compute one time-series model output inside a worker process."""
    if _TIMESERIES_PROCESS_SERVICE is None:
        raise RuntimeError("Timeseries process pool was not initialized")
    return _TIMESERIES_PROCESS_SERVICE.modelOutput(item, use_disk_cached=True)

def statusByConc(args):
    """Map a concentration value to its configured status label."""
    con = args[0]
    sts = 0
    if 18 < con <= 230:
        sts = 1
    elif 230 < con <= 700:
        sts = 2
    elif 700 < con <= 4600:
        sts = 3
    elif 4600 < con <= 46000:
        sts = 4
    elif con > 46000:
        sts = 5

    return sts

def northDirection(args):
    """Convert a directional angle into a named compass sector."""
    u = args[0]
    v = args[1]
    direction = math.atan2(v, u) / math.pi * 180
    if direction < 0:
        direction = direction + 360

    return direction

def modulus(args):
    """Return the vector modulus for the provided components."""
    u = args[0]
    v = args[1]
    return (u * u + v * v) ** .5

def windS(args):
    """Format wind speed and direction into a compact human-readable string."""
    if type(args) is list:
        direction = args[0]
    else:
        direction = args

    if 11.25 <= direction < 33.75:
        return "NNE"
    if 33.75 <= direction < 56.25:
        return "NE"
    if 56.25 <= direction < 78.75:
        return "ENE"
    if 78.75 <= direction < 101.25:
        return "E"
    if 101.25 <= direction < 123.75:
        return "ESE"
    if 123.75 <= direction < 146.25:
        return "SE"
    if 146.25 <= direction < 168.75:
        return "SSE"
    if 168.75 <= direction < 191.25:
        return "S"
    if 191.25 <= direction < 213.75:
        return "SSW"
    if 213.75 <= direction < 236.25:
        return "SW"
    if 236.25 <= direction < 258.75:
        return "WSW"
    if 258.75 <= direction < 281.25:
        return "W"
    if 281.25 <= direction < 303.75:
        return "WNW"
    if 303.75 <= direction < 326.25:
        return "NW"
    if 326.25 <= direction < 348.75:
        return "NNW"
    if 348.75 <= direction < 359.9999:
        return "N"

def currS(args):
    """Format current speed and direction into a compact human-readable string."""
    direction = northDirection(args)
    if 11.25 <= direction < 33.75:
        return "SSW"
    if 33.75 <= direction < 56.25:
        return "SW"
    if 56.25 <= direction < 78.75:
        return "WSW"
    if 78.75 <= direction < 101.25:
        return "W"
    if 101.25 <= direction < 123.75:
        return "WNW"
    if 123.75 <= direction < 146.25:
        return "NW"
    if 146.25 <= direction < 168.75:
        return "NNW"
    if 168.75 <= direction < 191.25:
        return "N"
    if 191.25 <= direction < 213.75:
        return "NNE"
    if 213.75 <= direction < 236.25:
        return "NE"
    if 236.25 <= direction < 258.75:
        return "ENE"
    if 258.75 <= direction < 281.25:
        return "E"
    if 281.25 <= direction < 303.75:
        return "ESE"
    if 303.75 <= direction < 326.25:
        return "SE"
    if 326.25 <= direction < 348.75:
        return "SSE"
    if 348.75 <= direction < 359.9999:
        return "S"

def weatherText(args):
    """Return a human-readable weather description for a condition code."""
    crh = args[0]
    clf = args[1]

    if crh < 0.1:
        if clf < .0625:
            return WEATHER_TEXTS[0]
        if clf < .1875:
            return WEATHER_TEXTS[1]
        if clf < .625:
            return WEATHER_TEXTS[2]
        if clf < .875:
            return WEATHER_TEXTS[3]
        return WEATHER_TEXTS[4]

    if crh < 2:
        return WEATHER_TEXTS[5]

    if crh < 10:
        return WEATHER_TEXTS[6]
    return WEATHER_TEXTS[7]


def weatherIcon(args):
    """Return the icon identifier associated with a weather condition code."""
    date13 = args[0]
    crh = args[1]
    clf = args[2]


    if len(date13) == 11:
        date13 = date13 + "00"
    hhmm = date13[-4:]

    if (hhmm >= "0500") and (hhmm <= "1800"):
        suf = '.png'
    else:
        suf = '_night.png'

    if crh < 0.1:
        if clf < .0625:
            return ('sunny' + suf)
        if clf < .1875:
            return ('cloudy1' + suf)
        if clf < .625:
            return ('cloudy2' + suf)
        if clf < .875:
            return ('cloudy4' + suf)
        return ('cloudy5' + suf)

    if crh < 2:
        return ('shower1' + suf)

    if crh < 10:
        return ('shower2' + suf)
    return ('shower3' + suf)


def knt2kmh(args):
    """Convert a speed from knots to kilometers per hour."""
    kt = args[0]
    return kt * 1.852


def windChill(args):
    """Estimate the wind chill temperature from air temperature and wind speed."""
    t2c = args[0]
    ws10 = args[1]
    wind = pow(knt2kmh([float(ws10)]), 0.16)
    return round((13.12 + 0.6215 * t2c - 11.37 * wind + 0.3965 * t2c * wind))


#### CSVFY ####
def csvfy(data):
    """Convert a Python value into a CSV-safe textual representation."""
    logger.debug("csvfy input type: %s", type(data))
    result = ""
    timeseries = data['timeseries']
    fields = data['fields']
    keys = ['dateTime']
    for field in fields:
        if not 'dateTime' in field:
            keys.append(field)
    line = ""
    for key in keys:
        line = line + key + ";"
    result = line[:-1] + "\n"

    for item in timeseries:
        line = ""

        for key in keys:
            try:
                line = line + str(item[str(key)]) + ";"
            except:
                line = line + ";"

        result = result + line[:-1] + "\n"

    output = make_response(result)
    output.headers["Content-type"] = "text/csv"
    return output


def knt2Beaufort(args):
    """Convert a speed in knots to the Beaufort scale."""
    wind_speed = args[0]
    return int(0.725 * ( wind_speed ** 2 ) ** (1/3))

def beaufortText(wind_speed):
    """Return the descriptive label for a Beaufort scale value."""

    beaufort = knt2Beaufort(wind_speed)

    text_list_en = ["Calm", "Light Air", "Light Breeze", "Gentle", "Moderate Breeze", "FreshBreeze", "Strong Breeze", "Near Gale", "Gale", "Strong Gale", "Storm", "Violent Storm", "Hurricane"]
    text_list_in = ["Calma", "Bava Di Vento", "Brezza Leggera", "Vento Moderato", "VentoTeso", "Vento Fresco", "Vento Forte", "Burrasca", "Tempesta", "Tempesta Violenta", "Uragano" ]

    
    out = {
        "it-IT": text_list_en[beaufort],
        "en-US": text_list_in[beaufort]
    }

    return out

def iconText(current):
    """Return the text label associated with an icon identifier."""
    crh = float(current['crh'])
    clf = float(current['clf'])
    date13=current['date']
    if len(date13)==11:
        date13=date13+"00"
    hhmm = date13[-4:]

    #print "----------------> date:"+str(date13)+"-->"+str(hhmm)

    if (hhmm >= "0500") and  (hhmm <= "1800"):
        suf = '.png'
    else:
        suf = '_night.png'

    #print "suf: " + suf

    if (crh < 0.1):
        if (clf < .0625):
            return ('sunny' + suf), WEATHER_TEXTS[0]
        if (clf < .1875):
            return ('cloudy1' + suf), WEATHER_TEXTS[1]
        if (clf < .625):
            return ('cloudy2' + suf), WEATHER_TEXTS[2]
        if (clf < .875):
            return ('cloudy4' + suf), WEATHER_TEXTS[3]
        return ('cloudy5' + suf), WEATHER_TEXTS[4]

    if (crh < 2):
        return ('shower1' + suf), WEATHER_TEXTS[5]
    if (crh < 10):
        return ('shower2' + suf), WEATHER_TEXTS[6]
    return ('shower3' + suf), WEATHER_TEXTS[7]

def significantHeightIcon(args):
    """Choose an icon for the provided significant wave height."""
    hs = round(args[0], 2)
    hs_icons = ["glassy.png", "rippled.png", "smooth.png", "slight.png", "moderate.png", "rough.png", "veryrough.png", "high.png", "veryhigh.png", "phenomenal.png"]
    index = -1
    
    if hs == 0.0:
        index = 0   
    elif hs <= 0.10:
        index = 1   
    elif hs <= 0.50:
        index = 2  
    elif hs <= 1.25:
        index = 3   
    elif hs <= 2.50:
        index = 4  
    elif hs <= 4.00:
        index = 5   
    elif hs <= 6.00:
        index = 6  
    elif hs <= 9.00:
        index = 7   
    elif hs <= 14.00:
        index = 8   
    else:
        index = 9   
        
    return hs_icons[index]

def surfaceCurrentIcon(args):
    """Choose an icon for the provided surface current magnitude."""
    scm = args[0]
    scm_icons = [ "current_very_weak.png", "current_weak.png", "current_low.png", "current_low_medium.png", "current_medium.png", "current_medium_high.png", "current_high.png", "current_very_high.png", "current_extremely_high.png", "current_maximum.png"]
    index = -1
    

    if scm < 0.4:
        index = 0
    elif scm < 0.8:
        index = 2
    elif scm < 1.2:
        index = 2
    elif scm < 1.6:
        index = 3
    elif scm < 2.0:
        index = 4
    elif scm < 2.4:
        index = 5
    elif scm < 2.6:
        index = 6
    elif scm < 2.8:
        index = 7
    elif scm < 3.0:
        index = 8
    else:
        ubdex = 9
    
    return scm_icons[index]

def concentrationParticles(args):
    """Classify particle concentration into the configured categories."""
    if int(args[0]) > 10:
        sts = statusByConc([int(args[0])])
    else:
        sts = int(args[0])
    sts_icons = ["absent.png", "verylow.png", "low.png", "medium.png", "high.png", "veryhigh.png", "critical.png"]

    return sts_icons[sts]

def musselContaminationIcon(args):
    """Choose an icon representing mussel contamination risk."""
    mci = args[0]
    mci_icons = ["absent.png", "verylow.png", "low.png", "medium.png", "high.png", "veryhigh.png", "critical.png"]

    return mci_icons[int(mci) + 1]

class MeteoServices:
    """Service or helper that encapsulates meteo services behavior."""
    places = None
    plotter = None
    default_domain = 'd01'
    default_place = 'reg15'
    default_output = 'gen'
    # default_prod = 'wrf3'
    default_prod = 'wrf5'
    default_xdim = 1024
    default_ydim = 768
    default_run = 'not'
    default_lang = "en-US"

    config = {}
    path = ""
    __statusCode = {'200': {'code': '200', 'msg': 'OK'}, '205': {'code': '205', 'msg': 'No Content'},
                    '231': {'code': '231', 'msg': 'Info Not Available'}, '400': {'code': '400', 'msg': 'Bad Request'},
                    '401': {'code': '401', 'msg': 'Unauthorized'}, '404': {'code': '404', 'msg': 'Not Found'}}

    def __init__(self, config):
        """Initialize meteo services state."""
        self.config = config
        self.maps = None
        self.legal = None
        self._numpy_method_cache = {}

        with open(self.config["MAPS"]) as f:
            self.maps = simplejson.load(f)
        with open(self.config["LEGAL"]) as f:
            self.legal = simplejson.load(f)

        self.places = Places(self.config)
        self.plotter = Plotter(self.config)

    def _model_output_cache_path(self, prod, place, timeref):
        """Return the cache-file path used by modelOutput for one hourly slice."""
        date = self._parse_datetime_ref(timeref, round_to_hour=(timeref is None))
        dateTime = self._format_datetime_ref(date)
        relative_path = os.path.sep.join(
            [place, prod, date.strftime("%Y"), date.strftime("%m"), date.strftime("%d")]
        )
        image_name = "jsn__" + place + "_" + prod + "_" + dateTime + ".json"
        return self.config['CACHE_JSON'] + os.path.sep + relative_path + os.path.sep + image_name

    def _is_model_output_cache_valid(self, item):
        """Return whether one time-series hourly slice already has a reusable disk-cache entry."""
        cache_path = self._model_output_cache_path(item["prod"], item["place"], item["date"])
        if os.path.isfile(cache_path) is False:
            return False

        path_archive = MakeArchivePaths.makePath(item["prod"], item["place"])

        if os.path.isfile(path_archive) and os.path.getmtime(path_archive) > os.path.getmtime(cache_path):
            return False

        return (time.time() - os.path.getmtime(cache_path)) <= self.config['TTL_DISKCACHE']

    def _timeseries_parallel_mode(self):
        """Return the configured execution mode for multi-step time-series endpoints."""
        return str(self.config.get("TIMESERIES_PARALLEL_MODE", "processes")).lower()

    def _timeseries_process_workers(self, item_count):
        """Return the number of process workers to use for uncached multi-step items."""
        if item_count < 2:
            return 1
        configured = self.config.get("NUM_PROCESSES")
        if configured is None:
            configured = min(os.cpu_count() or 1, self.config.get("NUM_THREADS", 1))
        return max(1, min(int(configured), item_count))

    def _timeseries_thread_workers(self, item_count):
        """Return the number of thread workers to use for local fallback execution."""
        if item_count < 1:
            return 1
        return max(1, min(self.config['NUM_THREADS'], item_count))

    def _load_timeseries_cached_outputs(self, items):
        """Load already-cached hourly model outputs in-process."""
        if not items:
            return []
        max_workers = self._timeseries_thread_workers(len(items))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            return list(executor.map(lambda item: self.modelOutput(item, use_disk_cached=True), items))

    def _compute_timeseries_uncached_outputs(self, items):
        """Compute uncached hourly model outputs using multiprocessing when configured."""
        if not items:
            return []

        parallel_mode = self._timeseries_parallel_mode()
        max_workers = self._timeseries_process_workers(len(items))

        if parallel_mode == "processes" and max_workers > 1:
            config_snapshot = dict(self.config)
            with ProcessPoolExecutor(
                max_workers=max_workers,
                initializer=_init_timeseries_process_pool,
                initargs=(config_snapshot,),
            ) as executor:
                return list(executor.map(_process_pool_model_output, items))

        thread_workers = self._timeseries_thread_workers(len(items))
        with ThreadPoolExecutor(max_workers=thread_workers) as executor:
            return list(executor.map(lambda item: self.modelOutput(item, use_disk_cached=True), items))

    def getMaps(self):
        """Implement get maps for meteo services."""
        return self.maps

    def printMaps(self):
        """Implement print maps for meteo services."""
        logger.info("maps: %s", self.maps)

    def getThemes(self, prod):
        """Implement get themes for meteo services."""
        return self.maps['products'][prod]

    def getProds(self, prod=None):
        """Implement get prods for meteo services."""
        result = {}
        if prod is None:
            result = self.maps["products"]
        else:
            try:
                result = self.maps["products"][prod]
            except ValueError as e:
                logger.error("[*] Value error : %s", e)
        return result

    def printProducts(self):
        """Implement print products for meteo services."""
        for item in self.maps["products"]:
            logger.info("product: %s", item)

    def __getFullLink(self, url, fields):
        """Internal helper for get full link."""
        fields_string = ''
        for key, value in fields.items():
            fields_string = fields_string + key + '=' + value + '&'
        fields_string = fields_string.rstrip('&')
        full_link = url + '?' + fields_string
        return full_link

    def __executeRequest(self, url):
        """Internal helper for execute request."""
        data = urllib_request.urlopen(url)
        data = data.read()

        if "Not Found" in data:
            return False

        if not data:
            return True
        else:
            return data

    def calc_boundaries(self, west_east_dim, south_north_dim, XLONG, XLAT):
        """Implement calc boundaries for meteo services."""
        xlon_a = [XLONG[0, 0], XLONG[south_north_dim - 1, 0], XLONG[0, west_east_dim - 1],
                  XLONG[south_north_dim - 1, west_east_dim - 1]]

        # check for dateline
        ilon = 0
        if abs(xlon_a[0] - xlon_a[2]) > 180.: ilon = 1
        if abs(xlon_a[1] - xlon_a[3]) > 180.: ilon = 1

        abslatmin = np.array(XLAT).min()
        abslatmax = np.array(XLAT).max()
        abslonmin = 99999.
        abslonmax = -99999.
        for i in range(0, 4):
            if xlon_a[i] < 0.0 and ilon == 1:
                abslonmin = min(abslonmin, 360. + xlon_a[i])
                abslonmax = max(abslonmax, 360. + xlon_a[i])
            else:
                abslonmin = min(abslonmin, xlon_a[i])
                abslonmax = max(abslonmax, xlon_a[i])

        lat_min = float(abslatmin)
        lat_max = float(abslatmax)
        lon_min = float(abslonmin)
        lon_max = float(abslonmax)

        dxll = (lon_max - lon_min) / west_east_dim
        dyll = (lat_max - lat_min) / south_north_dim

        return lon_min, lat_min, lon_max, lat_max, round(dxll, 6), round(dyll, 6)

    def printSpecificProducts(self, prod):
        """Implement print specific products for meteo services."""
        for item in self["products"][prod]:
            logger.info("specific product entry: %s", item)

    def getFields(self, prod):
        """Implement get fields for meteo services."""
        result = {}
        if prod in self.maps["products"] and 'fields' in self.maps["products"][prod]:
            result = self.maps["products"][prod]['fields']
        return result

    def getOutputs(self, prod):
        """Implement get outputs for meteo services."""
        result = {}
        if prod in self.maps["products"] and 'outputs' in self.maps["products"][prod]:
            result = self.maps["products"][prod]['outputs']
        return result

    def _parse_datetime_ref(self, timeref, round_to_hour=False, default_midnight=False):
        """Return a datetime parsed from the API time reference format."""
        if timeref is None:
            now = datetime.utcnow()
            if default_midnight:
                return datetime(now.year, now.month, now.day, 0, 0)
            if round_to_hour:
                return datetime(now.year, now.month, now.day, int(round(now.hour + now.minute / 60.0)), 0)
            return datetime(now.year, now.month, now.day, now.hour, now.minute)

        minute = int(timeref[11:13]) if len(timeref) == 13 else 0
        return datetime(
            int(timeref[:4]),
            int(timeref[4:6]),
            int(timeref[6:8]),
            int(timeref[9:11]),
            minute
        )

    def _format_datetime_ref(self, date_value):
        """Return the API datetime format for a datetime instance."""
        return date_value.strftime("%Y%m%dZ%H%M")

    def _get_numpy_method(self, method_name):
        """Return and cache the NumPy reduction function used by field extraction."""
        method = self._numpy_method_cache.get(method_name)
        if method is None:
            method = getattr(np, method_name)
            self._numpy_method_cache[method_name] = method
        return method

    def getProductAvail(self, params):
        """Implement get product avail for meteo services."""
        items = []
        prod = None
        place = None
        offset_pre = 1
        offset_post = 0
        timeref = None

        use_step_cache = True

        if params:
            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'place' in params and params['place'] is not None:
                place = params['place']

            if 'date' in params and params['date'] is not None:
                timeref = params['date']

            if 'offset_pre' in params:
                offset_pre = float(params['offset_pre'])

            if 'offset_pre' in params:
                offset_post = float(params['offset_post'])

        # Get the domain and the indeces of the place
        domain_indeces = self.places.get_domain_and_indeces_by_product_and_place(prod, place)

        # Check if domain and indeces are correct
        if domain_indeces is not None:

            # Retrieve domain and indeces
            (domain, Jmin, Jmax, Imin, Imax) = domain_indeces

            def daterange(start_date, end_date):
                """Yield ten-minute timestamps across the requested interval."""
                N = abs((end_date - start_date).days * 1440)
                for n in range(0, N, 10):
                    yield start_date + timedelta(n / 1440.0)

            def check_date(date):
                """Build one availability item when the expected NetCDF file exists."""
                item = None
                dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(
                    date.hour, '02') + format(date.minute, '02')
                dateTimePath = format(date.year, '04') + "/" + format(date.month, '02') + "/" + format(date.day, '02')

                # :/storage/ccmmma/prometeo/data/opendap//rdr1/d04/archive/2023/04/19/rdr1_d04_20230419Z0650.nc
                url = self.config['BASE_PATH'] + "/" + prod + "/" + domain + "/" + self.config[
                    'HISTORY'] + "/" + dateTimePath + "/" + prod + "_" + domain + "_" + dateTime + ".nc"
                # print("URL:"+str(url))

                if os.path.isfile(url):
                    item = {"prod": prod, "domain": domain, "place": place, "date": dateTime}
                return item

            if timeref is None:
                utc_now = datetime.utcnow()
                utc_now = datetime(utc_now.year, utc_now.month, utc_now.day, utc_now.hour, 0, 0)
                time_delta_pre = timedelta(minutes=offset_pre * 1440)
                time_delta_post = timedelta(minutes=offset_post * 1440)
                start_date = utc_now - time_delta_pre
                end_date = utc_now + time_delta_post

                for date in daterange(start_date, end_date):
                    item = check_date(date)
                    if item is not None:
                        items.append(item)
            else:
                year = int(timeref[:4])
                month = int(timeref[4:6])
                day = int(timeref[6:8])
                hour = int(timeref[9:11])
                if len(timeref) == 13:
                    minute = int(timeref[11:13])
                else:
                    minute = 0

                date = datetime(year, month, day, hour, minute)
                item = check_date(date)
                if item is not None:
                    items.append(item)
        return items

    def getLegalDisclaimer(self, options=None):
        """Implement get legal disclaimer for meteo services."""
        lang = "en-US"
        if options is not None:
            if "lang" in options and options['lang'] is not None:
                lang = options['lang']

        result = {
            "i18n": {
                lang: {
                    "disclaimer": self.legal["i18n"][lang]['disclaimer']
                }
            }
        }
        return result

    def getLegalPrivacy(self, options=None):
        """Implement get legal privacy for meteo services."""
        lang = "en-US"
        if options is not None:
            if "lang" in options and options['lang'] is not None:
                lang = options['lang']

        result = {
            "i18n": {
                lang: {
                    "privacy": self.legal["i18n"][lang]['privacy']
                }
            }
        }
        return result
    
    def convert_f_to_c(self, temp_in_fahrenheit):
        """Implement convert f to c for meteo services."""
        convert = (temp_in_fahrenheit - 32) * 5 / 9
        return float("{:.2f}".format(convert))
    
    def getInstruments(self):
        """Implement get instruments for meteo services."""
        signalk_url = "https://signalk.meteo.uniparthenope.it"
        signalk_meteo = f"{signalk_url}/signalk/v1/api/meteo/"

        headers = {
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(signalk_meteo, headers=headers)
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            logger.error("Errore nella richiesta: %s", e)
            return None

    '''
    def getInstruments(self):
        client = InfluxDBClient(url="http://193.205.230.7:8086", token="__jNBfyWPRNHEau33ebp2PzZSqoaHN5WkCqqZcELncYRpuF13LS-kV-cYmoq7zI3so3rtiFd2Kou6-md06PBdw==", org="Parthenope")
        query_api = client.query_api()
        
        query = f"""from(bucket: "ws") |> range(start: -3h) |> last()"""
        tables = query_api.query(query, org="Parthenope")
        instruments = Instrument.query.all()
        instruments_data = []
        
        for instrument in instruments:
            relevant_variables = instrument.variables.split(", ") if instrument.variables else []

            instrument_data = {
                'id': instrument.id,
                'name': instrument.name,
                'airlinkID': instrument.airlinkID,
                'latitude': instrument.latitude,
                'longitude': instrument.longitude,
                'type': instrument.instrument_type,
                'organization': instrument.organization,
                'image': f'static/uploads/{instrument.image}' if instrument.image else None
            }

            influx_data = {}
            for table in tables:
                for record in table.records:
                    if record.values.get("topic") == instrument.id:
                        if record.get_field() in relevant_variables:
                            influx_data[record.get_field()] = record.get_value()

            instrument_data['variables'] = influx_data
            if 'TempOut' in instrument_data['variables']:
                instrument_data['variables']['TempOut'] = self.convert_f_to_c(instrument_data['variables']['TempOut'])

            instruments_data.append(instrument_data)

        geojson_data = {
            "type": "FeatureCollection",
            "features": []
        }

        for station in instruments_data:
            feature = {
                "type": "Feature",
                "properties": {
                    "airlinkID": station["airlinkID"],
                    "id": station["id"],
                    "image": station["image"],
                    "name": station["name"],
                    "organization": station["organization"],
                    "type": station["type"],
                    "variables": station["variables"]
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [station["longitude"], station["latitude"], 0]
                }
            }
            
            geojson_data["features"].append(feature)

        return geojson_data
    '''


    def getProductAvailCalendar(self, params):
        """Implement get product avail calendar for meteo services."""
        calendar_items = []
        baseUrl = ""
        prod = "wrf5"
        start = None
        end = None
        timeZone = "UTC"

        start_date = None
        end_date = None

        if params:
            if 'baseUrl' in params and params['baseUrl'] is not None:
                baseUrl = params['baseUrl']

            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'place' in params and params['place'] is not None:
                place = params['place']

            if 'start' in params and params['start'] is not None:
                start = params['start']

            if 'end' in params and params['end'] is not None:
                end = params['end']

            if 'timeZone' in params and params['timeZone'] is not None:
                timeZone = params['timeZone']

        if start is None:
            utc_now = datetime.utcnow()
            start_date = datetime(utc_now.year, utc_now.month, 1, 0, 0, 0)
        else:
            # 2020-04-15T10:30:00+00:00
            year = int(start[:4])
            month = int(start[5:7])
            day = int(start[8:10])
            hour = int(start[11:13])
            minute = int(start[14:16])

            # print start[:4], start[5:7], start[8:10], start[11:13], start[14:16]

            start_date = datetime(year, month, day, hour, minute)

        if end is None:
            utc_now = datetime.utcnow()
            lastDay = calendar.monthrange(utc_now.year, utc_now.month)[1]
            end_date = datetime(utc_now.year, utc_now.month, lastDay, 23, 59, 59)
        else:
            # 2020-04-15T10:30:00+00:00
            year = int(end[:4])
            month = int(end[5:7])
            day = int(end[8:10])
            hour = int(end[11:13])
            minute = int(end[14:16])

            end_date = datetime(year, month, day, hour, minute)

        # Get the domain and the indeces of the place
        domain_indeces = self.places.get_domain_and_indeces_by_product_and_place(prod, place)

        # Check if domain and indeces are correct
        if domain_indeces is not None:

            # Retrieve domain and indeces
            (domain, Jmin, Jmax, Imin, Imax) = domain_indeces

            def daterange(start_date, end_date):
                """Yield ten-minute timestamps across the requested interval."""
                N = abs((end_date - start_date).days * 1440)
                for n in range(0, N, 10):
                    yield start_date + timedelta(n / 1440.0)

            def check_date(date):
                """Build one calendar item and note whether history or archive data exists."""
                item = None
                dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(
                    date.hour, '02') + format(date.minute, '02')
                dateTimePath = format(date.year, '04') + "/" + format(date.month, '02') + "/" + format(date.day, '02')

                sources = []
                url = self.config[
                          'BASE_PATH'] + "/" + prod + "/" + domain + "/history/" + dateTimePath + "/" + prod + "_" + domain + "_" + dateTime + ".nc"
                if os.path.isfile(url):
                    sources.append("history")

                url = self.config['BASE_PATH'] + "/" + prod + "/" + domain + "/" + self.config[
                    'ARCHIVE'] + "/" + dateTimePath + "/" + prod + "_" + domain + "_" + dateTime + ".nc"
                if os.path.isfile(url):
                    sources.append("archive")

                if len(sources) > 0:
                    item = {"prod": prod, "domain": domain, "place": place, "date": dateTime, "sources": sources}
                return item

            for date in daterange(start_date, end_date):
                item = check_date(date)
                if item is not None:

                    calendar_dateTime_start = format(date.year, '04') + "-" + format(date.month, '02') + "-" + format(
                        date.day, '02') + "T" + format(date.hour, '02') + ":" + format(date.minute, '02') + ":00+00:00"

                    minute_end = 0
                    if "rdr1" in prod or "rdr2" in prod:
                        minute_end = date.minute + 9
                    else:
                        minute_end = date.minute + 59

                    calendar_dateTime_end = format(date.year, '04') + "-" + format(date.month, '02') + "-" + format(
                        date.day, '02') + "T" + format(date.hour, '02') + ":" + format(minute_end, '02') + ":00+00:00"

                    title = item["domain"]
                    if "history" in item["sources"]: title = title + "/H"
                    if "archive" in item["sources"]: title = title + "/A"

                    calendar_item = {
                        "groupId": item["prod"],
                        "title": title,
                        "start": calendar_dateTime_start,
                        "end": calendar_dateTime_end,
                        "url": baseUrl + "&prod=" + item["prod"] + "&place=" + item["place"] + "&date=" + item["date"]
                    }
                    calendar_items.append(calendar_item)
        return calendar_items


    
    def modelOutput(self, params=None, use_disk_cached=True,):
        """Implement model output for meteo services."""
        import time as t

        retval = {}

        prod = self.default_prod
        place = self.default_place

        timeref = None


        if params:
            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'place' in params and params['place'] is not None:
                place = params['place']

            if 'date' in params and params['date'] is not None:
                timeref = params['date']

        date = self._parse_datetime_ref(timeref, round_to_hour=(timeref is None))
        dateTime = self._format_datetime_ref(date)
        relativePath = place + os.path.sep + prod + os.path.sep + date.strftime("%Y") + os.path.sep + date.strftime("%m") + os.path.sep + date.strftime("%d")
       
        imageName = "jsn__" + place + "_" + prod + "_" + dateTime + ".json" 
        imagePath = self.config['CACHE_JSON'] + os.path.sep + relativePath + os.path.sep + imageName

        cache_dir = self.config['CACHE_JSON'] + os.path.sep + relativePath
        if use_disk_cached:
            if os.path.exists(cache_dir) is False:
                os.makedirs(cache_dir)
            elif os.path.isfile(imagePath):

                path_archive = MakeArchivePaths.makePath(prod, place)

                if (os.path.isfile(path_archive) is True) and (os.path.getmtime(path_archive) > os.path.getmtime(imagePath)):
                    logger.info(f"DISK 2 : File '{imagePath}' not consistent respect to ARCHIVE file !")
                    os.remove(imagePath)
                    logger.info(f"DISK 2 : File '{imagePath}' deleted !")
                else:
                    # logger.info(f"DISK 2 : delta time expired {(t.time() - os.path.getmtime(imagePath))} !")
                    if t.time() - os.path.getmtime(imagePath) > self.config['TTL_DISKCACHE']:
                        logger.info(f"DISK 2 : File ( {imagePath} ) expired !")
                        os.remove(imagePath)
                        logger.info(f"DISK 2 : File ( {imagePath} ) deleted !")
                    else:
                        with open(imagePath, "r") as json_file:
                            retval = json.load(json_file)
                        return retval

        
        # if use_disk_cached is False or os.path.isfile(imagePath) is False:
            
        # Get the domain and the indeces of the place
        domain_indeces = self.places.get_domain_and_indeces_by_product_and_place(prod, place, date.strftime("%Y%m%dZ%H00"))


        # Check if domain and indeces are correct
        if domain_indeces is not None:

            # Retrieve domain and indeces
            (domain, Jmin, Jmax, Imin, Imax) = domain_indeces

            # Set the dateTime
            dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + format(date.minute, '02')

            dateTimePath = format(date.year, '04') + "/" + format(date.month, '02') + "/" + format(date.day, '02')

            #url = self.config['BASE_PATH'] + "/" + prod + "/" + domain + "/" + self.config['HISTORY'] + "/" + dateTimePath + "/" + prod + "_" + domain + "_" + dateTime + ".nc"
            url = self.config['BASE_PATH'] + "/" + prod + "/" + domain + "/" + self.config['ARCHIVE'] + "/" + dateTimePath + "/" + prod + "_" + domain + "_" + dateTime + ".nc"

            retval = {}

            # Check if the file exists
            dataset = None

            try:
                # Open the data file
                dataset = netCDF4.Dataset(url)
            except Exception as e:
                logger.error("[*] netCDF4 error : %s", e)

            # Check if the product is available and if the filds are defined
            if prod in self.maps["products"] and "fields" in self.maps["products"][prod]:

                # For each field in fields
                for field, item in self.maps["products"][prod]["fields"].items():

                    # Set default method
                    # method = "nanmean"
                    method = "mean"

                    # Check if method is defined in item
                    if "method" in item:

                        # Set the method
                        method = item["method"]


                    # Set the method
                    method = self._get_numpy_method(method)

                    # Set time to None
                    time = None

                    # Check if time is defined in item
                    if "time" in item:

                        # Set time
                        time = item["time"]

                    # Set level to None
                    level = None

                    # Check if level is in item
                    if "level" in item:

                        # Set level
                        level = item["level"]

                    # Check func to none
                    func = None

                    # Check if func is defined in item
                    if "func" in item:

                        # Get the module and the string module.function
                        parts = item["func"].split(".")

                        # Check if no module is set
                        if len(parts) == 1:

                            # Use the current module as default
                            parts = [ sys.modules[__name__], item["func"]]

                        # Check if the module name is set
                        elif len(parts) == 2:

                            # Use the specified module
                            parts = [ sys.modules[parts[0]], item["func"]]

                        # Try to set the function
                        try:

                            # Set the function pointer
                            func = getattr(parts[0], parts[1])

                        # If inconsistent module/function rise an exception
                        except Exception as e:
                            pass

                    a = 1
                    if "a" in item:
                        a = item["a"]

                    b = 0
                    if "b" in item:
                        b = item["b"]

                    round_digits = None
                    if "round" in item:
                        round_digits = item["round"]


                    zero_if_negative = False
                    if "zero_if_negative" in item:
                        zero_if_negative = item["zero_if_negative"]

                    zero_if_positive = False
                    if "zero_if_positive" in item:
                        zero_if_positive = item["zero_if_positive"]


                    # Check if var1 is defined
                    if "var" in item:

                        # Get the var1 value
                        var_list = item["var"]

                        # Check if var is a string
                        if type(var_list) == str:

                            # Convert var in a single element list
                            var_list = [ var_list ]

                        # Set the values list
                        values = []

                        # For each variable in the list
                        for var in var_list:

                            # Check if it is a link
                            if "__link__" in var:

                                # Set the field value
                                values.append("prod=" + prod + "&place=" + place + "&date=" + dateTime)

                            # Check if it is a datetime
                            elif "__dateTime__" in var:

                                # Set the field value
                                values.append(dateTime)

                            # Check if it is a iDate
                            elif "__iDate__" in var:
                                try:
                                    # Set the value
                                    values.append(dataset.IDATE)
                                except Exception as e:
                                    pass

                            else:
                                # Get the variable float value

                                # Check if both time and level are none (2D variable)
                                if time is None and level is None: 
                                    # Get the value and append it to the values list
                                    values.append(float(method(dataset.variables[var][Jmin:Jmax, Imin:Imax])))

                                # Check if time is none and level is not (3D variable, not depending by the time)
                                elif time is None and level is not None:
                                    # Get the value and append it to the values list
                                    values.append(float(method(dataset.variables[var][level, Jmin:Jmax, Imin:Imax])))

                                # Check if level is none and time is not (3D variable, not depending by the level)
                                elif time is not None and level is None:
                                    # Get the value and append it to the values list 
                                    values.append(float(method(dataset.variables[var][time, Jmin:Jmax, Imin:Imax])))

                                # If both time and level are not note, it is a 4D variable
                                else:

                                    # Get the value and append it to the values list
                                    values.append(float(method(dataset.variables[var][time, level, Jmin:Jmax, Imin:Imax])))

                        
                        # Check if at least one value is avaliable 
                        if len(values)>0:
                            # Initialize the value
                            value = None

                            # Check if a function have to be applied
                            if func is not None:

                                # Invoke the function
                                value = func(values)
                            else:
                                # Only one value
                                value = values[0]


                            # Check if value is integer of float and not nan
                            if (type(value) == int or type(value) == float) and not math.isnan(value):

                                # Apply the correction
                                value = value * a + b

                                # If needed, set the value as zero if negative
                                if zero_if_negative is True:
                                    if value < 0:
                                        value = 0

                                # If needed, set the value as zero if positive
                                if zero_if_positive is True:
                                    if value > 0:
                                        value = 0

                                # Check if the number have be rounded
                                if round_digits is not None and type(value) == float:

                                    # Round the value
                                    value = round(value, round_digits)
                                
                            # Check if value is valued
                            if (type(value) == float and not math.isnan(value)) or type(value) != float:

                                # Set the value
                                retval[field] = value

                # Close the datase
                dataset.close()

                # Set the result status
                retval['result'] = "ok"

                # Check if the opt parameter is set
                if "opt" in params:

                    # Check if the place info have to be added
                    if "place" in params['opt']:

                        # Add the place info
                        retval['place'] = self.places.get_place_by_id(place, params)

                    # Check if the fields info have to be added
                    if "fields" in params['opt']:

                        # Add the fields info
                        retval['fields'] = self.maps["products"][prod]['fields']
            else:
                # Set the result status
                retval['result'] = "error"

                # Add details to the result status
                retval['details'] = "Data not available"
        else:
            # Set the result status
            retval['result'] = "error"

            # Add details to the result status
            retval['details'] = "Place not indexed"
        
        # Save retval as .json file into cache_jsn
        if use_disk_cached:
            with open(imagePath, "w") as json_file:
                json.dump(retval, json_file, indent=4)
                
        # Return the result
        return retval
        
        # If it gets here it means that the file already exists, so it reads it and returns.
        #with open(imagePath, "r") as json_file:
        #    retval = json.load(json_file)
        #return retval
    
    
    '''
    # DISK-CACHE LOGIC IMPLEMENTED  -- NEW VERSION 
    def modelOutput(self, params=None):

        retval = {}

        prod = self.default_prod
        place = self.default_place

        timeref = None
        year = 0
        month = 0
        day = 0
        hour = 0
        minute = 0


        if params:
            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'place' in params and params['place'] is not None:
                place = params['place']

            if 'date' in params and params['date'] is not None:
                timeref = params['date']

        if timeref is None:
            date = datetime.utcnow()
            year = date.year
            month = date.month
            day = date.day
            hour = int(round(date.hour + date.minute / 60.0))
            minute = 0
        else:
            year = int(timeref[:4])
            month = int(timeref[4:6])
            day = int(timeref[6:8])
            hour = int(timeref[9:11])
            if len(timeref) == 13:
                minute = int(timeref[11:13])

        date = datetime(year, month, day, hour, minute)

        dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + format(date.minute, '02')
        
       
        
        #relativePath = "json" + os.path.sep + place + os.path.sep + prod + os.path.sep  + format(date.year, '04') + os.path.sep  + format(date.month, '02') + os.path.sep  + format(date.day, '02') 
       
        #if os.path.exists(self.config['CACHE_JSON'] + os.path.sep + relativePath) is False:
        #    os.makedirs(self.config['CACHE_JSON'] + os.path.sep + relativePath)

        #imageName = "jsn__" + place + "_" + prod + "_" + dateTime + ".json" 
        #imagePath = self.config['CACHE_JSON'] + os.path.sep + relativePath + os.path.sep + imageName
        

        # imageUrl = self.config['PUB_URL'] + "/" + relativePath + "/" + imageName

 
        # if use_disk_cached is False or os.path.isfile(imagePath) is False or (os.path.isfile(imagePath) is True or (time.time() - os.path.getmtime(imagePath)) > self.config['CACHE_TIMEOUT']):
        
        # Check into disk cache 
        #if use_disk_cached is False or os.path.isfile(imagePath) is False:

            # da qui era indentato di 1 
            # Data not present
           
        # Get the domain and the indeces of the place
        domain_indeces = self.places.get_domain_and_indeces_by_product_and_place(prod, place, date.strftime("%Y%m%dZ%H00"))


        # Check if domain and indeces are correct
        if domain_indeces is not None:

            # Retrieve domain and indeces
            (domain, Jmin, Jmax, Imin, Imax) = domain_indeces


            # Set the dateTime
            dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + format(date.minute, '02')

            dateTimePath = format(date.year, '04') + "/" + format(date.month, '02') + "/" + format(date.day, '02')

            url = self.config['BASE_PATH'] + "/" + prod + "/" + domain + "/" + self.config['HISTORY'] + "/" + dateTimePath + "/" + prod + "_" + domain + "_" + dateTime + ".nc"

            retval = {}

            # Check if the file exists
            dataset = None
        

            try:
                # Open the data file
                dataset = netCDF4.Dataset(url)
            except Exception as e:
                logger.error("[*] netCDF4 error : %s", e)

            # Check if the product is available and if the filds are defined
            if prod in self.maps["products"] and "fields" in self.maps["products"][prod]:

                # For each field in fields
                for field, item in self.maps["products"][prod]["fields"].items():

                    # Set default method
                    # method = "nanmean"
                    method = "mean"

                    # Check if method is defined in item
                    if "method" in item:

                        # Set the method
                        method = item["method"]


                    # Set the method
                    method = getattr(sys.modules["numpy"],method)

                    # Set time to None
                    time = None

                    # Check if time is defined in item
                    if "time" in item:

                        # Set time
                        time = item["time"]

                    # Set level to None
                    level = None

                    # Check if level is in item
                    if "level" in item:

                        # Set level
                        level = item["level"]

                    # Check func to none
                    func = None

                    # Check if func is defined in item
                    if "func" in item:

                        # Get the module and the string module.function
                        parts = item["func"].split(".")

                        # Check if no module is set
                        if len(parts) == 1:

                            # Use the current module as default
                            parts = [ sys.modules[__name__], item["func"]]

                        # Check if the module name is set
                        elif len(parts) == 2:

                            # Use the specified module
                            parts = [ sys.modules[parts[0]], item["func"]]

                        # Try to set the function
                        try:

                            # Set the function pointer
                            func = getattr(parts[0], parts[1])

                        # If inconsistent module/function rise an exception
                        except Exception as e:
                            pass

                    a = 1
                    if "a" in item:
                        a = item["a"]

                    b = 0
                    if "b" in item:
                        b = item["b"]

                    round_digits = None
                    if "round" in item:
                        round_digits = item["round"]


                    zero_if_negative = False
                    if "zero_if_negative" in item:
                        zero_if_negative = item["zero_if_negative"]

                    zero_if_positive = False
                    if "zero_if_positive" in item:
                        zero_if_positive = item["zero_if_positive"]


                    # Check if var1 is defined
                    if "var" in item:

                        # Get the var1 value
                        var_list = item["var"]

                        # Check if var is a string
                        if type(var_list) == str:

                            # Convert var in a single element list
                            var_list = [ var_list ]
                        

                        # Set the values list
                        values = []

                        # For each variable in the list
                        for var in var_list:


                            # Check if it is a link
                            if "__link__" in var:

                                # Set the field value
                                values.append("prod=" + prod + "&place=" + place + "&date=" + dateTime)

                            # Check if it is a datetime
                            elif "__dateTime__" in var:

                                # Set the field value
                                values.append(dateTime)

                            # Check if it is a iDate
                            elif "__iDate__" in var:
                                try:
                                    # Set the value
                                    values.append(dataset.IDATE)
                                except Exception as e:
                                    pass

                            else:
                                # Get the variable float value
                                
                                # Check if both time and level are none (2D variable)
                                if time is None and level is None: 
                                    # Get the value and append it to the values list
                                    values.append(float(method(dataset.variables[var][Jmin:Jmax, Imin:Imax])))

                                # Check if time is none and level is not (3D variable, not depending by the time)
                                elif time is None and level is not None:

                                    # Get the value and append it to the values list

                                    values.append(float(method(dataset.variables[var][level, Jmin:Jmax, Imin:Imax])))

                                # Check if level is none and time is not (3D variable, not depending by the level)
                                elif time is not None and level is None:
                                    values.append(float(method(dataset.variables[var][time, Jmin:Jmax, Imin:Imax])))

                                
                                # If both time and level are not note, it is a 4D variable
                                else:
                                    # Get the value and append it to the values list
                                    values.append(float(method(dataset.variables[var][time, level, Jmin:Jmax, Imin:Imax])))


                        # Check if at least one value is avaliable 
                        if len(values)>0:
                            # Initialize the value
                            value = None

                            # Check if a function have to be applied
                            if func is not None:
                                # Invoke the function
                                value = func(values)
                            else:
                                # Only one value
                                value = values[0]


                            # Check if value is integer of float and not nan
                            if (type(value) == int or type(value) == float) and not math.isnan(value):

                                # Apply the correction
                                value = value * a + b

                                # If needed, set the value as zero if negative
                                if zero_if_negative is True:
                                    if value < 0:
                                        value = 0

                                # If needed, set the value as zero if positive
                                if zero_if_positive is True:
                                    if value > 0:
                                        value = 0

                                # Check if the number have be rounded
                                if round_digits is not None and type(value) == float:

                                    # Round the value
                                    value = round(value, round_digits)
                                
                            # Check if value is valued
                            if (type(value) == float and not math.isnan(value)) or type(value) != float:

                                # Set the value
                                retval[field] = value
                            
                # Close the datase
                dataset.close()

                # Set the result status
                retval['result'] = "ok"

                # Check if the opt parameter is set
                if "opt" in params:

                    # Check if the place info have to be added
                    if "place" in params['opt']:

                        # Add the place info
                        retval['place'] = self.places.get_place_by_id(place, params)

                    # Check if the fields info have to be added
                    if "fields" in params['opt']:

                        # Add the fields info
                        retval['fields'] = self.maps["products"][prod]['fields']
            else:
                # Set the result status
                retval['result'] = "error"

                # Add details to the result status
                retval['details'] = "Data not available"
        else:
            # Set the result status
            retval['result'] = "error"

            # Add details to the result status
            retval['details'] = "Place not indexed"
        

        #TODO call set to disk-cache manage 
        # Save retval as .json file into cache_jsn
        #with open(imagePath, "w") as json_file:
        #    json.dump(retval, json_file, indent=4)
        
        # Return the result
        return retval

        #with open(imagePath, "r") as json_file:
        #    print(f"\n\njson presente in cache e considerato\n\n")
        #    retval = json.load(json_file)
        #return retval
    '''

    
    def ModelPlotUrl(self, use_disk_cached=True, params=None):
        """Implement model plot url for meteo services."""

        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        retval = {}

        prod = self.default_prod
        output = self.default_output
        place = self.default_place
        width = self.default_xdim
        height = self.default_ydim
        lang = self.default_lang

        timeref = None
        year = 0
        month = 0
        day = 0
        hour = 0
        minute = 0

        bars = False
        if params:
            if 'lang' in params and params['lang'] is not None:
                lang = params['lang']

            if 'opt' in params and params['opt'] is not None:
                if "bars" in params['opt'] and 'true' in params['opt']['bars']:
                    bars = True

            if 'width' in params and params['width'] is not None:
                width = int(params['width'])

            if 'height' in params and params['height'] is not None:
                height = int(params['height'])

            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'output' in params and params['output'] is not None:
                output = params['output']

            if 'place' in params and params['place'] is not None:
                place = params['place']

            if 'date' in params and params['date'] is not None:
                timeref = params['date']

        if timeref is None:
            # print "get current utc"
            date = datetime.utcnow()
            year = date.year
            month = date.month
            day = date.day
            hour = int(round(date.hour + date.minute / 60.0))
            minute = 0
        else:
            # print "Date is provided"
            year = int(timeref[:4])
            month = int(timeref[4:6])
            day = int(timeref[6:8])
            hour = int(timeref[9:11])
            if len(timeref) == 13:
                minute = int(timeref[11:13])

        dry = str(params['dry'])
        date = datetime(year, month, day, hour, minute)
        # Set the dateTime
        # dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + format(date.minute, '02')
        dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + "00"

        relativePath, imageName = self.plotter.render(place, prod, output, dateTime, language=lang, draw_colorbars=bars)

        imagePath = self.config['BASE_PRODUCTS'] + "/" + relativePath + "/" + imageName
        imageUrl = self.config['PUB_URL'] + "/" + relativePath + "/" + imageName

        retval['link'] = imageUrl

        return retval, imageName
    

    '''
    # DISK-CACHE LOGIC IMPLEMENTED  -- NEW VERSION 
    def ModelPlotUrl(self, result_file, params=None):
        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        retval = {}

        prod = self.default_prod
        output = self.default_output
        place = self.default_place
        width = self.default_xdim
        height = self.default_ydim
        lang = self.default_lang

        timeref = None
        year = 0
        month = 0
        day = 0
        hour = 0
        minute = 0

        bars = False
        if params:
            if 'lang' in params and params['lang'] is not None:
                lang = params['lang']

            if 'opt' in params and params['opt'] is not None:
                if "bars" in params['opt'] and 'true' in params['opt']['bars']:
                    bars = True

            if 'width' in params and params['width'] is not None:
                width = int(params['width'])

            if 'height' in params and params['height'] is not None:
                height = int(params['height'])

            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'output' in params and params['output'] is not None:
                output = params['output']

            if 'place' in params and params['place'] is not None:
                place = params['place']

            if 'date' in params and params['date'] is not None:
                timeref = params['date']

        if timeref is None:
            # print "get current utc"
            date = datetime.utcnow()
            year = date.year
            month = date.month
            day = date.day
            hour = int(round(date.hour + date.minute / 60.0))
            minute = 0
        else:
            # print "Date is provided"
            year = int(timeref[:4])
            month = int(timeref[4:6])
            day = int(timeref[6:8])
            hour = int(timeref[9:11])
            if len(timeref) == 13:
                minute = int(timeref[11:13])

        dry = str(params['dry'])

        # date = datetime(year, month, day, hour, minute)
        # Set the dateTime
        # dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + format(date.minute, '02')
        dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + "00"
                
        # relativePath, imageName = self.plotter.render(place, prod, output, dateTime, result_file, language=lang, draw_colorbars=bars)

        imageName = self.plotter.render(place, prod, output, dateTime, result_file, language=lang, draw_colorbars=bars)
        logger.debug("imageName: %s", imageName)

        if imageName is not None:
            #imagePath = self.config['BASE_PRODUCTS'] + "/" + relativePath + "/" + imageName
            # imageUrl = self.config['PUB_URL'] + "/" + relativePath + "/" + imageName
            # retval['link'] = imageUrl
            # print(f"\n\nModelPlotUrl -- retval : {retval}\n\n\n")
            return imageName  
        #return retval, imageName
    '''

    
    def ModelPlotImage(self, use_disk_cached=True, params=None):
        """Implement model plot image for meteo services."""

        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        retval = {}

        prod = self.default_prod
        output = self.default_output
        place = self.default_place
        width = self.default_xdim
        height = self.default_ydim
        lang = self.default_lang

        timeref = None
        year = 0
        month = 0
        day = 0
        hour = 0
        minute = 0

        bars = False

        if params:
            if 'lang' in params and params['lang'] is not None:
                lang = params['lang']

            if 'opt' in params and params['opt'] is not None:
                #if "bars" in params['opt'] and 'true' in params['opt']['bars']:
                if "bars" in params['opt']:
                    bars = True

            if 'width' in params and params['width'] is not None:
                width = int(params['width'])

            if 'height' in params and params['height'] is not None:
                height = int(params['height'])

            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'output' in params and params['output'] is not None:
                output = params['output']

            if 'place' in params and params['place'] is not None:
                place = params['place']

            if 'date' in params and params['date'] is not None:
                timeref = params['date']
        

        if timeref is None:
            # print "get current utc"
            date = datetime.utcnow()
            year = date.year
            month = date.month
            day = date.day
            hour = int(round(date.hour + date.minute / 60.0))
            minute = 0
        else:
            # print "Date is provided"
            year = int(timeref[:4])
            month = int(timeref[4:6])
            day = int(timeref[6:8])
            hour = int(timeref[9:11])
            if len(timeref) == 13:
                minute = int(timeref[11:13])

        dry = str(params['dry'])

        date = datetime(year, month, day, hour, minute)

        # Set the dateTime
        dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + format(date.minute, '02')

        # Assemble the relative path
        relativePath = "plt" + os.path.sep + place + os.path.sep + prod + os.path.sep  + format(date.year, '04') + os.path.sep  + format(date.month, '02') + os.path.sep  + format(date.day, '02') 

        #if os.path.exists(self.config['BASE_PRODUCTS'] + os.path.sep + relativePath) is False:
        #    os.makedirs(self.config['BASE_PRODUCTS'] + os.path.sep + relativePath)

        # Assemble the image name
        imageName = "plt_" + place + "_" + prod + "_" + dateTime + "_" + output + "_1024x768.png" 
        imagePath = self.config['BASE_PRODUCTS'] + os.path.sep + relativePath + os.path.sep + imageName
        imageUrl = self.config['PUB_URL'] + "/" + relativePath + "/" + imageName
        
        retval['link'] = imageUrl

        if os.path.exists(self.config['BASE_PRODUCTS'] + os.path.sep + relativePath) is False:
            os.makedirs(self.config['BASE_PRODUCTS'] + os.path.sep + relativePath)
        else:
            path_archive = MakeArchivePaths.makePath(params['prod'], params['place'], timeref)

            if os.path.isfile(imagePath):
                
                logger.info("DISK 3 : Check if valid file !")
                
                if (os.path.isfile(path_archive) is True) and (os.path.getmtime(path_archive) > os.path.getmtime(imagePath)):
                    logger.info(f"DISK 3 : File '{imagePath}' not consistent respect to ARCHIVE file !")  
                    os.remove(imagePath)
                    logger.info(f"DISK 3 : File '{imagePath}' deleted !")
                else:
                    logger.info(f"DISK 3 : delta time expired {(time.time() - os.path.getmtime(imagePath))} !")
                    if time.time() - os.path.getmtime(imagePath) > self.config['TTL_DISKCACHE']:
                        logger.info(f"DISK 3 : File ( {imagePath} ) expired !")
                        os.remove(imagePath)
                        logger.info(f"DISK 3 : File ( {imagePath} ) deleted !")
                    else: 
                        with open(imagePath, 'rb') as content_file:
                            retval = content_file.read()
                            content_file.close()
                        return retval, imageName

        # if use_disk_cached is False or os.path.isfile(imagePath) is False or (os.path.isfile(imagePath) is True or (time.time() - os.path.getmtime(imagePath)) > self.config['CACHE_TIMEOUT']):
            # Creation image 
        #    self.plotter.render(place, prod, output, dateTime, language=lang, draw_colorbars=bars)

        self.plotter.render(place, prod, output, dateTime, language=lang, draw_colorbars=bars)

        # retval['link'] = imageUrl
        
        try:
            with open(imagePath, 'rb') as content_file:
            #with open(imagePath, 'r') as content_file:
                retval = content_file.read()
                content_file.close()
        except Exception as e:
            
            imagePath = self.config['NOIMAGE_PATH']
            imageUrl = self.config['NOIMAGE_URL']

            with open(imagePath, 'rb') as content_file:
                retval = content_file.read()
                content_file.close()
                
            # retval['link'] = imagePath
            
        return retval, imageName
    

    '''
    # DISK-CACHE LOGIC IMPLEMENTED  -- NEW VERSION 
    def ModelPlotImage(self, result_path, params=None):
    # def ModelPlotImage(self, use_disk_cached=True, params=None):

        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        retval = {}

        prod = self.default_prod
        output = self.default_output
        place = self.default_place
        width = self.default_xdim
        height = self.default_ydim
        lang = self.default_lang

        timeref = None
        year = 0
        month = 0
        day = 0
        hour = 0
        minute = 0

        bars = False

        if params:
            if 'lang' in params and params['lang'] is not None:
                lang = params['lang']

            if 'opt' in params and params['opt'] is not None:
                #if "bars" in params['opt'] and 'true' in params['opt']['bars']:
                if "bars" in params['opt']:
                    bars = True

            if 'width' in params and params['width'] is not None:
                width = int(params['width'])

            if 'height' in params and params['height'] is not None:
                height = int(params['height'])

            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'output' in params and params['output'] is not None:
                output = params['output']

            if 'place' in params and params['place'] is not None:
                place = params['place']

            if 'date' in params and params['date'] is not None:
                timeref = params['date']
        
        
        if timeref is None:
            # print "get current utc"
            date = datetime.utcnow()
            year = date.year
            month = date.month
            day = date.day
            hour = int(round(date.hour + date.minute / 60.0))
            minute = 0
        else:
            # print "Date is provided"
            year = int(timeref[:4])
            month = int(timeref[4:6])
            day = int(timeref[6:8])
            hour = int(timeref[9:11])
            if len(timeref) == 13:
                minute = int(timeref[11:13])

        dry = str(params['dry'])

        date = datetime(year, month, day, hour, minute)

        # Set the dateTime
        dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + format(date.minute, '02')
        
        
        
        # Assemble the relative path
        #relativePath = "plt" + os.path.sep + place + os.path.sep + prod + os.path.sep  + format(date.year, '04') + os.path.sep  + format(date.month, '02') + os.path.sep  + format(date.day, '02') 

        #if os.path.exists(self.config['BASE_PRODUCTS'] + os.path.sep + relativePath) is False:
        #    os.makedirs(self.config['BASE_PRODUCTS'] + os.path.sep + relativePath)

        # Assemble the image name
        #imageName = "plt_" + place + "_" + prod + "_" + dateTime + "_" + output + "_1024x768.png" 

        #imagePath = self.config['BASE_PRODUCTS'] + os.path.sep + relativePath + os.path.sep + imageName
        #imageUrl = self.config['PUB_URL'] + "/" + relativePath + "/" + imageName
                
        #if use_disk_cached is False or os.path.isfile(imagePath) is False or (os.path.isfile(imagePath) is True or (time.time() - os.path.getmtime(imagePath)) > self.config['CACHE_TIMEOUT']):
            # Creation image 
        

        self.plotter.render(place, prod, output, dateTime, result_path, language=lang, draw_colorbars=bars)

        
        #retval['link'] = imageUrl
        # 
        #try:
        #    with open(imagePath, 'rb') as content_file:
        #    #with open(imagePath, 'r') as content_file:
        #        retval = content_file.read()
        #        content_file.close()
        #except Exception as e:
            
        #    imagePath = self.config['NOIMAGE_PATH']
        #    imageUrl = self.config['NOIMAGE_URL']

        #    with open(imagePath, 'rb') as content_file:
        #        retval = content_file.read()
        #        content_file.close()
                
            # retval['link'] = imagePath
        
        #return retval, imageName
    '''   

    def ModelPlotSkewT(self, use_disk_cached=True, params=None):
        """Implement model plot skew t for meteo services."""

        retval = {}

        prod = self.default_prod
        place = self.default_place
        lat = None
        lon = None

        timeref = None
        year = 0
        month = 0
        day = 0
        hour = 0
        minute = 0

        bars = False

        if params:
            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']
            
            if 'lat' in params and params['lat'] is not None:
                lat = float(params['lat'])
            
            if 'lon' in params and params['lon'] is not None:
                lon = float(params['lon'])
        

        if timeref is None:
            # print "get current utc"
            date = datetime.utcnow()
            year = date.year
            month = date.month
            day = date.day
            hour = int(round(date.hour + date.minute / 60.0))
            minute = 0
        else:
            # print "Date is provided"
            year = int(timeref[:4])
            month = int(timeref[4:6])
            day = int(timeref[6:8])
            hour = int(timeref[9:11])
            if len(timeref) == 13:
                minute = int(timeref[11:13])

        date = datetime(year, month, day, hour, minute)

        # Assemble the relative path
        relativePath = format(date.year, '04') + os.path.sep  + format(date.month, '02') + os.path.sep  + format(date.day, '02') 

        # Set the dateTime
        dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + format(date.minute, '02')

        # Assemble the image name
        lat_without_dot = str(lat).replace(".", "")
        lon_without_dot = str(lon).replace(".", "")
        imageName = "plt_" + place + "_" + prod + "_" + lat_without_dot + "_" + lon_without_dot + "_" + dateTime + "_1024x768.png"
        #imageName = "plt_" + place + "_" + prod + "_" + dateTime + "_1024x768.png" 
        imagePath = self.config['BASE_SKEWT'] + os.path.sep + relativePath + os.path.sep + imageName
        imageUrl = self.config['PUB_URL'] + "/" + relativePath + "/" + imageName   

        retval['link'] = imageUrl

        path_archive = MakeArchivePaths.makePath(params['prod'], None, timeref, True, lat, lon)

        if os.path.exists(self.config['BASE_SKEWT'] + os.path.sep + relativePath) is False:
            os.makedirs(self.config['BASE_SKEWT'] + os.path.sep + relativePath)
        else:
            if os.path.isfile(imagePath):
                
                if os.path.getmtime(path_archive) > os.path.getmtime(imagePath):
                    logger.info(f"DISK 4 : File '{imagePath}' not consistent respect to ARCHIVE file !")  
                    os.remove(imagePath)
                    logger.info(f"DISK 4 : File '{imagePath}' deleted !")
                else:
                    # logger.info(f"DISK 4 : delta time expired {(time.time() - os.path.getmtime(imagePath))} !")
                    if time.time() - os.path.getmtime(imagePath) > self.config['TTL_DISKCACHE']:
                        logger.info(f"DISK 4 : File ( {imagePath} ) expired !")
                        os.remove(imagePath)
                        logger.info(f"DISK 4 : File ( {imagePath} ) deleted !")
                    else: 
                        logger.info("DISK 4 : Present !")
                        with open(imagePath, 'rb') as content_file:
                            retval = content_file.read()
                            content_file.close()
                        return retval, imageName
        
        SkewTServices(path_archive).SkewTPlot(imagePath, lat, lon)

        try:
            with open(imagePath, 'rb') as content_file:
                retval = content_file.read()
                content_file.close()
        except Exception as e:
            
            imagePath = self.config['NOIMAGE_PATH']
            imageUrl = self.config['NOIMAGE_URL']

            with open(imagePath, 'rb') as content_file:
                retval = content_file.read()
                content_file.close()
                
            # retval['link'] = imagePath
            
        return retval, imageName


    def getlegenddata(self, prod, position, output, params=None):
        """Implement getlegenddata for meteo services."""
        data = None
        width = self.default_xdim
        height = self.default_ydim
        lang = "en-US"
        # lang = "it-IT"

        if params is not None:
            if "lang" in params and params['lang'] is not None:
                # lang = 'it-IT'
                lang = params['lang']

            if 'width' in params and params['width'] is not None:
                width = int(params['width'])

            if 'height' in params and params['height'] is not None:
                height = int(params['height'])

        # Generate a bitmap
        imgName = "legend_" + prod + "_" + position + "_" + output + "_" + str(width) + "x" + str(
            height) + ":" + lang + ".png"
        imgPath = self.config['BASE_PRODUCTS'] + "/legend/" + imgName

        # print("imgPath : " + imgPath)
        # log.info("imgPath : " + imgPath)

        basePath = "/project/var/bars"
        fileName = basePath + "/" + prod + "/bar_" + prod + "_" + output + "_" + position[0].lower() + ":" + lang + ".png"
        
        size = (width, height)

        if os.path.isfile(fileName):
            # print("file exist")
            img = Image.open(fileName)
            img.thumbnail(size, Image.ANTIALIAS)
        else:
            # print("file not exist")
            img = Image.new('RGBA', size)

        img.save(imgPath, 'PNG')

        with open(imgPath, 'rb') as content_file:
            data = content_file.read()

        return data

    def getlegenddata1(self, prod, position, output, params=None):
        """Implement getlegenddata1 for meteo services."""
        place = "ca004"
        data = None
        legendTheme = None

        width = self.default_xdim
        height = self.default_ydim

        timeref = None
        year = 0
        month = 0
        day = 0
        hour = 0
        minute = 0

        if params:
            if 'width' in params and params['width'] is not None:
                width = int(params['width'])

            if 'height' in params and params['height'] is not None:
                height = int(params['height'])

            if 'date' in params and params['date'] is not None:
                timeref = params['date']

        if timeref is None:
            # print "get current utc"
            date = datetime.utcnow()
            year = date.year
            month = date.month
            day = date.day
            hour = int(round(date.hour + date.minute / 60.0))
            minute = 0
        else:
            # print "Date is provided"
            year = int(timeref[:4])
            month = int(timeref[4:6])
            day = int(timeref[6:8])
            hour = int(timeref[9:11])
            if len(timeref) == 13:
                minute = int(timeref[11:13])

        # print "Place:"+str(place)
        date = datetime(year, month, day, hour, minute)
        # print "date:"+str(date)

        for theme in self.maps['products'][prod]['outputs'][output]['wms']:
            for item in theme:
                if "LEGEND" in item and position in theme['LEGEND']:
                    legendTheme = theme
                    break
            if legendTheme is not None:
                break

        if legendTheme is not None:


            # Get the domain and the indeces of the place
            domain_indeces = self.places.get_domain_and_indeces_by_product_and_place(prod, place)

            # Check if domain and indeces are correct
            if domain_indeces is not None:

                # Retrieve domain and indeces
                (domain, Jmin, Jmax, Imin, Imax) = domain_indeces

                # Set the dateTime
                dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(
                    int(round(date.hour + date.minute / 60.0)), '02') + "00"
                dateTimePath = format(date.year, '04') + "/" + format(date.month, '02') + "/" + format(date.day, '02')

                url = self.config['WMS_URL'] + "/lds/opendap/" + prod + "/" + domain + "/" + self.config[
                    'HISTORY'] + "/" + dateTimePath + "/" + prod + "_" + domain + "_" + dateTime + ".nc?"

                # url=url+'COLORBARONLY=true&'
                url = url + "LAYERS=" + theme['LAYERS'] + "&"

                url = url + 'COLORSCALERANGE=' + legendTheme['COLORSCALERANGE'] + "&"
                url = url + 'NUMCOLORBANDS=' + legendTheme['NUMCOLORBANDS'] + "&"
                url = url + 'ABOVEMAXCOLOR=' + legendTheme['ABOVEMAXCOLOR'] + "&"
                url = url + 'BELOWMINCOLOR=' + legendTheme['BELOWMINCOLOR'] + "&"
                url = url + 'BGCOLOR=' + legendTheme['BGCOLOR'] + "&"
                url = url + 'LOGSCALE=' + legendTheme['LOGSCALE'] + "&"
                url = url + 'STYLES=' + legendTheme['STYLES'] + "&"

                url = url + "FORMAT=image/png&"
                # url=url+"PALETTE=default&"

                if "top" in position or "bottom" in position:
                    url = url + "VERTICAL=false&"

                url = url + "SERVICE=WMS&VERSION=1.1.1&REQUEST=GetLegendGraphic&"
                url = url + "WIDTH=" + str(width) + "&HEIGHT=" + str(height)

                # print("-------------->"+str(url))

                try:
                    response = requests.get(url, stream=True)

                    if response.ok:
                        data = requests.get(url).content
                except:
                    pass

        if data is None:
            # Generate a bitmap
            imgName = "legend_" + prod + "_" + position + "_" + output + "_" + str(width) + "x" + str(height) + ".png"
            imgPath = self.config['BASE_PRODUCTS'] + "/legend/" + imgName
            img = Image.new('RGBA', (width, height))
            img.save(imgPath, 'PNG')
            with open(imgPath, 'rb') as content_file:
                data = content_file.read()

        return data

    def plotmetacharts(self, prod, output):
        """Implement plotmetacharts for meteo services."""
     
            
        retval = {"meta-chart": {}}
        chart = (
            self.maps
            .get("products", {})
            .get(prod, {})
            .get("outputs", {})
            .get(output, {})
            .get("chart", {})
        )


        for key in [ "title_chart", "title_bars", "var_bars", "pos_bars", "unit_bars", "clevels", "ccolors", "title_line", "var_line", "pos_line", "unit_line", "values_line" ]:
            if key in chart:
                retval["meta-chart"][key] = chart[key]

        return retval
    
    def timeseries(self, params=None):
        """Implement timeseries for meteo services."""

        retval = {}

        prod = self.default_prod
        place = self.default_place

        timeref = None
        step = 1
        hours = 0
        use_step_cache = True

        if params:

            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'place' in params and params['place'] is not None:
                place = params['place']

            if 'date' in params and params['date'] is not None:
                timeref = params['date']

            if 'step' in params:
                step = int(params['step'])
            else:
                step = 1

            if 'hours' in params:
                hours = int(params['hours'])
            else:
                hours = 0

            if 'use_disk_cached' in params:
                use_step_cache = bool(params['use_disk_cached'])

        date = self._parse_datetime_ref(timeref, default_midnight=(timeref is None))


        # Get the domain and the indeces of the place
        domain_indeces = self.places.get_domain_and_indeces_by_product_and_place(prod, place)


        # Check if domain and indeces are correct
        if domain_indeces is not None:

            # Retrieve domain and indeces
            (domain, Jmin, Jmax, Imin, Imax) = domain_indeces

            retval = {"timeseries": []}

            forecast = {}
            items = []
            count = 0
            while count < 168:
                dateTime = self._format_datetime_ref(date)
                dateTimePath = date.strftime("%Y/%m/%d")
        
                #TODO: replace "/" with os.path.sep 
                url = self.config['BASE_PATH'] + "/" + prod + "/" + domain + "/" + self.config['ARCHIVE'] + "/" + dateTimePath + "/" + prod + "_" + domain + "_" + dateTime + ".nc"

                if os.path.isfile(url):
                    items.append({"prod": prod, "place": place, "date": dateTime})
                else:
                    break
                date = date + timedelta(hours=1)
                count = count + 1

            cached_items = []
            uncached_items = items
            if use_step_cache and items:
                cached_items = [item for item in items if self._is_model_output_cache_valid(item)]
                uncached_items = [item for item in items if item not in cached_items]

            model_outputs = []
            if cached_items:
                model_outputs.extend(self._load_timeseries_cached_outputs(cached_items))
            if uncached_items:
                if use_step_cache:
                    model_outputs.extend(self._compute_timeseries_uncached_outputs(uncached_items))
                else:
                    thread_workers = self._timeseries_thread_workers(len(uncached_items))
                    with ThreadPoolExecutor(max_workers=thread_workers) as executor:
                        model_outputs.extend(
                            list(executor.map(
                                lambda item: self.modelOutput(item, use_disk_cached=False),
                                uncached_items
                            ))
                        )

            for model_output in model_outputs:
                forecast[model_output["dateTime"]]=model_output

            keys = sorted(forecast)
            if hours == 0:
                hours = len(keys)
            
            if len(keys) == len(items) or 1 == 1:
                autostep = 0
                if step < 1:
                    autostep = 1
                    step = self.maps["products"][prod]['autosteps'][autostep - 1]

                if step == 1 and autostep == 0:
                    hour = 0
                    for key in keys:
                        retval["timeseries"].append(forecast[key])
                        hour = hour + 1
                        if hour == hours:
                            break
                else:
                    count = 0
                    sums = {}
                    maxs = {}
                    mins = {}
                    iDate = None
                    dateTime = None
                    hour = 0
                    for key in keys:
                        if count == 0:
                            # log.info("----------------- MeteoServices : enter in ( if count == 0 )")

                            # initialize
                            dateTime = forecast[key]['dateTime']
                            if 'iDate' in forecast[key]:
                                iDate = forecast[key]['iDate']
                                # print "init:",dateTime
                            for field in forecast[key]:

                                if field in self.maps["products"][prod]['fields']:
                                   
                                    if 'aggregate' in self.maps["products"][prod]['fields'][field]:

                                        aggregateList = self.maps["products"][prod]['fields'][field]['aggregate']

                                        if any("sum" in s for s in aggregateList) or any("ave" in s for s in aggregateList):
                                            sums[field] = forecast[key][field]

                                        if any("min" in s for s in aggregateList):
                                            mins[field] = forecast[key][field]

                                        if any("max" in s for s in aggregateList):
                                            maxs[field] = forecast[key][field]
                        else:
                          
                            for field in forecast[key]:

                                if field in self.maps["products"][prod]['fields'] : 
                                
                                    if 'aggregate' in self.maps["products"][prod]['fields'][field]:
                                        aggregateList = self.maps["products"][prod]['fields'][field]['aggregate']
                                        if any("sum" in s for s in aggregateList) or any("ave" in s for s in aggregateList):
                                            sums[field] = sums[field] + forecast[key][field]

                                        if any("max" in s for s in aggregateList):
                                            if forecast[key][field] > maxs[field]:
                                                maxs[field] = forecast[key][field]

                                        if any("min" in s for s in aggregateList):
                                            if forecast[key][field] < mins[field]:
                                                mins[field] = forecast[key][field]

                        count = count + 1
                        if count == step:

                          
                            # print "aggr:",dateTime
                            # print str(sums)
                            # print str(mins)
                            # print str(maxs)
                            # aggregate
                            aggregated = {}
                            for field in forecast[key]:



                                if field in self.maps["products"][prod]['fields']: 

                                    # log.info("[*][*][*][*] field : " + str(field))

                                    # if field == "mcape":
                                    #    log.info("[*][*][*][*] mcape type : " + str(type(self.maps["products"][prod]['fields'][field])))



                                    if 'aggregate' in self.maps["products"][prod]['fields'][field]:
                                        aggregateList = self.maps["products"][prod]['fields'][field]['aggregate']
                                        if any("ave" in s for s in aggregateList):
                                            aggregated[field] = round(1.0 * sums[field] / count,
                                                                    self.maps["products"][prod]['fields'][field]['round'])

                                        if any("sum" in s for s in aggregateList):
                                            aggregated[field] = round(sums[field],
                                                                    self.maps["products"][prod]['fields'][field]['round'])

                                        if any("min" in s for s in aggregateList):
                                            aggregated[field + "-min"] = round(mins[field], self.maps["products"][prod]['fields'][field]['round'])

                                        if any("max" in s for s in aggregateList):
                                            aggregated[field + "-max"] = round(maxs[field],
                                                                            self.maps["products"][prod]['fields'][field][
                                                                                'round'])

                            aggregated["dateTime"] = dateTime
                            if iDate is not None:
                                aggregated["iDate"] = iDate
                            aggregated["link"] = "product=" + prod + "&place=" + place + "&date=" + dateTime
                            try:
                                aggregated['wchill'] = windChill(aggregated["t2c"], aggregated["ws10"])
                            except Exception as e:
                                pass

                            try:
                                aggregated['winds'] = windS(aggregated["wd10"])
                            except Exception as e:
                                # log.info("----------------- MeteoServices -  error windS : " + str(e))
                                pass

                            try:
                                current = {
                                    "date": dateTime,
                                    "crh": aggregated["crh"],
                                    "clf": aggregated["clf"]
                                }
                                aggregated['icon'], aggregated['text'] = iconText(current)
                                aggregated['icon'] = aggregated['icon'].replace("_night", "")
                                # print aggregated['icon']
                            except Exception as e:
                                # print(str(e))
                                pass
                            
                            try:
                                aggregated['icon'] = significantHeightIcon([aggregated['hs']])
                            except Exception as e:
                                logger.info(f"error : {e}")
                                pass
                            
                            try:
                                aggregated['icon'] = surfaceCurrentIcon([aggregated['scm']])
                            except Exception as e:
                                logger.info(f"error : {e}")
                            
                            try:
                                aggregated['icon'] = concentrationParticles([aggregated['sts']])
                            except Exception as e:
                                logger.info(f"error : {e}")
                            
                            try:
                                aggregated['icon'] = musselContaminationIcon([aggregated['mci']])
                            except Exception as e:
                                logger.info(f"error : {e}")
                            
                            # log.info("----------------- MeteoServices -  aggregated : " + str(aggregated))

                            # save
                            retval["timeseries"].append(aggregated)
                            # log.info("[*][*][*][*] aggregated : " + str(aggregated))
                            if autostep > 0:
                                autostep = autostep + 1
                                step = self.maps["products"][prod]['autosteps'][autostep - 1]

                            count = 0

                # self.addDerivatedParams(retval['timeseries'])
                retval['result'] = "ok"

                if "opt" in params:
                    if "place" in params['opt']:
                        retval['place'] = self.places.get_place_by_id(place, params)
                    if "fields" in params['opt']:
                        retval['fields'] = self.maps["products"][prod]['fields']
            else:
                retval['result'] = "error"
                retval['details'] = "Data error"
        else:
            retval['result'] = "error"
            retval['details'] = "Place not indexed"

        
        #log.info("----------------- MeteoServices - retval " + str(retval))

        return retval

    def modelcharturl(self, params=None):
        """Implement modelcharturl for meteo services."""
        # log.info("modelcharturl")
        # url = self.base_url + 'charts.php'
        url = self.config['BASE_URL'] + '/charts.php'
        prod = self.default_prod
        place = self.default_place
        output = 'tsp'
        hours = 144
        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        day = now.strftime('%d')
        step = 1
        md5 = ""
        hour = '00'

        if params:
            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']
            if 'place' in params and params['place'] is not None:
                place = params['place']
            if 'step' in params and params['step'] is not None:
                step = params['step']
            if 'hours' in params and params['hours'] is not None:
                hours = params['hours']
            if 'output' in params and params['output'] is not None:
                output = params['output']
            if 'md5' in params and params['md5'] is not None:
                md5 = params['md5']

        date = str(year) + str(month) + str(day) + 'Z' + hour

        fields = {
            'dry': 'true',
            'prod': urllib.quote_plus(prod),
            'place': urllib.quote_plus(place),
            'output': urllib.quote_plus(output),
            'date': urllib.quote_plus(date),
            'step': urllib.quote_plus(str(step)),
            'hours': urllib.quote_plus(str(hours)),
            'md5': urllib.quote_plus(str(md5))
        }

        full_link = self.__getFullLink(url, fields)
        if "DEBUG" in os.environ:
            logger.debug("full_link: %s", full_link)

        data = self.__executeRequest(full_link)
        # log.info("full_link: " + str(full_link))
        # log.info("data     : " + str(data))
        if not data:
            return self.__statusCode['404']
        try:
            result = xmltodict.parse(data)
        except:
            return self.__statusCode['400']
        return result
        
    
    # funziona aggiunta dalle vecchie API 
    def modelmapurl_or_image(self, use_disk_cached=True, params = None):
        """Implement modelmapurl or image for meteo services."""
        retval = {}

        # places = Places(app.application.config)
        prod = self.default_prod
        output = self.default_output
        place = self.default_place
        width = self.default_xdim
        height = self.default_ydim

        timeref = None
        year=0
        month=0
        day=0
        hour=0
        minute=0


        if params:
            if 'width' in params and params['width'] is not None:
                width = int(params['width'])

            if 'height' in params and params['height'] is not None:
                height = int(params['height'])

            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'output' in params and params['output'] is not None:
                output = params['output']

            if 'place' in params and params['place'] is not None:
                place = params['place']

            if 'date' in params and params['date'] is not None:
                timeref = params['date']

        if timeref is None:
            date=datetime.utcnow()
            year=date.year
            month=date.month
            day=date.day
            hour=int(round(date.hour+date.minute/60.0))
            if hour>23:
                hour=23
            minute=0
        else:
            #print "Date is provided"
            year=int(timeref[:4])
            month=int(timeref[4:6])
            day=int(timeref[6:8])
            hour=int(timeref[9:11])
            if len(timeref)==13:
                minute=int(timeref[11:13])

        # Get dry
        dry = str(params['dry'])

        #print "Place:"+str(place) 
        date=datetime(year, month, day, hour, minute)
        #print "date:"+str(date)

        # Get place data
        #params = {'id':place,'filter':None, 'prod':prod}
        #print str(place)+":"+str(params)

        # Set the dateTime
        dateTime=format(date.year,'04')+format(date.month,'02')+format(date.day,'02')+"Z"+format(date.hour,'02')+format(date.minute,'02')
        dateTimePath=format(date.year,'04')+"/"+format(date.month,'02')+"/"+format(date.day,'02')

        imageName="map_"+place+"_"+prod+"_"+dateTime+"_"+output+"_"+str(width)+"x"+str(height)+".png"
        relativePath="map/"+place+"/"+prod+"/"+dateTimePath

        # Check if the directory exists
        if os.path.exists(self.config['BASE_PRODUCTS']+"/"+relativePath) is False:
        
            # Create the directory
            os.makedirs(self.config['BASE_PRODUCTS']+"/"+relativePath)

        imagePath=self.config['BASE_PRODUCTS']+"/"+relativePath+"/"+imageName
        imageUrl=self.config['PUB_URL']+"/"+relativePath+"/"+imageName

        # Check if the file already exists and it is valid
        if use_disk_cached is False or os.path.isfile(imagePath) is False or ( os.path.isfile(imagePath) is True and (time.time() - os.path.getmtime(imagePath)) > self.config['CACHE_TIMEOUT']):
                        
            # Get place data
            placeData = self.places.get_place_by_id(place,params)
           
            # Check if the place is valid
            if placeData is not None:

                # Get the domain and the indeces of the place
                domain_indeces=self.places.get_domain_and_indeces_by_product_and_place(prod, place)


                # Check if domain and indeces are correct
                if domain_indeces is not None:
                    
                    # Retrieve domain and indeces
                    (domain,Jmin,Jmax,Imin,Imax)=domain_indeces

                    minLon=placeData["minLon"]
                    minLat=placeData["minLat"]
                    maxLon=placeData["maxLon"]
                    maxLat=placeData["maxLat"]

                    cLon=(maxLon+minLon)/2.0
                    cLat=(maxLat+minLat)/2.0

                    coscLat=math.cos(cLat*0.0174533)

                    a=1.0*width/height
 
                    dLat=maxLat-minLat
                    dLon=maxLon-minLon

                    if width>height:
                        if dLon>dLat:
                            dLat2=a*(dLon*coscLat)/2
                            minLat=cLat-dLat2
                            maxLat=cLat+dLat2
                        else:
                            dLon2=a*dLat/2
                            minLon=cLon-dLon2
                            maxLon=cLon+dLon2
                    else:
                        if dLon>dLat:
                            dLon2=(1/a)*dLat/2
                            minLon=cLon-dLon2
                            maxLon=cLon+dLon2
                        else:
                            dLat2=(1/a)*(dLon*coscLat)/2
                            minLat=cLat-dLat2
                            maxLat=cLat+dLat2


                    bbox=str(minLon)+","+str(minLat)+","+str(maxLon)+","+str(maxLat)
                    imgBaseMap = Image.new('RGBA', (width, height))

                    for item in self.maps['base']:
                        url=item+"&width="+str(width)+"&height="+str(height)+"&bbox="+str(bbox)+"&"
                        url=url+"FORMAT=image/png&"
                        url=url+"TRANSPARENT=TRUE&"
                        url=url+"SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&SRS=EPSG:4326&"
                        response = requests.get(url, stream=True)

                        if response.ok:
                            data = requests.get(url).content
                            imgLayer = Image.open(io.BytesIO(data))
                            imgBaseMap.paste(imgLayer, (0, 0), imgLayer)

                    #noImage=False
                    # for theme in self.maps['themes'][prod][output]:

                    if prod in self.maps['products'] and output in self.maps['products'][prod]:
                        for theme in self.maps['products'][prod][output]:
                            url=self.config['WMS_URL']+"/lds/opendap/"+prod+"/"+domain+"/"+self.config['HISTORY']+"/"+dateTimePath+"/"+prod+"_"+domain+"_"+dateTime+".nc?"
                            for item in theme:
                                url=url+item+"="+theme[item]+"&"

                            url=url+"LAYERS=lds/opendap/"+prod+"/"+domain+"/"+self.config['HISTORY']+"/"+dateTimePath+"/"+prod+"_"+domain+"_"+dateTime+".nc/"+theme['LAYERS']+"&"
                            url=url+"FORMAT=image/png&"
                            url=url+"TRANSPARENT=TRUE&"
                            #url=url+"TIME=1970-01-01T00:00:00.000Z&"
                            url=url+"SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&SRS=EPSG:4326&"
                            url=url+"BBOX="+bbox+"&"
                            url=url+"WIDTH="+str(width)+"&HEIGHT="+str(height)


                            response = requests.get(url, stream=True)

                            if response.ok:
                                data = requests.get(url).content
                                imgLayer = Image.open(io.BytesIO(data))
                                imgBaseMap.paste(imgLayer, (0, 0), imgLayer)
                            else:
                                noImage=True
                                break

                    #if noImage is False:
                    if "NOOVRL" not in params['opt']:
                        for item in self.maps['overlay']:
                            try:
                                url=item+"&width="+str(width)+"&height="+str(height)+"&srs=EPSG:4326&bbox="+str(bbox)+"&"
                                url=url+"FORMAT=image/png&"
                                url=url+"TRANSPARENT=TRUE&"
                                url=url+"SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&SRS=EPSG:4326&"
                                response = requests.get(url, stream=True)

                                if response.ok:
                                    data = requests.get(url).content
                                    imgLayer = Image.open(io.BytesIO(data))
                                    imgBaseMap.paste(imgLayer, (0, 0), imgLayer)
                            except Exception as e :
                                logger.error("error : %s", e)
                                #log.error("error : " + str(e))


                    #### ####
                    draw = ImageDraw.Draw(imgBaseMap)
                    # use a bitmap font
                    draw.text((0, 0),dateTime)

                    #### Save image #####
                    imgBaseMap.save(imagePath)


            else:
                # The place is not available
                imagePath=self.config['NOIMAGE_PATH']
                imageUrl=self.config['NOIMAGE_URL']


        retval['link']=imageUrl
        if dry.lower() == "false":
            try:
                #with open(imagePath, 'r') as content_file:
                with open(imagePath, 'rb') as content_file:
                    retval = content_file.read()
            except Exception as e:
                imagePath=self.config['NOIMAGE_PATH']
                imageUrl=self.config['NOIMAGE_URL']
        

        return (retval,imageName)


    def MakeJsonAlt(self, prod, place, params=None): 
        """Implement make json alt for meteo services."""
        prod = prod
        place = place
        output = 'gen'
        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        day = now.strftime('%d')
        hour = '00'
        minute = '00'

        if params:
            if 'output' in params and params['output'] is not None:
                output = params['output']
            if "lang" in params and params['lang'] is not None:
                lang = params['lang']
            if "date" in params and params['date'] is not None:
                now = params['date']
                year = now[0:4]
                month = now[4:6]
                day = now[6:8]
                hour = now[9:11]
                minute = now[11:13]

        model_name = self.maps["products"][prod]["desc"][lang]
        output_name = self.maps["products"][prod]["outputs"][output]["title"][lang]
            
        out = self.maps["alt"][lang].replace("%H", hour).replace("%M",minute).replace("%d", day).replace("%m", month).replace("%Y", year).replace("__place__", place).replace("__model__", model_name).replace("__output__", output_name)

        return out


    ''' 
    # funzione aggiunta dalle vecchie API 
    def modelploturl_or_image(self, use_disk_cached=True, params = None):
        months=[ "jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
        retval = {}

        # places = self.Places(self.config)
        prod = self.default_prod
        output = self.default_output
        place = self.default_place
        width = self.default_xdim
        height = self.default_ydim

        timeref = None
        year=0
        month=0
        day=0
        hour=0
        minute=0

        bars='false'

        if params:
            if 'opt' in params and params['opt'] is not None:
                if "bars" in params['opt']:
                    bars='true'
            if 'width' in params and params['width'] is not None:
                width = int(params['width'])

            if 'height' in params and params['height'] is not None:
                height = int(params['height'])

            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'output' in params and params['output'] is not None:
                output = params['output']

            if 'place' in params and params['place'] is not None:
                place = params['place']

            if 'date' in params and params['date'] is not None:
                timeref = params['date']

        if timeref is None:
            #print "get current utc"
            date=datetime.utcnow()
            year=date.year
            month=date.month
            day=date.day
            hour=int(round(date.hour+date.minute/60.0))
            minute=0
        else:
            #print "Date is provided"
            year=int(timeref[:4])
            month=int(timeref[4:6])
            day=int(timeref[6:8])
            hour=int(timeref[9:11])
            if len(timeref)==13:
                minute=int(timeref[11:13])

        # Get dry
        dry = str(params['dry'])

        #print "hour:"+str(hour)
        #print "Place:"+str(place) 
        date=datetime(year, month, day, hour, minute)
        #print "date:"+str(date)

        # Get place data
        params1 = {'id':place,'filter':None, 'prod':prod}

        # Set the dateTime
        dateTime=format(date.year,'04')+format(date.month,'02')+format(date.day,'02')+"Z"+format(date.hour,'02')+format(date.minute,'02')
        dateTimePath=format(date.year,'04')+"/"+format(date.month,'02')+"/"+format(date.day,'02')

        imageName="plt_"+place+"_"+prod+"_"+dateTime+"_"+output+"_"+str(width)+"x"+str(height)+".png"
        relativePath="plt/"+place+"/"+prod+"/"+dateTimePath

        # Check if the directory exists
        if os.path.exists(self.config['BASE_PRODUCTS']+"/"+relativePath) is False:

            # Create the directory
            os.makedirs(self.config['BASE_PRODUCTS']+"/"+relativePath)
        
        
        imagePath=self.config['BASE_PRODUCTS']+"/"+relativePath+"/"+imageName
        imageUrl=self.config['PUB_URL']+"/"+relativePath+"/"+imageName

        # Check if the file already exists and it is valid
        if use_diskcached is False or os.path.isfile(imagePath) is False or ( os.path.isfile(imagePath) is True and (time.time()-os.path.getmtime(imagePath))>86400):

            #imagePath=self.cfg['NOIMAGE_PATH']
            # placeData = places.get_place_by_id(place,params)
            placeData = self.places.get_place_by_id(place,params)
            if placeData is not None:

                # Get the domain and the indeces of the place
                domain_indeces=self.places.get_domain_and_indeces_by_product_and_place(prod, place)


                # Check if domain and indeces are correct
                if domain_indeces is not None:

                    # Retrieve domain and indeces
                    (domain,Jmin,Jmax,Imin,Imax)=domain_indeces


                    minLon=placeData["minLon"]
                    minLat=placeData["minLat"]
                    maxLon=placeData["maxLon"]
                    maxLat=placeData["maxLat"]

                    # Set the local path of the data file
                    url=self.config['BASE_PATH']+"/"+prod+"/"+domain+"/"+self.config['HISTORY']+"/"+dateTimePath+"/"+prod+"_"+domain+"_"+dateTime+".nc"
                
                    dataset=None
                    try:
                        # Open the data file
                        dataset = netCDF4.Dataset(url)
                    except:
                        imagePath=self.config['NOIMAGE_PATH']
                        imageUrl=self.config['NOIMAGE_URL']

                    if dataset is not None:

                        controlFile="""
dset """+url+"""
dtype netcdf"""
                        if "rdr1" in prod or "rdr2" in prod:
                            XLONG=dataset.variables["lon"][::]
                            XLAT=dataset.variables["lat"][::]
                            south_north_dim=len(XLAT)
                            west_east_dim=len(XLONG[0])

                            (lon_min,lat_min,lon_max,lat_max,dxll,dyll)=self.calc_boundaries(west_east_dim,south_north_dim,XLONG,XLAT)

                            controlFile=controlFile+"""
undef -999000000
TITLE Weather Radar Output Grid: Time, bottom_top, south_north, west_east
xdef  """+str(west_east_dim)+""" linear   """+str(lon_min)+"""   """+str(dxll)+"""
ydef  """+str(south_north_dim)+""" linear   """+str(lat_min)+"""   """+str(dyll)+"""
zdef  30 linear 1 1
tdef   1 linear """+format(date.hour,'02')+""":"""+format(date.minute,'02')+"""Z"""+format(date.day,'02')+months[date.month-1]+format(date.year,'04')+""" 1hr
vars 3
reflectivity=>reflectivity  0  t,y,x  Reflectivity
rain=>rain                  0  t,y,x  Rain
mask=>mask                  0  y,x    Mask
endvars
"""
                            #print str(controlFile)

                        if "wcm3" in prod:
                            ipoints=len(dataset.dimensions['longitude'])
                            jpoints=len(dataset.dimensions['latitude'])
                            lon0=dataset.variables["longitude"][0]
                            lat0=dataset.variables["latitude"][0]
                            lon1=dataset.variables["longitude"][-1]
                            lat1=dataset.variables["latitude"][-1]

                            dxll=(lon1-lon0)/ipoints
                            dyll=(lat1-lat0)/jpoints

                            controlFile=controlFile+"""
undef 1.0e+37f
TITLE WACOMM Output Grid: Time, bottom_top, south_north, west_east
xdef """+str(ipoints)+""" linear  """+str(lon0)+"""   """+str(dxll)+"""
ydef """+str(jpoints)+""" linear  """+str(lat0)+"""   """+str(dyll)+"""
zdef  11 linear 1 1
tdef   1 linear """+format(date.hour,'02')+""":"""+format(date.minute,'02')+"""Z"""+format(date.day,'02')+months[date.month-1]+format(date.year,'04')+""" 1hr
vars 1
conc=>conc 11 t,z,y,x  Tracer concentration
endvars
"""
                            #print str(controlFile)
                        if "aiq3" in prod:
                            ipoints=len(dataset.dimensions['longitude'])
                            jpoints=len(dataset.dimensions['latitude'])
                            lon0=dataset.variables["longitude"][0]
                            lat0=dataset.variables["latitude"][0]
                            lon1=dataset.variables["longitude"][-1]
                            lat1=dataset.variables["latitude"][-1]

                            dxll=(lon1-lon0)/ipoints
                            dyll=(lat1-lat0)/jpoints

                            controlFile=controlFile+"""
undef 1.0e+37f
TITLE AIQUAM Output Grid: Time, bottom_top, south_north, west_east
xdef """+str(ipoints)+""" linear  """+str(lon0)+"""   """+str(dxll)+"""
ydef """+str(jpoints)+""" linear  """+str(lat0)+"""   """+str(dyll)+"""
zdef  11 linear 1 1
tdef   1 linear """+format(date.hour,'02')+""":"""+format(date.minute,'02')+"""Z"""+format(date.day,'02')+months[date.month-1]+format(date.year,'04')+""" 1hr
vars 1
class_predict=>class_predict 0 t,y,x  Predicted class
endvars
"""
                            #print str(controlFile)
                        if "rms3" in prod:

                            ipoints=len(dataset.dimensions['longitude'])
                            jpoints=len(dataset.dimensions['latitude'])
                            lon0=dataset.variables["longitude"][0]
                            lat0=dataset.variables["latitude"][0]
                            lon1=dataset.variables["longitude"][-1]
                            lat1=dataset.variables["latitude"][-1]

                            dxll=(lon1-lon0)/ipoints
                            dyll=(lat1-lat0)/jpoints

                            controlFile=controlFile+"""
undef 1.e+37
TITLE ROMS Output Grid: Time, bottom_top, south_north, west_east
xdef """+str(ipoints)+""" linear  """+str(lon0)+"""   """+str(dxll)+"""
ydef """+str(jpoints)+""" linear  """+str(lat0)+"""   """+str(dyll)+"""
zdef  11 linear 1 1
tdef   1 linear """+format(date.hour,'02')+""":"""+format(date.minute,'02')+"""Z"""+format(date.day,'02')+months[date.month-1]+format(date.year,'04')+""" 1hr
vars 7
zeta=>zeta  0  t,y,x   free-surface
u=>u       11  t,z,y,x u-momentum component
v=>v       11  t,z,y,x v-momentum component
ubar=>ubar  0  t,y,x   vertically integrated u-momentum component
vbar=>vbar  0  t,y,x   vertically integrated v-momentum component
salt=>salt 11  t,z,y,x salinity
temp=>temp 11  t,z,y,x potential temperature
endvars
"""
                            #print str(controlFile)
                        if "ww33" in prod:

                            ipoints=len(dataset.dimensions['longitude'])
                            jpoints=len(dataset.dimensions['latitude'])
                            lon0=dataset.variables["longitude"][0]
                            lat0=dataset.variables["latitude"][0]
                            lon1=dataset.variables["longitude"][-1]
                            lat1=dataset.variables["latitude"][-1]

                            dxll=(lon1-lon0)/ipoints
                            dyll=(lat1-lat0)/jpoints

                            controlFile=controlFile+"""
undef 1.e+37
TITLE WWatch3 Output Grid: Time, bottom_top, south_north, west_east
xdef """+str(ipoints)+""" linear  """+str(lon0)+"""   """+str(dxll)+"""
ydef """+str(jpoints)+""" linear  """+str(lat0)+"""   """+str(dyll)+"""
zdef   1 linear 1 1
tdef   1 linear """+format(date.hour,'02')+""":"""+format(date.minute,'02')+"""Z"""+format(date.day,'02')+months[date.month-1]+format(date.year,'04')+""" 1hr
vars 5
hs=>hs  0  t,y,x   Significant wave height
lm=>lm  0  t,y,x   Wave length
fp=>fp  0  t,y,x   Peak frequency
dir=>dir  0  t,y,x  Wave direction
period=>period  0  t,y,x  Wave period
endvars
"""
                            #print str(controlFile)

                        if "wrf5" in prod:
                            ipoints=len(dataset.dimensions['longitude'])
                            jpoints=len(dataset.dimensions['latitude'])
                            lon0=dataset.variables["longitude"][0] 
                            lat0=dataset.variables["latitude"][0]
                            lon1=dataset.variables["longitude"][-1]    
                            lat1=dataset.variables["latitude"][-1]
                            dxll=(lon1-lon0)/ipoints
                            dyll=(lat1-lat0)/jpoints
                            controlFile=controlFile+"""
undef 1.e30
title  OUTPUT FROM WRF V3.9.1 MODEL
xdef """+str(ipoints)+""" linear  """+str(lon0)+"""   """+str(dxll)+"""
ydef """+str(jpoints)+""" linear  """+str(lat0)+"""   """+str(dyll)+"""
zdef  27 linear 1 1
tdef   1 linear """+format(date.hour,'02')+""":"""+format(date.minute,'02')+"""Z"""+format(date.day,'02')+months[date.month-1]+format(date.year,'04')+""" 1hr
vars 48
U10M=>u10m               0  t,y,x    wind u component at 10m
V10M=>v10m               0  t,y,x    wind v component at 10m
WSPD10=>ws10             0  t,y,x    wind speed at 10m
WDIR10=>wd10             0  t,y,x    wind direction at 10m
DELTA_WSPD10=>delta_ws10 0  t,y,x    difference of wind speed at 10m
DELTA_WDIR10=>delta_wd10 0  t,y,x    difference of wind direction at 10m
CLDFRA_TOTAL=>clf_total  0  t,y,x    total cloud fraction
SLP=>slp                 0  t,y,x    pressure at sea level
UH=>uh                   0  t,y,x    updraft helicity
RH2=>rh2                 0  t,y,x    relative humidity at 2m
T2C=>t2c                 0  t,y,x    temperature at 2m
DELTA_RAIN=>delta_rain   0  t,y,x    hourly cumulated rain mm
GPH500=>gph500           0  t,y,x    geopotential height at 500 hPa
GPH850=>gph850           0  t,y,x    geopotential height at 850 hPa
HOURLY_SWE=>hourly_swe   0  t,y,x    equivalent snow water kg m-2
DAILY_RAIN=>daily_rain   0  t,y,x    daily cumulated rain mm
U300=>u300               0  t,y,x    wind u component at 300 Hpa
V300=>v300               0  t,y,x    wind v component at 300 Hpa
RH300=>rh300             0  t,y,x    relative humidity at 300 Hpa
TC300=>tc300             0  t,y,x    temperature in celsius at 300 Hpa
U500=>u500               0  t,y,x    wind u component at 500 Hpa
V500=>v500               0  t,y,x    wind v component at 500 Hpa
RH500=>rh500             0  t,y,x    relative humidity at 500 Hpa
TC500=>tc500             0  t,y,x    temperature in celsius at 500 Hpa
U700=>u700               0  t,y,x    wind u component at 700 Hpa
V700=>v700               0  t,y,x    wind v component at 700 Hpa
RH700=>rh700             0  t,y,x    relative humidity at 700 Hpa
TC700=>tc700             0  t,y,x    temperature in celsius at 700 Hpa
U850=>u850               0  t,y,x    wind u component at 850 Hpa
V850=>v850               0  t,y,x    wind v component at 850 Hpa
RH850=>rh850             0  t,y,x    relative humidity at 850 Hpa
TC850=>tc850             0  t,y,x    temperature in celsius at 850 Hpa
U925=>u925               0  t,y,x    wind u component at 925 Hpa
V925=>v925               0  t,y,x    wind v component at 925 Hpa
RH925=>rh925             0  t,y,x    relative humidity at 925 Hpa
TC925=>tc925             0  t,y,x    temperature in celsius at 925 Hpa
U950=>u950               0  t,y,x    wind u component at 950 Hpa
V950=>v950               0  t,y,x    wind v component at 950 Hpa
RH950=>rh950             0  t,y,x    relative humidity at 950 Hpa
TC950=>tc950             0  t,y,x    temperature in celsius at 950 Hpa
U975=>u975               0  t,y,x    wind u component at 975 Hpa
V975=>v975               0  t,y,x    wind v component at 975 Hpa
RH975=>rh975             0  t,y,x    relative humidity at 975 Hpa
TC975=>tc975             0  t,y,x    temperature in celsius at 975 Hpa
U1000=>u1000             0  t,y,x    wind u component at 1000 Hpa
V1000=>v1000             0  t,y,x    wind v component at 1000 Hpa
RH1000=>rh1000           0  t,y,x    relative humidity at 1000 Hpa
TC1000=>tc1000           0  t,y,x    temperature in celsius at 1000 Hpa
endvars
"""
                        dataset.close()
                        tempdir="/tmp/grads_"+prod+"_"+str(uuid.uuid4())
                        os.makedirs(tempdir)

                        controlFileName=tempdir+"/controlfile.ctl"

                        file = open(controlFileName,"w") 
                        file.write(controlFile)
                        file.close() 
                        
                        //script=self.config['GRADS_SCRIPT']

                        # environment="/home/ccmmma/prometeo/opt/ccmmmaapi/sourceme-grads-2.2.1"
                        # label=placeData["long_name"]["it"]
                        # command='grads -lbc "'+script+" "+controlFileName+" "+str(minLon)+" "+str(minLat)+" "+str(maxLon)+" "+str(maxLat)+" "+place+" "+domain+" "+prod+" "+output+" "+str(width)+" "+str(height)+" "+imagePath+" "+tempdir+" "+bars+" "+label+'"'
                        # os.system(". "+environment+";"+command)
                        #shutil.rmtree(tempdir)
                        


            else:
                # The place is not available
                imagePath=self.config['NOIMAGE_PATH']
                imageUrl=self.config['NOIMAGE_URL']

        retval['link']=imageUrl
        if dry.lower() == "false":
            try:
                with open(imagePath, 'r') as content_file:
                    retval = content_file.read()
            except:
                imagePath=self.config['NOIMAGE_PATH']
                imageUrl=self.config['NOIMAGE_URL']

        return (retval,imageName)
        '''
    
