import matplotlib
import netCDF4
import numpy
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from matplotlib.figure import Figure
import cartopy.crs as ccrs
import cartopy.io.shapereader as shapereader


def MakeFigureAndAxes(min_lon: str, max_lon: str, min_lat: str, max_lat: str, label: str, place: str, prod: str):
    shape = list(shapereader.Reader("/Users/dario/PycharmProjects/Meteorographica/Europa_shp_data/europe.shp").geometries())
    fig = Figure(figsize=(15.0, 10.0), dpi=300, edgecolor='#000000', linewidth=0.0) #frameon=False  subplotpars=None frameon=False, tight_layout=None

    title_1 = "http://meteo.uniparthenope.it"
    title_2 = "Forecast : " + str(label) + " ( " + str(place) + " / " + str(prod) + " )"
    fig.suptitle(title_1 + "\n" + title_2, size=25, color='#000000')

    projection = ccrs.RotatedPole(pole_longitude=180.0, pole_latitude=90.0)
    ax = fig.add_axes([0.05, 0, 0.90, 1], projection=projection)
    ax.add_geometries(shape, projection, edgecolor='black', facecolor='white')
    extent = [float(min_lon), float(max_lon), float(min_lat), float(max_lat)]
    ax.set_extent(extent, crs=projection)

    return fig, ax


def AddGrid(ax, min_lon: str, max_lon: str, min_lat: str, max_lat: str, **kwargs):
    kwargs.setdefault('linestyle_major', '-')
    kwargs.setdefault('linewidth_major', 0.1)
    kwargs.setdefault('sep_major', 2.0)
    kwargs.setdefault('zorder', 0)

    gl_major = ax.gridlines(linestyle=kwargs.get('linestyle_major'), linewidth=kwargs.get('linewidth_major'), color=kwargs.get('color_major'), draw_labels=True, x_inline=False, y_inline=False)

    if float(max_lat) - float(min_lat) > 0.20:
        gl_major.xlocator = matplotlib.ticker.FixedLocator(numpy.arange(float(min_lon), float(max_lon) + kwargs.get('sep_major'), kwargs.get('sep_major')))
        gl_major.ylocator = matplotlib.ticker.FixedLocator(numpy.arange(float(min_lat), float(max_lat) + kwargs.get('sep_major'), kwargs.get('sep_major')))
    else:
        gl_major.xlocator = matplotlib.ticker.FixedLocator(numpy.arange(float(min_lon), float(max_lon) + 0.015, 0.015))
        gl_major.ylocator = matplotlib.ticker.FixedLocator(numpy.arange(float(min_lat), float(max_lat) + 0.015, 0.015))


    gl_major.xformatter = LONGITUDE_FORMATTER
    gl_major.yformatter = LATITUDE_FORMATTER

    gl_major.top_labels = False
    gl_major.right_labels = False

    gl_major.xlabel_style = {'color': 'black', 'weight': 'bold'}
    gl_major.ylabel_style = {'color': 'black', 'weight': 'bold'}


def PlotBarbsWind(url_dataset, ax):
    dataset = netCDF4.Dataset(url_dataset)
    ax.barbs(dataset.variables['longitude'][:], dataset.variables['latitude'][:], dataset.variables['U10M'][0, :, :] * 1.94, dataset.variables['V10M'][0, :, :] * 1.94, regrid_shape=10, zorder=5)
    dataset.close()


def PlotSeaWaveAndDir(url_dataset, ax):
    dataset = netCDF4.Dataset(url_dataset)
    ax.contourf(dataset.variables['longitude'][:], dataset.variables['latitude'][:], dataset.variables['hs'][0, :, :])
    ax.contour(dataset.variables['longitude'][:], dataset.variables['latitude'][:], dataset.variables['lm'][0, :, :])
    ax.quiver(dataset.variables['longitude'][:], dataset.variables['latitude'][:], numpy.cos((dataset.variables['dir'][0, :, :]-180)*0.0174533), (dataset.variables['dir'][0, :, :]-180)*0.0174533, regrid_shape=20)
    dataset.close()


def PlotClouds(url_dataset, ax):
    dataset = netCDF4.Dataset(url_dataset)
    min_val = numpy.min(dataset.variables['CLDFRA_TOTAL'][0, :, :])
    max_val = numpy.max(dataset.variables['CLDFRA_TOTAL'][0, :, :])
    if min_val != max_val:
        ax.contourf(dataset.variables['longitude'][:], dataset.variables['latitude'][:], dataset.variables['CLDFRA_TOTAL'][0, :, :], alpha=0.30, colors=['#C0C0C0', '#A0A0A0', '#808080'], zorder=5) #colors=['#808080', '#A0A0A0', '#C0C0C0'])
    dataset.close()


def PlotRain(url_dataset, ax):
    dataset = netCDF4.Dataset(url_dataset)
    min_val = numpy.min(dataset.variables['DELTA_RAIN'])
    max_val = numpy.max(dataset.variables['DELTA_RAIN'])
    if min_val != max_val:
        ax.contourf(dataset.variables['longitude'][:], dataset.variables['latitude'][:], dataset.variables['DELTA_RAIN'][0, :, :], alpha=0.30, colors=['#808080', '#A0A0A0', '#C0C0C0'], algorithm='threaded')
    dataset.close()


