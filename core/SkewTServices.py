#################################################
#
# Author: Diana Di Luccio
#
#################################################

#Skew-T LogP plot for WRF out file
import wrf
import os
from netCDF4 import Dataset
import matplotlib.pyplot as plt
import numpy as np
#import proplot as pplt
import metpy.calc as mpcalc
from metpy.plots import SkewT
from metpy.units import units
import pandas as pd
import metpy.calc as mpcalc
from metpy.units import units
from metpy.plots import SkewT, Hodograph


class SkewTServices:
    def __init__(self, dataset):
        self.dataset = dataset

    
    def SkewTPlot(self, save_path, lat, lon):

        wrfin = Dataset(self.dataset)
        lat_lon = [lat, lon]
        x_y = wrf.ll_to_xy(wrfin, lat_lon[0], lat_lon[1])

        p1 = wrf.getvar(wrfin,"pressure",timeidx=0)
        T1 = wrf.getvar(wrfin,"tc",timeidx=0)
        Td1 = wrf.getvar(wrfin,"td",timeidx=0)
        u1 = wrf.getvar(wrfin,"ua",timeidx=0)
        v1 = wrf.getvar(wrfin,"va",timeidx=0)
        z1 = wrf.getvar(wrfin,"z",timeidx=0)
        hght = wrf.getvar(wrfin,"height",timeidx=0)
        print(T1)

        hg = hght[:,x_y[0],x_y[1]].values * units.hPa
        p = p1[:,x_y[0],x_y[1]].values * units.hPa
        T = T1[:,x_y[0],x_y[1]].values * units.degC
        Td = Td1[:,x_y[0],x_y[1]].values * units.degC
        u = u1[:,x_y[0],x_y[1]].values * units('m/s')
        v = v1[:,x_y[0],x_y[1]].values * units('m/s')
        z = z1[:,x_y[0],x_y[1]].values * units.m


        # aggiunta Profilo parcel & LCL
        prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
        lcl_pressure, lcl_temperature = mpcalc.lcl(p[0], T[0], Td[0])
        print("LCL_P=",lcl_pressure)
        print("LCL_T=",lcl_temperature)

        parcel_t_start = T[0]
        print("Pt_start=",parcel_t_start)
        parcel_p_start = p[0]
        print("Pp_start=",parcel_p_start)
        try:
            lfc_p, lfc_t = mpcalc.lfc(p, T, Td, prof)
        except Exception:
            lfc_p, lfc_t = lcl_pressure, lcl_temperature
        print("lfc_p=",lfc_p)
        print("lfc_t=",lfc_t)

        el_p,el_t = mpcalc.el(p,T,Td)
        print("el_p=",el_p)
        print("el_t=",el_t)

        try:
            sbcape,sbcin = mpcalc.surface_based_cape_cin(p,T,Td)
        except IndexError:
            sbcape,sbcin = 0.0*units.joule/units.kilogram,-999.9*units.joule/units.kilogram
        try:
            mucape,mucin = mpcalc.most_unstable_cape_cin(p,T,Td)
        except IndexError:
            mucape,mucin = 0.0*units.joule/units.kilogram,-999.9*units.joule/units.kilogram

        pwat = mpcalc.precipitable_water(p,Td)
        kindex = mpcalc.k_index(p, T, Td)
        total_totals = mpcalc.total_totals_index(p, T, Td)

        print("SBCAPE=",sbcape)
        print("SBCIN=",sbcin)
        print("MUCAPE=",mucape)
        print("MUCIN=",mucin)
        print("PWATER=",pwat)
        print("KINDEX",kindex)
        print("TT", total_totals)

        print("p range:", p.min(), p.max())
        print("T surface:", T[0], "Td surface:", Td[0])
        print("Numero livelli:", len(p))


        #fine aggiunte
        fig = plt.figure(figsize=(15, 9))
        skew = SkewT(fig, rect=(0.08, 0.1, 0.6, 0.8))
        # Plot the data using normal plotting functions, in this case using
        # log scaling in Y, as dictated by the typical meteorological plot
        skew.plot(p, T, 'r',label='TEMPERATURE')
        skew.plot(p, Td, 'g',label='DEWPOINT')

        #aggiunte
        skew.plot(p, prof, 'k', linewidth=2,label='SB PARCEL PATH')
        #file aggiunte

        # Set spacing interval--Every 50 mb from 1000 to 100 mb
        my_interval = np.arange(100, 1000, 50) * units('mbar')

        # Get indexes of values closest to defined interval
        ix = mpcalc.resample_nn_1d(p, my_interval)

        # Plot only values nearest to defined interval values
        skew.plot_barbs(p[ix], u[ix], v[ix])

        # Add the relevant special lines
        skew.plot_dry_adiabats()
        skew.plot_moist_adiabats()
        skew.plot_mixing_lines()
        skew.ax.set_ylim(1000, 100)
        skew.ax.set_xlim(-60, 40)

        skew.shade_cape(p, T, prof, alpha=0.2, label='SBCAPE')
        skew.shade_cin(p, T, prof, alpha=0.2, label='SBCIN')

        skew.ax.set_xlabel('Temperature ($^\circ$C)')
        skew.ax.set_ylabel('Pressure (hPa)')

        skew.ax.set_ylabel('Pressure (hPa)')

        # Add legends to the skew and hodo
        skewleg = skew.ax.legend(loc='upper left')

        # Create a hodograph
        #ax_hod = inset_axes(skew.ax, '40%', '40%', loc=1)
        ax = plt.axes((0.65, 0.50, 0.4, 0.4))
        h = Hodograph(ax, component_range=80.)
        h.add_grid(increment=20)

        l=h.plot_colormapped(u, v, hg)
        cbar=plt.colorbar(l,fraction=0.05, orientation='horizontal')
        cbar.set_label('Height [m]')

        # There is a lot we can do with this data operationally, so let's plot some of
        # these values right on the plot, in the box we made
        # First lets plot some thermodynamic parameters
        plt.figtext(0.73, 0.37,f"SBCAPE: {sbcape:.0f~P}", weight="bold", fontsize=15, color="black", ha="left")
        plt.figtext(0.73, 0.34,f"SBCIN: {sbcin:.0f~P}", weight="bold", fontsize=15, color="black", ha="left")

        plt.figtext(0.73, 0.31,f"MUCAPE: {mucape:.0f~P}", weight="bold", fontsize=15, color="black", ha="left")
        plt.figtext(0.73, 0.28,f"MUCIN: {mucin:.0f~P}", weight="bold", fontsize=15, color="black", ha="left")

        plt.figtext(0.73, 0.25,f"TT-INDEX: {total_totals:.0f~P}", weight="bold", fontsize=15, color="black", ha="left")
        plt.figtext(0.73, 0.22,f"K-INDEX: {kindex:.0f~P}", weight="bold", fontsize=15, color="black", ha="left")

        #plt.show()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, bbox_inches='tight', dpi=300)


       