import sys
from core.Logger import logger

from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon

from netCDF4 import Dataset as NetCDFFile
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.basemap import Basemap

from core.Places import Places
import haversine

import pickle
import json
import os
import datetime


class DataNotAvailableException(Exception):
    pass

class Plotter(object):
    maps = None
    config = None
    places = None
    ax = None
    data_path = None
    result_path = None
    cache_path = None

    # Constructor
    def __init__(self, config):

        # Set the configuration object
        self.config= config

        # Create a Places instance
        self.places = Places(self.config)

        # Check if in the configuration object MAPS is present
        if "MAPS" in self.config:

            # Get the name of the maps configuration file
            config_file = self.config["MAPS"]

            # Check if the file exists
            if os.path.exists(config_file):

                # Read the configuration file
                with open(config_file, 'r') as f:

                    # Parse the maps object from json
                    self.maps = json.load(f)

                    # Check if the data_path is present
                    if "data_path" not in self.maps :
                        raise Exception("Missing data_path in the json configuration file")
                    
                    # Get the data path
                    self.data_path = self.maps["data_path"]

                    # Check if the result_path is present
                    if "result_path" not in self.maps:
                        raise Exception("Missing result_path in the json configuration file")
                    
                    # Get the result path
                    self.result_path = self.maps["result_path"]

                    # Check if the cache_path is present
                    if "cache_path" not in self.maps:
                        raise Exception("Missing cache_path in the json configuration file")
        
                    # Get the cache path
                    self.cache_path = self.maps["cache_path"]

                    # Check if the cache path doesn't exist
                    if os.path.exists(self.cache_path) is False:

                        # Create the cache path
                        os.makedirs(self.cache_path)

            else:
                logger.critical(config_file + " not found!")
        else:
            logger.critical("MAPS not set in the json configuration file.")

    # Add a shaded layer to the basemap
    def _add_shaded(self, basemap, values, lons, lats, data, colors, legend_title, position_legend, size="2%",pad="5%", label_size=8, ticks_position="right", draw_colorbars = True):
        
        # Convert the colormap from 0-255 RGBA to 0.0-1.0 RGBA
        colors = [[j / 255 for j in i] for i in colors]

        # Append
        bounds = np.append(values[1:], values[-1] + 1)

        # Create a colormap with the listed colors skipping the first one
        cmap = ListedColormap(colors[1:])

        # Set the first color as the one below the bounds
        cmap.set_under(colors[0])

        # Set the last color as the ono over the bounds
        cmap.set_over(colors[-1])

        # Normalize the colormap on the bounds
        norm = BoundaryNorm(bounds, ncolors=len(colors) - 1)

        # Add a filled contour to the basemap
        cf = basemap.contourf(lons, lats, data, values[1:], cmap=cmap, norm=norm, latlon=True, extend='both',
                              vmin=values[0], vmax=values[-1])
        
        # Check if the color bars must be drawn
        if draw_colorbars:

            # Add the colorbar
            cf = basemap.colorbar(cf, position_legend, size=size, pad=pad, ticks=values[1:])

            # Set the tick parameters
            cf.ax.tick_params(labelsize=label_size)

            # Set the ticks position on the y axis
            cf.ax.yaxis.set_ticks_position(ticks_position)

            # Set the label position on the y axis
            cf.ax.yaxis.set_label_position(ticks_position)

            # Set the legend title
            cf.set_label(legend_title)

    # Add a shapefiles layer to the basemap
    def _add_shapefiles(self, basemap, shapefiles):

        # For each shapefile in the shapefiles array...
        for shapefile in shapefiles:

            # Check if the path is defined and if the related file exists
            if "path" in shapefile and os.path.exists(shapefile["path"]+".shp"):

                # Get the shapefile path
                shapefile_path = shapefile["path"]

                # Get the shapefile name
                shapefile_name = os.path.basename(shapefile_path)

                # Set default shapefile color
                shapefile_color = "black"

                # Check if the color is defined
                if "color" in shapefile:

                    # Set the color
                    shapefile_color = shapefile["color"]

                # Check if the marker is defined (point shapefile)
                if "marker" in shapefile:

                    # Get the marker object
                    marker = shapefile["marker"]

                    # Set the marker default symbol
                    marker_symbol = "+"

                    # Set the marker default size
                    marker_size = 1

                    # Set the marker default edge width
                    marker_edge_width = 1

                    # Check if the symbol is defined
                    if "symbol" in marker:

                        # Set the symbol
                        marker_symbol = marker["symbol"]

                    # Check if the edge width is defined
                    if "edge_width" in marker:

                        # Set the edge width
                        marker_edge_width = marker["edge_width"]

                    # Check if the marker size is defined
                    if "marker_size" in marker:

                        # Set the marker size
                        marker_size = marker["size"]

                    # Read the shapefile
                    basemap.readshapefile(shapefile_path, shapefile_name)

                    # For each point in the shapefile
                    for info, item in zip(getattr(basemap,shapefile_name+"_info"), getattr(basemap,shapefile_name)):

                        # Plot the marker on the basemap
                        basemap.plot(
                            item[0], item[1], marker=marker_symbol, color=shapefile_color,
                            markersize=marker_size, markeredgewidth=marker_edge_width
                            )

                # Check if fillcolor is defined (filled polygon shapefile)
                if "fillcolor" in shapefile:

                    # Set the fill color
                    shapefile_fillcolor = shapefile["fillcolor"]

                    # Read the shapefile
                    basemap.readshapefile(shapefile_path, shapefile_name, default_encoding='iso-8859-15', drawbounds = False)

                    # Define an array of patches
                    patches   = []

                    # Fpr each polygon on the shapefile...
                    for info, item in zip(getattr(basemap,shapefile_name+"_info"), getattr(basemap,shapefile_name)):

                        # Append a polygon to the patches array
                        patches.append(

                            # Create a polygon
                            Polygon(np.array(item), True)
                            )
        
                    # Add the collection of patches
                    self.ax.add_collection(
                        # Create a patch collection
                        PatchCollection(patches, facecolor= shapefile_fillcolor, edgecolor=shapefile_color, linewidths=0.5)
                        )

                else:

                    # Read the shapefile and add it to the basemap (Polygon shapefile)
                    basemap.readshapefile(shapefile_path, shapefile_name, default_encoding='iso-8859-15', color=shapefile_color)
                   

    def render(self, place, prod, output, dateTime, language="en-US", draw_colorbars=True):

        # Get place information by id
        place_info = self.places.get_place_by_id(place)
        # place_info = self.places.get_place_by_id(place, params)

        if (place_info is None) or (str(place_info['long_name']['it']) == "Italia" and prod == "rms3") or (str(place_info['long_name']['it']) == "Italia" and prod == "aiq3") or (str(place_info['long_name']['it']) == "Italia" and prod == "wcm3"):
            relative_path = self.config['NOIMAGE_PATH']
            image_name = "noimage.png"
            return relative_path, image_name
        

        # Get bounding box of the place
        minLat = place_info["minLat"]
        maxLat = place_info["maxLat"]
        minLon = place_info["minLon"]
        maxLon = place_info["maxLon"]

        # Calculate the distance between the two opposite vertex of the bounding box
        diag = haversine.haversine((minLat, minLon), (maxLat, maxLon))

        # The the domain id by the product and the place
        domainId = self.places.get_domain_and_indeces_by_product_and_place(prod, place)[0]     
          
        # Get the year (YYYY)
        year = dateTime[:4]

        # Get the month (01-12)
        month = dateTime[4:6] 

        # Get the day in the month (01-31)
        day = dateTime[6:8]

        # Get the hours (00-23)
        hour = dateTime[9:11]

        # Get the minutes (00-59, usually 00)
        minute = dateTime[11:13]

        # Assemble the path where data is located
        data_file = self.data_path + \
            prod + os.path.sep + domainId + os.path.sep +"archive" + \
            os.path.sep + year + os.path.sep  + month + os.path.sep + \
            day + os.path.sep  + prod + "_" + domainId + "_" + dateTime + ".nc"

        # Check if the the file not exists
        if os.path.exists(data_file) is False:
            # Raise an exception
            logger.error('data_file : ' + str(data_file))
            raise DataNotAvailableException
        
        # Assemble the relative path
        relative_path = "plt" + os.path.sep + place + os.path.sep + prod + os.path.sep  + year + os.path.sep  + month + os.path.sep  + day 

        # Assemble the image name
        image_name = "plt_" + place + "_" + prod + "_" + dateTime + "_" + output + "_1024x768.png" 

        # Assemble the path where the image will be written
        result_file = self.result_path + os.path.sep + relative_path + os.path.sep + image_name

        # Check if the destination path exists
        if os.path.exists(os.path.dirname(result_file)) is False:

            # Create the destination path
            os.makedirs(os.path.dirname(result_file))

        # Define the netcdf file
        nc = None
        try:
            nc = NetCDFFile(data_file)
        except:
            raise Exception
        
        # Get the latitude array
        lat = nc.variables['latitude'][:]

        # Get the longitude array
        lon = nc.variables['longitude'][:]

        # Get the time array
        time = nc.variables['time'][:]

        # Set default subsampling skip
        skip = 20

        # Set default scale factor
        scale = 1

        # Set default hepto Pascal tick
        hpa_tick = 1

        # Set default wind barb lenght
        barb_length = 1

        # Assemble the basemap 
        basemap_key = self.cache_path + os.path.sep + place + '.pkl'

        # Initialize the basemap object
        basemap = None

        # Check if the map is cached on disk
        if os.path.exists(basemap_key):
            
            # Open the cached file
            with open(basemap_key, 'rb') as f:

                # Load the cached file
                basemap = pickle.load(f)

        else:
            # Create the basemap
            basemap = Basemap(
                projection='merc',
                llcrnrlon=minLon, llcrnrlat=minLat, urcrnrlon=maxLon, urcrnrlat=maxLat)

            # Open the chacked file
            with open(basemap_key, 'wb') as f:

                # Write the file to the cache
                pickle.dump(basemap, f)

        # Add a subplot 
        self.ax  = plt.figure().add_subplot(111)

        # Check if a shapefiles object is defined in the configuration file
        if "shapefiles" in self.maps:

            # Add all the shapefiles as basemap
            self._add_shapefiles(basemap, self.maps["shapefiles"]) 

        # Set the number of map paralles
        parallels = np.arange(minLat, maxLat, (maxLat - minLat) / 4)

        # Set the number of map meridians
        meridians = np.arange(minLon, maxLon, (maxLat - minLat) / 4)

        # Draw the parallels
        basemap.drawparallels(parallels, labels=[1, 0, 0, 0], fontsize=4)

        # Draw the meridians
        basemap.drawmeridians(meridians, labels=[0, 0, 0, 1], fontsize=4)

        # Create a mesh grid using nongitudes and latitudes
        lons, lats = np.meshgrid(lon, lat)

        # Initialize the title string
        title = None

        # Check if products is in the configuration files
        if "products" not in self.maps:
            raise Exception("The products key missing in the configuration file")
        
        if prod not in self.maps["products"]:
            raise Exception("The " + prod + " key is missing in the products definition")
        
        # Check if a configuration is present for the selected product and domain
        if "config" in self.maps["products"][prod] and domainId in self.maps["products"][prod]["config"]:

            # Get the configuration items array for the product and domain
            items = self.maps["products"][prod]["config"][domainId]
            
            # For each item in the items array...
            for item in items:
                # Check if the place bounding box diagonal is withn a close or open boundary
                if (
                    "ge" in item and "lt" in item and item["ge"] <= diag < item["lt"]
                ) or (
                    "ge" in item and "lt" not in item and item["ge"] <= diag
                ):
                    # Check if the values is defined
                    if "values" in item:

                        # Get the values definition
                        values = item["values"]

                        # Check if the skip is defined
                        if "skip" in values:

                            # Set the skip
                            skip = values["skip"]

                        # Check if the scale is defined
                        if "scale" in values:

                            # Set the scale
                            scale = values["scale"]

                        # Check if the hpa tick is defined
                        if "hpa_tick" in values:

                            # Set the hpa tick
                            hpa_tick = values["hpa_tick"]

                        # Check if the barb lenght is defined
                        if "barb_length" in values:

                            # Set the barb lenght
                            barb_length = values["barb_length"]
                        break

        # Check if the outputs key is defined        
        if "outputs" not in self.maps["products"][prod]:
            raise Exception("The outputs key is missing in products."+prod)

        # Get the outputs dictionary
        outputs = self.maps["products"][prod]["outputs"]

        # Check if the selected output is in the output dictionary
        if output not in outputs:
            raise Exception("The " + output + " key is missing in products."+prod+".outputs")

        # Get the output object        
        outputs_output = outputs[output]
            
        # Check if the plot key is in the output 
        if "plot" not in outputs_output:
            raise Exception("The plot key is missing in products."+prod+".outputs." + output)
        
    
        # Get the plot object
        plot = outputs_output["plot"]

        # Set the default title
        title = ""

        # Check if the title key is in the output object
        if "title" in outputs_output:

            # Check if title in the selected language is not present
            if language not in outputs_output["title"]:

                # Set the language as english by default
                language = "en-US"
            
            # Get the title
   
        
        title = outputs_output["title"][language]
      
            
        # Check if the layers key is present in the plot object
        if "layers" not in plot:
            raise Exception("The layers key is not present in products."+prod+".outputs." + output+".plot")
        
        # Set the layers object
        layers = plot["layers"]

        # For each layer in layers...
        for layer in layers:

            # Define var1 name
            var1_name = None

            # Define var2 name 
            var2_name = None

            # Define the time index
            time = None

            # Define the level index
            level = None

            # Define default layer type 
            layer_type = "contourf"

            # Define default layer title
            text = ""

            # Define default pad
            pad = "10%"

            # Define default color bar position
            position = "left"

            # Define default ticks position
            ticks_position = "left"

            # Define default label size
            label_size = 8

            # Define colormap name
            colormap_name = None

            # Define colormap object
            colormap = None

            # Define default minimum contour level
            clev_min = 0

            # Define default maximum contour level 
            clev_max = 100

            # Check if the var1 key is defined in layer
            if "var1" in layer:

                # Set the var1 name
                var1_name = layer["var1"]

            # Check if the var2 key is defined in layer
            if "var2" in layer:

                # Set the var2 name
                var2_name = layer["var2"]

            # Check if the time key is defined 
            if "time" in layer:
                time = layer["time"]

            # Check if the level key is defined 
            if "level" in layer:
                level = layer["level"]

            # Check if the type key is defined 
            if "type" in layer:
                layer_type = layer["type"]

            # Check if the text key is defined 
            if "text" in layer:
                text = layer["text"][language]

            # Check if the pad key is defined 
            if "pad" in layer:
                pad = layer["pad"]

            # Check if the position key is defined 
            if "position" in layer:
                position = layer["position"]

            # Check if the ticks_position key is defined 
            if "ticks_position" in layer:
                ticks_position = layer["ticks_position"]

            # Check if the label_size key is defined
            if "label_size" in layer:
                label_size = layer["label_size"]

            # Check if the colormap key is defined
            if "colormap" in layer:
                colormap_name = layer["colormap"]

            # Check if the clev_min key is defined
            if "clev_min" in layer:
                clev_min = layer["clev_min"]

            # Check if the clev_max key is defined
            if "clev_max" in layer:
                clev_max = layer["clev_max"]

            # Check if the colors key is defined
            if "colors" in layer:
                colors = layer["colors"]

            # Check if the colormap name is present and not empity
            if colormap_name is not None and colormap_name != "":

                # Check if the colormap is not present
                if colormap_name not in self.maps["colormaps"]:
                    raise Exception("The " + colormap_name + " is not present in the configuration json file")
                
                # Set the colormap object    
                colormap = self.maps["colormaps"][colormap_name]

            # Set the var1 reference to None
            var1 = None

            # Set the var2 reference to None
            var2 = None

            # Check if both time and level are defined
            if time is not None and level is not None:

                # Check if var1 name is defined and not empty
                if var1_name is not None and var1_name != "":

                    # Read the var1 from the netcdf file
                    var1 = nc.variables[var1_name][:][time][level]

                # Check if var2 name is defined and not empty
                if var2_name is not None and var1_name != "":

                    # Read the var2 from the netcdf file
                    var2 = nc.variables[var2_name][:][time][level]

            # Check if only the time is defined
            elif time is not None and level is None:

                # Check if var 1 is defined and not empty
                if var1_name is not None and var1_name != "":

                    # Read the var1 from the netcdf file
                    var1 = nc.variables[var1_name][:][time]

                # Check if var 2 is defined and not empty
                if var2_name is not None and var1_name != "":

                    # Read the var2 from the netcdf file
                    var2 = nc.variables[var2_name][:][time]

            # Check if only level is defined
            elif time is None and level is not None:

                # Check if var 1 is defined and not empty
                if var1_name is not None and var1_name != "":

                    # Read the var1 from the netcdf file
                    var1 = nc.variables[var1_name][:][level]

                # Check if var 2 is defined and not empty
                if var2_name is not None and var1_name != "":

                    # Read the var2 from the netcdf file
                    var2 = nc.variables[var2_name][:][level]

            # Both time and level are not defined 
            else:
                # Check if var 1 is defined and not empty
                if var1_name is not None and var1_name != "":

                    # Read the var1 from the netcdf file
                    var1 = nc.variables[var1_name][:]

                # Check if var 2 is defined and not empty
                if var2_name is not None and var1_name != "":

                    # Read the var2 from the netcdf file
                    var2 = nc.variables[var2_name][:]

            # Check the a parameter is defined 
            if "a" in layer:

                # Multiply var 1 by a is it is defined 
                if var1 is not None: var1 = var1 * layer["a"]

                # Multiply var 2 by a is it is defined
                if var2 is not None: var2 = var2 * layer["a"]

            # Check the b parameter is defined
            if "b" in layer:

                # Add var 1 by b is it is defined 
                if var1 is not None: var1 = var1 + layer["b"]

                # Add var 2 by b is it is defined
                if var2 is not None: var2 = var2 + layer["b"]

            # Check check colormap is defined
            if colormap is not None and "clevs" in colormap and "ccols" in colormap:

                # Get the color levels
                clevs = colormap["clevs"]

                # Get the colors definition 
                colors = [tuple(x) for x in colormap["ccols"]]


            
            # Check if the layer type is shaded 
            if "shaded" in layer_type:
                var = None
                
                if var2 is not None:
                    var = np.hypot(var1, var2)
                else:
                    var = var1

                self._add_shaded(
                    basemap,
                    clevs,
                    lons, lats,
                    var, colors,
                    text, position, pad=pad, ticks_position=ticks_position, label_size=label_size, draw_colorbars=draw_colorbars)

            elif "contour" in layer_type:

                var = None
                if var2 is not None:
                    var = np.hypot(var1, var2)
                else:
                    var = var1
                
                # aggiunto da dario if 
                if output == 'wn2':
                    hpa_tick=140

                clevs = np.arange(clev_min, clev_max, hpa_tick)
                cs = basemap.contour(lons, lats, var, clevs, colors=colors, linewidths=0.5, latlon=True)
                clabels = plt.clabel(cs, fontsize=6, inline=1, fmt='%1.0f')
                [txt.set_bbox(dict(facecolor='white', edgecolor='none', pad=0)) for txt in clabels]

            elif "angle" in layer_type:
                skip2 = (slice(None, None, skip), slice(None, None, skip))
                var = 90-var1[skip2]
                var[var<0]+=360
                var[var>360]-=360
                var[var==360]=0
                var = var * 0.0174533 
                var1 = np.cos(var)
                var2 = np.sin(var)
                basemap.quiver(
                    lons[skip2], lats[skip2],
                    var1, var2,
                    latlon=True, scale=scale, scale_units="inches", pivot='middle', linewidths=.01,  edgecolors='gray'
                )

            elif "versor" in layer_type:
                skip2 = (slice(None, None, skip), slice(None, None, skip))
                var = np.hypot(var1[skip2], var2[skip2])
                basemap.quiver(
                    lons[skip2], lats[skip2],
                    var1[skip2] / var, var2[skip2] / var,
                    latlon=True, scale=scale, scale_units="inches", pivot='middle', linewidths=.01,  edgecolors='gray'
                )
            elif "vector" in layer_type:
                skip2 = (slice(None, None, skip), slice(None, None, skip))
                basemap.quiver(
                    lons[skip2], lats[skip2],
                    var1[skip2], var2[skip2],
                    latlon=True, scale=scale, scale_units="inches", pivot='middle'
                )
            elif "barbs" in layer_type:
                skip2 = (slice(None, None, skip), slice(None, None, skip))
                basemap.barbs(
                    lons[skip2], lats[skip2],
                    var1[skip2], var2[skip2],
                    latlon=True, pivot='middle',  barbcolor='#666666', length=barb_length
                )
            elif "shapefiles" in layer_type:
                if "shapefiles" in layer:
                    self._add_shapefiles(basemap,layer["shapefiles"])

        place_name = ""
        if language in place_info["name"]:
            place_name = place_info["name"][language]
        elif language[:2] in place_info["name"]:
            place_name = place_info["name"][language[:2]]
        else:
            place_name = place_info["name"][next(iter(place_info["name"]))]

        plot_title = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute)).strftime(self.maps["title"][language]).replace("__name__", place_name).replace("__title__", title).replace("__product__",prod).replace("__output__",output).replace("__place__",place).replace("__domain__",domainId)
        plt.title( plot_title )
        plt.show()
        plt.savefig(result_file, bbox_inches='tight', dpi=300)

        return relative_path, image_name
