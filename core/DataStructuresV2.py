

# -------------------------------- BASE MAPS ------------------------------------------------

baseMaps = {
    "navionicsMarine": {
        "name": {
            "it-IT": "Navionics Marine Chart",
            "en-US": "Navionics Marine Chart"
        },
        "type": "navionics",
        "extras": {
            "navKey": 'Navionics_webapi_00480',
            "chartType": "JNC.NAVIONICS_CHARTS.NAUTICAL",
            "isTransparent": False,
            "logoPayoff": True,
            "zIndex": 1
        }
    },
    "navionicsSonar": {
        "name": {
            "it-IT": "Navionics Marine Sonar",
            "en-US": "Navionics Marine Sonar"
        },
        "type": "navionics",
        "extras": {
            "navKey": 'Navionics_webapi_00480',
            "chartType": 'JNC.NAVIONICS_CHARTS.SONARCHART',
            "isTransparent": False,
            "zIndex": 1
        }
    },
    "navionicsSky": {
        "name": {
            "it-IT": "Navionics Ski Chart",
            "en-US": "Navionics Ski Chart"
        },
        "type": "navionics",
        "extras": {
            "navKey": 'Navionics_webapi_00480',
            "chartType": 'JNC.NAVIONICS_CHARTS.SKI',
            "isTransparent": False,
            "zIndex": 1
        }
    },
    "satellite": {
        "name": {
            "it-IT": "Satellite",
            "en-US": "Satellite"
        },
        "type": "tiled",
        "url": 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        "extras": {
            "attribution": 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        }
    },
    "darkGray": {
        "name": {
            "it-IT": "Toni scuri",
            "en-US": "Dark Gray"
        },
        "type": "tiled",
        "url": "http://{s}.sm.mapstack.stamen.com/(toner-lite,$fff[difference],$fff[@23],$fff[hsl-saturation@20])/{z}/{x}/{y}.png",
        "extras": {
            "attribution": 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), and the GIS User Community'
        }
    },
    "osm": {
        "name": {
            "it-IT": "Open Street Map",
            "en-US": "Open Street Map"
        },
        "type": "tiled",
        "url": 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        "extras": {
            "attribution": '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }
    }
}

# ------------------------------ LAYERS ---------------------------

