"""Plotting weather maps, meteograms, and other visualizations."""

import os
import datetime
import pytz

import matplotlib as M
from matplotlib.font_manager import FontProperties
import matplotlib.pyplot as plt
import numpy as np
import cartopy.feature as cfeature
from cartopy import crs as ccrs

from utils.lookups import lat_lon

M.rcParams["font.size"] = 11
M.rcParams["font.family"] = "Helvetica"

def plot_meteogram(df, plot_col, title=None, save=None,second_df=None, second_col=None):
    """Plot a meteogram of the dataframe of data.

    Args:
        df (pd.DataFrame): DataFrame of data to plot.
        plot_col (str): Column in df to plot.
        title (str, optional): Title of the plot. Defaults to no title.
        save (str, optional): Path to save the plot. Defaults to not saving (only returning) the plot.
        second_df (pd.DataFrame, optional): Second DataFrame of data to plot. Defaults to None.
        second_col (str, optional): Column in second_df to plot. Defaults to None.

    Returns:
        fig, ax: Matplotlib figure and axis objects.
    """

    fig, ax = plt.subplots(1, figsize=(12, 8), dpi=200)

    # Plotting the data
    ax.plot(df.index, df[plot_col])

    if second_df is not None:
        assert second_col is not None
        ax.plot(second_df.index, second_df[second_col])

    # Setting the title
    if title:
        ax.set_title(title, fontsize=16, fontweight='bold')

    # Formatting the UTC time on the x-axis
    ax.xaxis.set_major_formatter(M.dates.DateFormatter('%Y-%m-%d %H:%M', tz=pytz.utc))
    plt.xticks(rotation=45)

    fig.tight_layout()

    # Refresh the figure to ensure the labels are updated
    fig.canvas.draw()

    # Optional: Adding local time labels in red below UTC labels
    local_tz = pytz.timezone('America/Denver')  # Adjust for your timezone
    for tick in ax.get_xticklabels():
        # Ensure the tick label is not empty
        if tick.get_text():
            utc_time = datetime.datetime.strptime(tick.get_text(), '%Y-%m-%d %H:%M')
            local_time = utc_time.replace(tzinfo=pytz.utc).astimezone(local_tz)
            ax.text(tick.get_position()[0], tick.get_position()[1] - 0.05,
                    local_time.strftime('%-I:%M %p'), color='red',
                    ha='right', transform=ax.get_xaxis_transform())

    # Saving the figure
    if save is not None:
        fig.savefig(save)

    return fig, ax

