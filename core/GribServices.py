import simplejson
import time
from datetime import timedelta, date, datetime
import os
import os.path
# import ConfigParser
import os
import netCDF4
from netCDF4 import Dataset
from wrf import getvar, ALL_TIMES, get_basemap, latlon_coords, geo_bounds, to_np, get_cartopy, destagger, ll_to_xy
import numpy as np
from scipy.interpolate import griddata
from core.Logger import logger

class GribServices:
    default_domain = 'd01'
    default_prod = 'wrf5'
    config = {}
    path = ""

    __statusCode = {'200': {'code': '200', 'msg': 'OK'}, '205': {'code': '205', 'msg': 'No Content'},
                    '231': {'code': '231', 'msg': 'Info Not Available'}, '400': {'code': '400', 'msg': 'Bad Request'},
                    '401': {'code': '401', 'msg': 'Unauthorized'}, '404': {'code': '404', 'msg': 'Not Found'}}

    def __init__(self, config):
        self.config = config
        self.products = None
        self.maps = None
        with open(self.config["MAPS"]) as f:
            self.maps = simplejson.load(f)
        self.products = self.maps["products"]

    def getStatusCode(self, code):
        return self.__statusCode[code]

    def asText(self, params=None):
        retval = ""

        prod = self.default_prod
        domain = self.default_domain

        timeref = None
        year = 0
        month = 0
        day = 0
        hour = 0
        minute = 0

        if params:
            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'domain' in params and params['domain'] is not None:
                domain = params['domain']

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

        date = datetime(year, month, day, hour, minute)

        data_ora = format(date.year, '04') + "-" + format(date.month, '02') + "-" + format(date.day,'02') + " " + format(date.hour, '02') + ":" + format(date.minute, '02') + ":00"

        # Set the dateTime
        dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + format(date.minute, '02')
        dateTimePath = format(date.year, '04') + "/" + format(date.month, '02') + "/" + format(date.day, '02')

        csvName = domain + "_" + prod + "_" + dateTime + ".csv"
        relativePath = "csv/" + domain + "/" + prod + "/" + dateTimePath

        try:
            os.makedirs(self.config['BASE_PRODUCTS'] + "/" + relativePath)
        except Exception as e:
            logger.error(str(e))
            pass

        csvPath = self.config['BASE_PRODUCTS'] + "/" + relativePath + "/" + csvName
        csvUrl = self.config['PUB_URL'] + "/" + relativePath + "/" + csvName

        # Check if the file already exists and it is valid
        if os.path.isfile(csvPath) is False or (os.path.isfile(csvPath) is True and (time.time() - os.path.getmtime(csvPath)) > self.config['CACHE_TIMEOUT']):
            # Set the local path of the data file
            # url = self.cfg['BASE_PATH'] + "/" + prod + "/" + domain + "/archive/" + dateTimePath + "/" + prod + "_" + domain + "_" + dateTime + ".nc"
            url = self.config['BASE_PATH'] + prod + "/" + domain + "/archive/" + dateTimePath + "/" + prod + "_" + domain + "_" + dateTime + ".nc"
            # print(url)
            ncfile = None
            try:
                # Open the data file
                ncfile = netCDF4.Dataset(url)
            except Exception as e:
                logger.error(str(e))
                pass

            if ncfile is not None:
                lines = []
                if "wrf5" in prod:
                    T2C = ncfile.variables["T2C"][0][:]
                    SLP = ncfile.variables["SLP"][0][:]
                    RH2 = ncfile.variables["RH2"][0][:]
                    DELTA_RAIN = ncfile.variables["DELTA_RAIN"][0][:]
                    UH = ncfile.variables["UH"][0][:]
                    MCAPE = ncfile.variables["MCAPE"][0][:]
                    TC500 = ncfile.variables["TC500"][0][:]
                    TC850 = ncfile.variables["TC850"][0][:]
                    GPH500 = ncfile.variables["GPH500"][0][:]
                    GPH850 = ncfile.variables["GPH850"][0][:]
                    WSPD10 = ncfile.variables["WSPD10"][0][:]
                    WDIR10 = ncfile.variables["WDIR10"][0][:]
                    DELTA_WSPD10 = ncfile.variables["DELTA_WSPD10"][0][:]
                    DELTA_WDIR10 = ncfile.variables["DELTA_WDIR10"][0][:]
                    CLDFRA_TOTAL = ncfile.variables["CLDFRA_TOTAL"][0][:]
                    U10M = ncfile.variables["U10M"][0][:]
                    V10M = ncfile.variables["V10M"][0][:]

                    lines.append("j;i;T2C;SLP;WSPD10;WDIR10;RH2;UH;MCAPE;TC500;TC850;GPH500;GPH850;CLDFRA_TOTAL;U10M;V10M;DELTA_WSPD10;DELTA_WDIR10;DELTA_RAIN")

                    nLats = len(T2C)
                    nLons = len(T2C[0])

                    for j in range(nLats):
                        for i in range(nLons):
                            line = str(j) + ";" + str(i) + ";"
                            # print line
                            line = line + str(T2C[j][i]) + ";" + str(SLP[j][i]) + ";" + str(WSPD10[j][i]) + ";" + str(
                                WDIR10[j][i]) + ";" + str(RH2[j][i]) + ";" + str(UH[j][i]) + ";" + str(
                                MCAPE[j][i]) + ";" + str(TC500[j][i]) + ";" + str(TC850[j][i]) + ";" + str(
                                GPH500[j][i]) + ";" + str(GPH850[j][i]) + ";" + str(CLDFRA_TOTAL[j][i]) + ";" + str(
                                U10M[j][i]) + ";" + str(V10M[j][i]) + ";" + str(DELTA_WSPD10[j][i]) + ";" + str(
                                DELTA_WDIR10[j][i]) + ";" + str(DELTA_RAIN[j][i])
                            lines.append(line.replace("--", "?").replace("nan", "?"))

                with open(csvPath, 'w') as f:
                    for line in lines:
                        f.write(line + "\n")
                    f.close()

        try:
            with open(csvPath, 'r') as content_file:
                retval = content_file.read()
        except Exception as e:
            logger.error(str(e))
            pass

        return retval

    def asJson(self, params=None):
        
        # logger.error(f"AsJson : {params}")
    
        retval = {}

        prod = self.default_prod
        domain = self.default_domain

        timeref = None
        year = 0
        month = 0
        day = 0
        hour = 0
        minute = 0

        if params:
            if 'prod' in params and params['prod'] is not None:
                prod = params['prod']

            if 'domain' in params and params['domain'] is not None:
                domain = params['domain']

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

        data_ora = format(date.year, '04') + "-" + format(date.month, '02') + "-" + format(date.day, '02') + " " + format(date.hour, '02') + ":" + format(date.minute, '02') + ":00"

        # Set the dateTime
        dateTime = format(date.year, '04') + format(date.month, '02') + format(date.day, '02') + "Z" + format(date.hour, '02') + format(date.minute, '02')
        dateTimePath = format(date.year, '04') + "/" + format(date.month, '02') + "/" + format(date.day, '02')

        jsonName = domain + "_" + prod + "_" + dateTime + ".json"
        relativePath = "jsn/" + domain + "/" + prod + "/" + dateTimePath

        if os.path.exists(self.config['BASE_PRODUCTS'] + "/" + relativePath) is False:
            try:
                os.makedirs(self.config['BASE_PRODUCTS'] + "/" + relativePath)
            except Exception as e:
                logger.error(str(e))
                pass

        jsonPath = self.config['BASE_PRODUCTS'] + "/" + relativePath + "/" + jsonName
        jsonUrl = self.config['PUB_URL'] + "/" + relativePath + "/" + jsonName

        # Check if the file already exists and it is valid
        if os.path.isfile(jsonPath) is False or (os.path.isfile(jsonPath) is True and (time.time() - os.path.getmtime(jsonPath)) > self.config['CACHE_TIMEOUT']):
            
            # Set the local path of the data file 
            # url =  self.config['BASE_STORAGE_PATH'] + prod + "/" + domain + "/history/" + dateTimePath + "/" + prod + "_" + domain + "_" + dateTime + ".nc"
            
            url = self.config['BASE_PATH'] + prod + "/" + domain + "/history/" + dateTimePath + "/" + prod + "_" + domain + "_" + dateTime + ".nc"

            logger.info("url_data : " + str(url))
            
            ncfile = None
            try:
                # Open the data file
                ncfile = netCDF4.Dataset(url)
            except Exception as e:
                logger.error(str(e))
                pass

            if ncfile is not None:
                result = {}
                if "wrf5" in prod:

                    Xlat = getvar(ncfile, "XLAT", timeidx=ALL_TIMES)
                    Xlon = getvar(ncfile, "XLONG", timeidx=ALL_TIMES)

                    row_lat = len(Xlat) - 1
                    col_lat = len(Xlat[0]) - 1

                    row_long = len(Xlon) - 1
                    col_long = len(Xlon[0]) - 1

                    A = [Xlat[0][0], Xlon[0][0]]
                    B = [Xlat[0][col_lat], Xlon[0][col_long]]
                    C = [Xlat[row_lat][col_lat], Xlon[row_long][col_long]]
                    D = [Xlat[row_lat][0], Xlon[row_long][0]]

                    min_lat = Xlat[0][0]
                    minI = 0

                    Xlat[0][0] - Xlat[1][1]
                    Xlon[0][0] - Xlon[1][1]

                    ''' from A to B '''
                    for i in range(col_lat, -1, -1):
                        np1 = [Xlat[0][i], Xlon[0][i]]
                        if np1[0] > min_lat:
                            minI = i
                            min_lat = np1[0]

                    max_lat = Xlat[row_lat][col_lat]
                    maxI = col_lat

                    ''' from C to D '''
                    for i in range(col_lat, -1, -1):
                        np1 = [Xlat[row_lat][i], Xlon[row_long][i]]
                        if np1[0] < max_lat:
                            maxI = i
                            max_lat = np1[0]

                    min_long = Xlon[0][0]
                    minJ = 0

                    ''' from A to D '''
                    for i in range(row_lat, -1, -1):
                        np1 = [Xlat[i][0], Xlon[i][0]]
                        if np1[1] > min_long:
                            minJ = i
                            min_long = np1[1]

                    max_long = Xlon[0][col_long]
                    maxJ = row_lat

                    ''' from B to C '''
                    for i in range(row_lat, -1, -1):
                        np1 = [Xlat[i][col_lat], Xlon[i][col_lat]]
                        if np1[1] < max_long:
                            maxJ = i
                            max_long = np1[1]

                    minLat = min_lat.item()
                    maxLat = max_lat.item()
                    minLon = min_long.item()
                    maxLon = max_long.item()

                    minimo = ll_to_xy(ncfile, minLat, minLon, timeidx=0, squeeze=True, meta=True, stagger=None, as_int=True)
                    massimo = ll_to_xy(ncfile, maxLat, maxLon, timeidx=0, squeeze=True, meta=True, stagger=None, as_int=True)

                    py = np.array(Xlat).flatten()
                    px = np.array(Xlon).flatten()

                    uvmet10 = getvar(ncfile, "uvmet10", meta=True)
                    z = np.array(uvmet10[0]).flatten()

                    xi = np.linspace(minLon, maxLon, len(uvmet10[0][0]))

                    dLon = [j - i for i, j in zip(xi[:-1], xi[1:])]

                    temp = 0
                    somma = 0

                    count = len(xi)

                    for i, j in zip(xi[:-1], xi[1:]):
                        temp = j - i
                        somma = somma + temp

                    dLon = somma / count

                    yi = np.linspace(minLat, maxLat, len(uvmet10[0]))

                    temp = 0
                    somma = 0

                    count = len(yi)

                    for i, j in zip(yi[:-1], yi[1:]):
                        temp = j - i
                        somma = somma + temp

                    dLat = somma / count

                    X, Y = np.meshgrid(xi, yi)

                    U10i = griddata((px, py), z, (X, Y), method='cubic')

                    xi = np.linspace(minLon, maxLon, len(uvmet10[1][0]))
                    yi = np.linspace(minLat, maxLat, len(uvmet10[1]))
                    X, Y = np.meshgrid(xi, yi)

                    z = np.array(uvmet10[1]).flatten()

                    V10i = griddata((px, py), z, (X, Y), method='cubic')

                    nrows = len(U10i)
                    ncols = len(U10i[0])

                    result = [{
                        "header": {
                            "parameterUnit": "m.s-1",
                            "parameterNumber": 2,
                            "dx": dLon,
                            "dy": dLat,
                            "parameterNumberName": "U-component_of_wind",
                            "la1": maxLat,
                            "la2": minLat,
                            "parameterCategory": 2,
                            "lo2": maxLon,
                            "nx": ncols,
                            "ny": nrows,
                            "refTime": data_ora,
                            "lo1": minLon
                        },
                        "data": []
                    }, {
                        "header": {
                            "parameterUnit": "m.s-1",
                            "parameterNumber": 3,
                            "dx": dLon,
                            "dy": dLat,
                            "parameterNumberName": "V-component_of_wind",
                            "la1": maxLat,
                            "la2": minLat,
                            "parameterCategory": 2,
                            "lo2": maxLon,
                            "nx": ncols,
                            "ny": nrows,
                            "refTime": data_ora,
                            "lo1": minLon
                        },
                        "data": []
                    }
                    ]

                N = len(U10i) - 1
                for i in range(N, -1, -1):
                    for j in range(len(U10i[i])):
                        result[0]["data"].append(round(U10i[i][j], 1))

                M = len(V10i) - 1
                for i in range(M, -1, -1):
                    for j in range(len(V10i[i])):
                        result[1]["data"].append(round(V10i[i][j], 1))

                with open(jsonPath, 'w') as f:
                    simplejson.dump(result, f)
                    f.close()

        try:
            with open(jsonPath, 'r') as content_file:
                retval = content_file.read()
        except:
            pass

        return simplejson.loads(retval)


# if __name__ == "__main__":
#     fname = "../etc/ccmmmaapi.development.conf";
#     config = {}
#    with open(fname) as f:
#        content = f.readlines()
#        for line in content:
#            line = line.replace("\n", "").replace("\r", "")
#            if line == "" or line.startswith('#') or not " = " in line:
#                continue
#
#            parts = line.split(" = ")
#
#            if '"' in parts[1][0] and '"' in parts[1][-1:]:
#                config[parts[0]] = parts[1].replace('"', '')
#            else:
#                if '.' in parts[1]:
#                    config[parts[0]] = float(parts[1])
#                else:
#                    config[parts[0]] = int(parts[1])


#    print(str(config))
#
#    gs = GribServices(config)
#    params = {'domain': 'd01', 'prod': 'wrf5', 'date': '20181029Z0000'}
#
#    output = gs.asText(params)
#    print(str(output))