layers = {
    "info": {
        "name": {
            "it-IT": "Info",
            "en-US": "Info"
        },
        "type": "icon",
        "url": 'https://api.meteo.uniparthenope.it/apps/owm/wrf5/{prefix}/{z}/{x}/{y}.geojson?date={ncepDate}',
        "style": {
            "clickable": "true",
            "color": "#00D",
            "fillColor": "#00D",
            "weight": "1.0",
            "opacity": "0.3",
            "fillOpacity": 0.2
        },
        "extras": {
            "popup": [
                {"name": {"it-IT": "Nazione", "en-US": "Country"}, "property": "country"},
                {"name": {"it-IT": "Citt&agrave;", "en-US": "City"}, "property": "name"},
                {"name": {"it-IT": "Nvolosit&agrave;", "en-US": "Clouds"}, "property": "clf", "eval": "parseInt(clf * 100);",
                 "unit": "%"},
                {"name": {"it-IT": "Data", "en-US": "Date"}, "property": "dateTime"},
                {"name": {"it-IT": "Umidit&agrave;", "en-US": "Umidity"}, "property": "rh2", "unit": "%"},
                {"name": {"it-IT": "Pressione", "en-US": "Pressure"}, "property": "slp", "unit": "hPa"},
                {"name": {"it-IT": "Temperatura", "en-US": "Temp"}, "property": "t2c", "unit": "&deg;C"},
                {"name": {"it-IT": "Cielo", "en-US": "Sky"}, "property": "text", "eval": "text.it"},
                {"name": {"it-IT": "Direzione del vento", "en-US": "Wind direction"}, "property": "wd10", "unit": "&deg;N"},
                {"name": {"it-IT": "Velocit&agrave del vento", "en-US": "Wind Speed"}, "property": "ws10", "unit": "m/s"},
                {"name": {"it-IT": "Temperatura percepita", "en-US": "Wind Chill"}, "property": "wchill", "unit": "&deg;C"},
                {"name": {"it-IT": "Vento", "en-US": "winds"}, "property": "winds"},
                {"name": {"it-IT": "Dettagli", "en-US": "Details"}, "property": "link",
                 "link": "https://meteo.uniparthenope.it/forecast/forecast?"},
            ],
            "icons": {
                "sunny_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/sunny_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy1_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy1_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy2_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy2_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy3_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy3_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy4_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy4_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy5_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy5_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "shower1_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/shower1_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "shower2_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/shower2_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "shower3_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/shower3_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "sunny.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/sunny.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy1.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy1.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy2.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy2.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy3.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy3.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy4.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy4.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy5.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy5.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "shower1.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/shower1.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "shower2.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/shower2.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "shower3.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/shower3.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },

            }
        }
    },
    "universiade2019": {
        "name": {
            "it-IT": "Universiadi 2019",
            "en-US": "Universiade 2019"
        },
        "type": "icon",
        "url": 'https://api.meteo.uniparthenope.it/apps/owm/wrf5/UNI19/{z}/{x}/{y}.geojson?date={ncepDate}',
        "style": {
            "clickable": "true",
            "color": "#00D",
            "fillColor": "#00D",
            "weight": "1.0",
            "opacity": "0.3",
            "fillOpacity": 0.2
        },
        "extras": {
            "popup": [
                {"name": {"it-IT": "Nazione", "en-US": "Country"}, "property": "country"},
                {"name": {"it-IT": "Sito", "en-US": "Venue"}, "property": "name"},
                {"name": {"it-IT": "Nuolosit&agrave;", "en-US": "Clouds"}, "property": "clf", "eval": "parseInt(clf * 100);",
                 "unit": "%"},
                {"name": {"it-IT": "Data", "en-US": "Date"}, "property": "dateTime"},
                {"name": {"it-IT": "Umidit&agrave;", "en-US": "Umidity"}, "property": "rh2", "unit": "%"},
                {"name": {"it-IT": "Pressione", "en-US": "Pressure"}, "property": "slp", "unit": "hPa"},
                {"name": {"it-IT": "Temperatura", "en-US": "Temp"}, "property": "t2c", "unit": "&deg;C"},
                {"name": {"it-IT": "Cielo", "en-US": "Sky"}, "property": "text", "eval": "text['it']"},
                {"name": {"it-IT": "Direzione del vento", "en-US": "Wind direction"}, "property": "wd10", "unit": "&deg;N"},
                {"name": {"it-IT": "Velocit&agrave del vento", "en-US": "Wind Speed"}, "property": "ws10", "unit": "m/s"},
                {"name": {"it-IT": "Temperatura percepita", "en-US": "Wind Chill"}, "property": "wchill", "unit": "&deg;C"},
                {"name": {"it-IT": "Vento", "en-US": "winds"}, "property": "winds"},
                {"name": {"it-IT": "Dettagli", "en-US": "Details"}, "property": "link",
                 "link": "https://meteo.uniparthenope.it/forecast/forecast?"},
            ],
            "icons": {
                "sunny_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/sunny_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "shower1_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/shower1_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy2_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy2_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "shower2_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/shower2_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy1_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy1_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy1_night.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy1_night.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "sunny.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/sunny.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy1.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy1.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy2.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy2.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy3.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy3.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy4.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy4.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "cloudy5.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/cloudy5.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "shower1.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/shower1.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "shower2.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/shower2.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },
                "shower3.png": {
                    "url": "http://meteo.uniparthenope.it/sites/all/themes/zircon_custom/js/images/shower3.png",
                    "iconSize": [50, 50],
                    "iconAnchor": [9, 21],
                    "popupAnchor": [20, -17]
                },

            }
        }
    },
    "wind": {
        "name": {
            "it-IT": "Vento",
            "en-US": "Wind"
        },
        "type": "velocity",
        "url": "https://api.meteo.uniparthenope.it/products/wrf5/forecast/{domain}/grib/json?date={ncepDate}",
        "extras": {
            "displayValues": True,
            "displayOptions": {
                "velocityType": 'Wind 10m',
                "position": 'bottomleft',
                "displayPosition": 'bottomleft',
                "displayEmptyString": 'No wind data',
                "angleConvention": 'meteoCW',
                "speedUnit": 'kt'
            },
            "minVelocity": 0,
            "maxVelocity": 25.72,
            "velocityScale": 0.005,
            "colorScale": [
                "#000033", "#0117BA", "#011FF3", "#0533FC", "#1957FF", "#3B8BF4",
                "#4FC6F8", "#68F5E7", "#77FEC6", "#92FB9E", "#A8FE7D", "#CAFE5A",
                "#EDFD4D", "#F5D03A", "#EFA939", "#FA732E", "#E75326", "#EE3021",
                "#BB2018", "#7A1610", "#641610"]
        }
    },
    "slp": {
        "name": {
            "it-IT": "Pressione",
            "en-US": "Pressure"
        },
        "type": "wms",
        "url": 'https://api.meteo.uniparthenope.it/ncWMS2/wms/lds/cache/wrf5/{domain}/archive/{year}/{month}/{day}/wrf5_{domain}_{ncepDate}.nc',
        "extras": {
            "LAYERS": "SLP",
            "COLORSCALERANGE": "960,1040",
            "NUMCOLORBANDS": "250",
            "ABOVEMAXCOLOR": "extend",
            "BELOWMINCOLOR": "extend",
            "BGCOLOR": "extend",
            "LOGSCALE": "false",
            "STYLES": "contours"
        }
    },
    "cloud": {
        "name": {
            "it-IT": "Nuvolosit&agrave;",
            "en-US": "Cloud"
        },
        "type": "wms",
        "url": 'https://api.meteo.uniparthenope.it/ncWMS2/wms/lds/wrf5/{domain}/archive/{year}/{month}/{day}/wrf5_{domain}_{ncepDate}.nc',
        "extras": {

            "layers": 'CLDFRA_TOTAL',
            "styles": 'raster/wrf5_cldfrc',
            "format": 'image/png',
            "transparent": True,
            "opacity": 0.8,
            "COLORSCALERANGE": "0.125,1",
            "NUMCOLORBANDS": "250",
            "ABOVEMAXCOLOR": "extend",
            "BELOWMINCOLOR": "transparent",
            "BGCOLOR": "extend",
            "LOGSCALE": "false"
        }
    },
    "t2c": {
        "name": {
            "it-IT": "Temperatura a 2m",
            "en-US": "Temperature at 2m"
        },
        "type": "wms",
        "url": 'https://api.meteo.uniparthenope.it/ncWMS2/wms/lds/cache/wrf5/{domain}/archive/{year}/{month}/{day}/wrf5_{domain}_{ncepDate}.nc',
        "extras": {
            "layers": 'T2C',
            "styles": 'raster/wrf5_t2c_lamma',
            "format": 'image/png',
            "transparent": True,
            "opacity": 0.8,
            "COLORSCALERANGE": "-40,50",
            "NUMCOLORBANDS": "19",
            "ABOVEMAXCOLOR": "extend",
            "BELOWMINCOLOR": "extend",
            "BGCOLOR": "extend",
            "LOGSCALE": "false"
        }
    },
    "rain": {
        "name": {
            "it-IT": "Pioggia",
            "en-US": "Rain"
        },
        "type": "wms",
        "url": 'https://api.meteo.uniparthenope.it/ncWMS2/wms/lds/cache/wrf5/{domain}/archive/{year}/{month}/{day}/wrf5_{domain}_{ncepDate}.nc',
        "extras": {
            "layers": 'DELTA_RAIN',
            "styles": 'raster/wrf5_rain_lamma',
            "format": 'image/png',
            "transparent": True,
            "opacity": 0.8,
            "COLORSCALERANGE": ".2,60",
            "NUMCOLORBANDS": "15",
            "ABOVEMAXCOLOR": "extend",
            "BELOWMINCOLOR": "transparent",
            "BGCOLOR": "extend",
            "LOGSCALE": "false"
        }
    },
    "snow": {
        "name": {
            "it-IT": "Neve",
            "en-US": "Snow"
        },
        "type": "wms",
        "url": 'https://api.meteo.uniparthenope.it/ncWMS2/wms/lds/cache/wrf5/{domain}/archive/{year}/{month}/{day}/wrf5_{domain}_{ncepDate}.nc',
        "extras": {
            "layers": 'HOURLY_SWE',
            "styles": 'raster/wrf5_snow',
            "format": 'image/png',
            "transparent": True,
            "opacity": 0.8,
            "COLORSCALERANGE": "0.5,15.5",
            "NUMCOLORBANDS": "6",
            "ABOVEMAXCOLOR": "extend",
            "BELOWMINCOLOR": "transparent",
            "BGCOLOR": "extend",
            "LOGSCALE": "false"
        }
    },
}