def PlotSnow(url_dataset, ax):
    dataset = netCDF4.Dataset(url_dataset)
    min_val = numpy.min(dataset.variables['HOURLY_SWE'])
    max_val = numpy.max(dataset.variables['HOURLY_SWE'])
    if min_val != max_val:
        ax.contourf(dataset.variables['longitude'][:], dataset.variables['latitude'][:], dataset.variables['HOURLY_SWE'][0, :, :], alpha=0.30,  colors=['#808080', '#A0A0A0', '#C0C0C0'], algorithm='threaded')
    dataset.close()


def PlotCur(url_dataset, ax):
    dataset = netCDF4.Dataset(url_dataset)
    cs = mag(dataset.variables['u'][0, :, :, :], dataset.variables['v'][0, :, :, :])
    ax.contourf(dataset.variables['longitude'][:], dataset.variables['latitude'][:], cs[0, :, :])
    u = dataset.variables['u'][0, :, :, :] / cs[0, :, :]
    v = dataset.variables['v'][0, :, :, :] / cs[0, :, :]
    ax.quiver(dataset.variables['longitude'][:], dataset.variables['latitude'][:], u[0, :, :], v[0, :, :], regrid_shape=20)
    dataset.close()


def PlotConc(url_dataset, ax):
    dataset = netCDF4.Dataset(url_dataset)
    ax.contourf(dataset.variables['longitude'][:], dataset.variables['latitude'][:], dataset.variables['conc'][0, 0, :, :], alpha=0.30)
    dataset.close()


def mag(u, v):
    return numpy.sqrt(u[:]*u[:]+v[:]*v[:])


def FigureSave(fig, url):
    fig.savefig(url)


def wrf5MapGen(url_dataset, min_lon: str, max_lon: str, min_lat: str, max_lat: str, label: str, place: str, prod: str):
    fig, axes = MakeFigureAndAxes(min_lon, max_lon, min_lat, max_lat, label, place, prod)
    AddGrid(axes, min_lon, max_lon, min_lat, max_lat, sep_major=0.10, color_major='#000000')
    PlotClouds(url_dataset, axes)
    PlotRain(url_dataset, axes)
    PlotSnow(url_dataset, axes)
    PlotBarbsWind(url_dataset, axes)
    FigureSave(fig, "wrf5MapGen.png")


def rms3MapGen(url_dataset, min_lon: str, max_lon: str, min_lat: str, max_lat: str, label: str, place: str, prod: str):
    fig, axes = MakeFigureAndAxes(min_lon, max_lon, min_lat, max_lat, label, place, prod)
    AddGrid(axes, min_lon, max_lon, min_lat, max_lat, sep_major=0.10, color='#ffffff')
    PlotCur(url_dataset, axes)
    FigureSave(fig, "rms3MapGen.png")


def ww33MapGen(url_dataset, min_lon: str, max_lon: str, min_lat: str, max_lat: str, label: str, place: str, prod: str):
    fig, axes = MakeFigureAndAxes(min_lon, max_lon, min_lat, max_lat, label, place, prod)
    AddGrid(axes, min_lon, max_lon, min_lat, max_lat, sep_major=0.10, color='#ffffff')
    PlotSeaWaveAndDir(url_dataset, axes)
    FigureSave(fig, "ww33MapGen.png")


def wcm3MapGen(url_dataset, min_lon: str, max_lon: str, min_lat: str, max_lat: str, label: str, place: str, prod: str):
    fig, axes = MakeFigureAndAxes(min_lon, max_lon, min_lat, max_lat, label, place, prod)
    AddGrid(axes, min_lon, max_lon, min_lat, max_lat, sep_major=0.10, color='#ffffff')
    PlotConc(url_dataset, axes)
    FigureSave(fig, "wcm3MapGen.png")


if __name__ == '__main__':
    pass
    # ca001
    # figure, ax = MakeFigureAndAxes("13.81", "14.57", "40.51", "40.88", "Golfo Di Napoli", "ca001", "x")
    # ca002
    # figure, ax = MakeFigureAndAxes("14.13", "15.06", "40.24", "40.69", "Golfo Di Salerno", "ca002", "x")
    # ca003
    # figure, ax = MakeFigureAndAxes("14.85", "15.8", "39.81", "40.27", "Cilento", "ca003", "x")
    # ca004
    # figure, ax = MakeFigureAndAxes("14.18", "14.33", "40.78", "40.85", "Baia Di Napoli", "ca004", "x")
    # ca005
    # figure, ax = MakeFigureAndAxes("13.81", "14.0", "40.65", "40.8", "Isola D'Ischia", "ca005", "x")
    # ca006
    # figure, ax = MakeFigureAndAxes("13.98", "14.05", "40.73", "40.8", "Isola Di Procida", "ca006", "x")
    # ca015
    # figure, ax = MakeFigureAndAxes("14.2", "14.26", "40.79", "40.84", "America Cup World Series", "ca006", "x")


    # wrf5MapGen("wrf5_d03_20230526Z0900.nc", "13.81", "14.57", "40.51", "40.88", "Golfo Di Napoli", "ca001", "wrf5")
    # ww33MapGen("ww33_d03_20230524Z0900.nc", "13.81", "14.57", "40.51", "40.88", "Golfo Di Napoli", "ca001", "ww33")
    # rms3MapGen("rms3_d03_20230522Z0700.nc", "13.81", "14.57", "40.51", "40.88", "Golfo Di Napoli", "ca001", "rms3")
    # wcm3MapGen("wcm3_d03_20230526Z1700.nc", "13.81", "14.57", "40.51", "40.88", "Golfo Di Napoli", "ca001", "wcm3")