def surface_plot(ds,vrbl_key,fchr=0,label="variable",save=None,vlim=None,levels=None,plot_type="pcolormesh",
                         my_extent=[-110.6, -108.7, 40.95, 39.65]):
    if "step" in ds.dims:
        plot_data = ds.isel(step=fchr)[vrbl_key]
    else:
        plot_data = ds[vrbl_key]

    my_transform = ccrs.PlateCarree()

    fig, ax = plt.subplots(1, figsize=[8,6], constrained_layout=True, dpi=250,
                      subplot_kw={'projection' : ds.herbie.crs},) #  my_transform = ccrs.PlateCarree())
    coast = cfeature.NaturalEarthFeature(category='physical', scale='10m',
                                         edgecolor='black', name='coastline')

    counties = cfeature.NaturalEarthFeature(category='cultural', scale='10m',
                                            edgecolor='black', name='admin_2_counties_lakes', alpha=0.2)
    if vlim is None:
        vmin = None
        vmax = None
    else:
        vmin, vmax = vlim

    cmap = plt.cm.inferno_r
    colors = cmap(np.arange(cmap.N))
    colors[:int(0.2 * cmap.N), -1] = np.linspace(0, 1, int(0.2 * cmap.N))  # Adjust transparency
    my_cm = M.colors.LinearSegmentedColormap.from_list('custom_plasma', colors)

    # f1 = ax.contourf(
    if plot_type == "pcolormesh":
        f1 = ax.pcolormesh(
                        ds.longitude, ds.latitude,
                        plot_data,
                        alpha=0.8,
                        transform=my_transform,
                        vmin=vmin, vmax=vmax,
                        cmap=M.cm.inferno_r,
                        # cmap=my_cm,
                        # levels=levels,
                        )
        c1 = plt.colorbar(f1, fraction=0.046, pad=0.04)
        c1.set_label(label=label, size=18, weight='bold')
        c1.ax.tick_params(labelsize=18)

    elif plot_type == "contour":
        f1 = ax.contour(
                        ds.longitude, ds.latitude,
                        plot_data,
                        transform=my_transform,
                        color=["k",],
                        # levels=levels,
                        )
    else:
        raise Exception


    ax.add_feature(cfeature.STATES, facecolor='none', edgecolor='black')
    ax.add_feature(coast, facecolor='none', edgecolor='black')
    ax.add_feature(counties, facecolor='none', edgecolor='black')
    ax.add_feature(cfeature.LAKES, facecolor="none",edgecolor="black")
    ax.add_feature(cfeature.RIVERS, facecolor="none", edgecolor="black")

    # lat_lon is dictionary of {place: (lat,lon)}
    for place, (lat, lon) in lat_lon.items():
        ax.scatter(lon, lat, transform=ccrs.PlateCarree(), marker='o', color='r')
        ax.text(lon, lat, place, transform=ccrs.PlateCarree(), size=12, ha='right', va='bottom', color='blue')

    # To zoom further in:

    ax.set_extent(my_extent, crs=my_transform)

    if save is not None:
        fig.savefig(save)

    return fig,ax


def plot_hline_lv(ax,lv_dict,c="red",lw=0.5):
    font_props = FontProperties()
    font_props.set_weight('bold')
    font_props.set_variant('small-caps')

    for k,v in lv_dict.items():
        ax.text(0.01, v, f'{k}', verticalalignment='center', color=c, fontsize=9,
                    transform=ax.get_yaxis_transform(), ha='left', backgroundcolor='white',
                    fontproperties=font_props)
        ax.axhline(v, color=c, lw=lw)
    return ax

def plot_profile(T_profile,Z_profile,fmt, xlim=None, ylim=None,
                        plot_levels=None,save=None,title=None):
    fig, ax = plt.subplots(1, figsize=(8,8))
    if fmt == "model":
        f1 = ax.plot(T_profile,Z_profile,color='#1f77b4',lw=2)
    elif fmt == "obs":
        f1 = ax.scatter(T_profile,Z_profile)
    if ylim is not None:
        ax.set_ylim(ylim)
    if xlim is not None:
        ax.set_xlim(xlim)

    ax.set_xlabel('Temperature (C)', fontsize=12, fontweight='bold', color='#333333')
    ax.set_ylabel('Altitude (m)', fontsize=12, fontweight='bold', color='#333333')
    # Add subtitle with date
    if title is None:
        title = 'Vertical profile of temperature'
    ax.set_title(title, fontsize=16, fontweight='bold', color='#333333')

    ax.grid(True, which='both', linestyle='--', linewidth=0.5, alpha=0.7)
    ax.minorticks_on()

    # Setting spines to be less prominent
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#888888')
    ax.spines['left'].set_color('#888888')

    ax.tick_params(axis='both', which='both', labelsize=10, labelcolor='#333333')

    if plot_levels is not None:
        ax = plot_hline_lv(ax,plot_levels)

    if save is not None:
        fig.savefig(save)
    pass
    return fig,ax

def do_sfc_plot(ds,vrbl,minmax=None):
    # TODO: units and conversion elegantly!
    data = ds[vrbl]
    if vrbl == "t2m":
        # K to C
        data -= 273.15
    fig,ax = plt.subplots(1)
    if minmax is None:
        im = ax.imshow(data[::-1,:])
    else:
        im = ax.imshow(data[::-1,:],vmin=minmax[0],vmax=minmax[1])
    plt.colorbar(im)
    return fig,ax