# --------------------------------- MAPS -----------------------------------

maps = {
    "universiade2019": {
        "name": {
            "it-IT": "Previsioni Meteo Universiadi 2019",
            "en-US": "Universiade 2019 Weather Forecast"
        },
        "baseMaps": [
            {"satellite": False},
            {"osm": True}
        ],
        "layers": [
            {"cloud": True},
            {"t2c": False},
            {"rain": True},
            {"snow": True},
            {"wind": True},
            {"universiade2019": True},
        ]
    },
    "weather": {
        "name": {
            "it-IT": "Previsioni Meteo",
            "en-US": "Weather Forecast"
        },
        "baseMaps": [
            {"satellite": True},
            {"darkGray": False},
            {"osm": False}
        ],
        "layers": [
            {"slp": False},
            {"cloud": True},
            {"t2c": False},
            {"rain": True},
            {"snow": True},
            {"wind": True},
            {"info": False},
        ]
    },
    "muggles": {
        "name": {
            "it-IT": "Previsioni Meteo Semplificate",
            "en-US": "Easy Weather Forecast"
        },
        "baseMaps": [
            {"satellite": True},
        ],
        "layers": [
            {"cloud": True},
            {"rain": True},
            {"snow": True},
            {"wind": True},
            {"info": True},
        ]
    },
    "nautical": {
        "name": {
            "it-IT": "Previsioni Meteo Nautiche",
            "en-US": "Nautical Weather Forecast"
        },
        "baseMaps": [
            {"navionicsMarine": True},
            {"navionicsSonar": False}
        ],
        "layers": [
            {"cloud": True},
            {"t2c": False},
            {"rain": True},
            {"snow": True},
            {"wind": True}
        ]
    },
}

