"""Services for generating Skew-T meteorological diagrams."""

#################################################
#
# Author: Diana Di Luccio
#
#################################################

import wrf
import os
from netCDF4 import Dataset
import matplotlib.pyplot as plt
import numpy as np
import metpy.calc as mpcalc
from metpy.units import units
from metpy.plots import SkewT, Hodograph
from core.Logger import logger


class SkewTServices:
    """Service or helper that encapsulates skew tservices behavior."""
    def __init__(self, dataset):
        """Initialize skew tservices state."""
        self.dataset = dataset

    
    def SkewTPlot(self, save_path, lat, lon):
        """Implement skew tplot for skew tservices."""
        wrfin = None
        fig = None
        try:
            wrfin = Dataset(self.dataset)
            x_y = wrf.ll_to_xy(wrfin, lat, lon)
            x_index = int(x_y[0])
            y_index = int(x_y[1])

            p1 = wrf.getvar(wrfin, "pressure", timeidx=0)
            T1 = wrf.getvar(wrfin, "tc", timeidx=0)
            Td1 = wrf.getvar(wrfin, "td", timeidx=0)
            u1 = wrf.getvar(wrfin, "ua", timeidx=0)
            v1 = wrf.getvar(wrfin, "va", timeidx=0)
            z1 = wrf.getvar(wrfin, "z", timeidx=0)
            hght = wrf.getvar(wrfin, "height", timeidx=0)
            logger.debug("SkewT temperature field loaded")

            hg = hght[:, x_index, y_index].values * units.hPa
            p = p1[:, x_index, y_index].values * units.hPa
            T = T1[:, x_index, y_index].values * units.degC
            Td = Td1[:, x_index, y_index].values * units.degC
            u = u1[:, x_index, y_index].values * units('m/s')
            v = v1[:, x_index, y_index].values * units('m/s')
            z = z1[:, x_index, y_index].values * units.m

            prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
            lcl_pressure, lcl_temperature = mpcalc.lcl(p[0], T[0], Td[0])
            logger.debug("LCL_P=%s", lcl_pressure)
            logger.debug("LCL_T=%s", lcl_temperature)

            try:
                lfc_p, lfc_t = mpcalc.lfc(p, T, Td, prof)
            except Exception:
                lfc_p, lfc_t = lcl_pressure, lcl_temperature
            logger.debug("lfc_p=%s", lfc_p)
            logger.debug("lfc_t=%s", lfc_t)

            el_p, el_t = mpcalc.el(p, T, Td)
            logger.debug("el_p=%s", el_p)
            logger.debug("el_t=%s", el_t)

            try:
                sbcape, sbcin = mpcalc.surface_based_cape_cin(p, T, Td)
            except IndexError:
                sbcape, sbcin = 0.0 * units.joule / units.kilogram, -999.9 * units.joule / units.kilogram
            try:
                mucape, mucin = mpcalc.most_unstable_cape_cin(p, T, Td)
            except IndexError:
                mucape, mucin = 0.0 * units.joule / units.kilogram, -999.9 * units.joule / units.kilogram

            pwat = mpcalc.precipitable_water(p, Td)
            kindex = mpcalc.k_index(p, T, Td)
            total_totals = mpcalc.total_totals_index(p, T, Td)

            logger.debug("SBCAPE=%s", sbcape)
            logger.debug("SBCIN=%s", sbcin)
            logger.debug("MUCAPE=%s", mucape)
            logger.debug("MUCIN=%s", mucin)
            logger.debug("PWATER=%s", pwat)
            logger.debug("KINDEX=%s", kindex)
            logger.debug("TT=%s", total_totals)
            logger.debug("pressure range: %s %s", p.min(), p.max())
            logger.debug("surface values: T=%s Td=%s", T[0], Td[0])
            logger.debug("number of levels: %s", len(p))

            fig = plt.figure(figsize=(15, 9))
            skew = SkewT(fig, rect=(0.08, 0.1, 0.6, 0.8))
            skew.plot(p, T, 'r', label='TEMPERATURE')
            skew.plot(p, Td, 'g', label='DEWPOINT')
            skew.plot(p, prof, 'k', linewidth=2, label='SB PARCEL PATH')

            my_interval = np.arange(100, 1000, 50) * units('mbar')
            ix = mpcalc.resample_nn_1d(p, my_interval)
            skew.plot_barbs(p[ix], u[ix], v[ix])

            skew.plot_dry_adiabats()
            skew.plot_moist_adiabats()
            skew.plot_mixing_lines()
            skew.ax.set_ylim(1000, 100)
            skew.ax.set_xlim(-60, 40)
            skew.shade_cape(p, T, prof, alpha=0.2, label='SBCAPE')
            skew.shade_cin(p, T, prof, alpha=0.2, label='SBCIN')
            skew.ax.set_xlabel('Temperature ($^\circ$C)')
            skew.ax.set_ylabel('Pressure (hPa)')
            skew.ax.legend(loc='upper left')

            ax = plt.axes((0.65, 0.50, 0.4, 0.4))
            h = Hodograph(ax, component_range=80.)
            h.add_grid(increment=20)

            line = h.plot_colormapped(u, v, hg)
            cbar = plt.colorbar(line, fraction=0.05, orientation='horizontal')
            cbar.set_label('Height [m]')

            plt.figtext(0.73, 0.37, f"SBCAPE: {sbcape:.0f~P}", weight="bold", fontsize=15, color="black", ha="left")
            plt.figtext(0.73, 0.34, f"SBCIN: {sbcin:.0f~P}", weight="bold", fontsize=15, color="black", ha="left")
            plt.figtext(0.73, 0.31, f"MUCAPE: {mucape:.0f~P}", weight="bold", fontsize=15, color="black", ha="left")
            plt.figtext(0.73, 0.28, f"MUCIN: {mucin:.0f~P}", weight="bold", fontsize=15, color="black", ha="left")
            plt.figtext(0.73, 0.25, f"TT-INDEX: {total_totals:.0f~P}", weight="bold", fontsize=15, color="black", ha="left")
            plt.figtext(0.73, 0.22, f"K-INDEX: {kindex:.0f~P}", weight="bold", fontsize=15, color="black", ha="left")

            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            fig.savefig(save_path, bbox_inches='tight', dpi=300)
        finally:
            if wrfin is not None:
                wrfin.close()
            if fig is not None:
                plt.close(fig)


       
