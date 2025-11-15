"""Plotting weather maps, meteograms, and other visualizations."""

import os
import datetime

import pandas as pd
import pytz

import matplotlib as M
import matplotlib.cm as cmaps
import matplotlib.dates as mdates
from cfgrib.messages import multi_enabled
from matplotlib.font_manager import FontProperties
import matplotlib.pyplot as plt
import numpy as np
import cartopy.feature as cfeature
from cartopy import crs as ccrs

from utils.utils import get_nice_tick_spacing
from utils.lookups import lat_lon, Lookup

M.rcParams["font.size"] = 11
# M.rcParams["font.family"] = ["Helvetica", "Ubuntu Light", "Roboto", "Nimbus Sans",]
M.rcParams["font.family"] = "sans-serif"
M.rcParams["font.sans-serif"] = ["Nimbus Sans", "Helvetica", "Ubuntu Sans Light", "Roboto Sans"]

def plot_comparison_meteogram(df, plot_col, title=None, save=None,
                                second_df=None, second_col=None):
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
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M', tz=pytz.utc))
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

def surface_plot(ds,vrbl_key,fchr=0,label="variable",save=None,vlim=None,
                        levels=None, plot_type="pcolormesh",
                        my_extent=None,
                        annotate_vals=False, decimal_places=2):
    if my_extent is None:
        my_extent=[-110.6, -108.7, 40.95, 39.65]
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

    cmap = cmaps.inferno_r
    colors = cmap(np.arange(cmap.N))
    colors[:int(0.2 * cmap.N), -1] = np.linspace(0, 1, int(0.2 * cmap.N))  # Adjust transparency
    my_cm = M.colors.LinearSegmentedColormap.from_list('custom_plasma', colors)

    # f1 = ax.contourf(
    if plot_type == "pcolormesh":
        f1 = ax.pcolormesh(
            ds.longitude, ds.latitude,
            plot_data,
            alpha=0.63,
            transform=my_transform,
            vmin=vmin, vmax=vmax,
            cmap=cmaps.inferno_r,
            # cmap=my_cm,
            # levels=levels,
            edgecolors='black',
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

    # Annotate plot_data gridded values on the plot in the centre of each cell
    for i in range(plot_data.shape[0]):
        for j in range(plot_data.shape[1]):
            ax.text(ds.longitude.values[j], ds.latitude.values[i],
                    f'{plot_data.values[i, j]:.{decimal_places}f}',
                    ha='center', va='center', transform=my_transform,
                    fontsize=8, color='black')

    # MAP FEATURES
    ax.add_feature(cfeature.STATES, facecolor='none', edgecolor='red',
                   linewidth=0.5, linestyle=':')
    ax.add_feature(coast, facecolor='none', edgecolor='black')
    ax.add_feature(counties, facecolor='none', edgecolor='gray', alpha=0.3)
    ax.add_feature(cfeature.LAKES, facecolor="aqua",edgecolor="aqua")
    ax.add_feature(cfeature.RIVERS, facecolor="blue", edgecolor="aqua")

    # lat_lon is dictionary of {place: (lat,lon)}
    for place, (lat, lon) in lat_lon.items():
        ax.scatter(lon, lat, transform=ccrs.PlateCarree(), marker='o', color='r')
        ax.text(lon, lat, place, transform=ccrs.PlateCarree(), size=12,
                    ha='right', va='bottom', color='blue')

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

def visualize_station_locations(meta_df, towns, extent, only_stids=None, stid_name=False):
    """
    Visualize station locations on a map.

    Args:
        meta_df (pd.DataFrame): Metadata dataframe containing station information.
        towns (dict): Dictionary of towns with their coordinates.
        extent (list): List of extents for the map [west, east, south, north].
        only_stids (list, optional): List of station IDs to plot. If None, plot all stations.
        stid_name (bool, optional): Annotate the stid string by each scatter point. Default is False.

    """
    fig = plt.figure(figsize=(12, 9))
    ax = plt.axes(projection=ccrs.PlateCarree())

    lats = []
    lons = []
    elevs = []
    stids = []

    for stid in meta_df.columns:
        if only_stids is None or stid in only_stids:
            # Convert to meters
            elevs.append(meta_df[stid].loc["ELEV_DEM"] * 0.304)
            lats.append(meta_df[stid].loc["latitude"])
            lons.append(meta_df[stid].loc["longitude"])
            stids.append(stid)

    sc = ax.scatter(lons, lats, c=elevs, transform=ccrs.PlateCarree())
    cbar = fig.colorbar(sc, orientation='horizontal', pad=0.01)

    # Annotate stid string by each scatter point if stid_name is True
    if stid_name:
        for lon, lat, stid in zip(lons, lats, stids):
            ax.text(lon, lat, stid, transform=ccrs.PlateCarree(), fontsize=8)

    # Add reference towns in RED
    for town, latlon in towns.items():
        ax.scatter(latlon[1], latlon[0], color='red', transform=ccrs.PlateCarree())
        ax.text(latlon[1], latlon[0], town, color='red', transform=ccrs.PlateCarree())

    ax.add_feature(cfeature.STATES.with_scale("10m"))
    ax.add_feature(cfeature.RIVERS.with_scale("10m"))

    ax.set_extent(extent)  # set extents
    plt.show()

def plot_meteogram(df_dict, vrbl_col, title=None, fig=None, ax=None,
                        fill_union=False, plot_ensemble_mean=False,
                        do_legend=False):
    """Plot meteogram for ensemble forecasts with inch markers.

    Args:
        df_dict (dict): Dictionary of dataframes containing ensemble member data
            in format {'ensemble_name': dfXX} where XX is in [1,30].
        vrbl_col (str): Column name for the variable to plot.
        title (str, optional): Title of the plot. Defaults to None.
        fig (matplotlib.figure.Figure, optional): Figure object. Defaults to None.
        ax (matplotlib.axes.Axes, optional): Axes object. Defaults to None.

    Returns:
        tuple: (matplotlib.figure.Figure, matplotlib.axes.Axes)
    """
    # Initialize plot if not provided
    if (fig is None) and (ax is None):
        fig, ax = plt.subplots(figsize=(13, 6))

    # Unit conversation - TODO use pint and metpy?
    vrbl_factors = {
        'prmsl': 0.01,  # Pa to hPa
        'sde': 1,  # values already converted to mm upstream
    }

    for k, v in df_dict.items():
        df_dict[k][vrbl_col] = v[vrbl_col] * vrbl_factors.get(vrbl_col, 1)

    # Compute global min/max using vectorized operations
    all_values = pd.concat([df[vrbl_col] for df in df_dict.values()])
    all_values = all_values.replace([np.inf, -np.inf], np.nan).dropna()
    if all_values.empty:
        ax.text(
            0.5,
            0.5,
            "No finite values available",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=12,
        )
        ax.set_axis_off()
        return fig, ax
    y_min = all_values.min()
    y_max = all_values.max()

    if vrbl_col == 'mslp':
        y_min -= 5  # Add 5 hPa to the minimum
        y_max += 5  # Add 5 hPa to the maximum

    delta = None
    if np.isclose(y_max, y_min):
        # Expand a flat line slightly so matplotlib can set limits.
        delta = max(abs(y_max) * 0.1, 1.0)
        y_min -= delta
        y_max += delta

    # Calculate dynamic grid interval based on the range of y values
    y_range = y_max - y_min
    grid_interval = y_range / 10 if y_range != 0 else (delta or 1.0)

    # Round to nearest grid interval for cleaner limits
    y_min = np.floor(y_min / grid_interval) * grid_interval
    y_max = np.ceil(y_max / grid_interval) * grid_interval

    # Plot ensemble members with optimized color assignment
    colors = generate_color_dict(list(df_dict.keys()))
    for member_name, df_ in df_dict.items():
        ax.plot(df_[vrbl_col].index, df_[vrbl_col],
                label=member_name, color=colors[member_name],
                linewidth=0.75, alpha=0.75)

    # Set primary y-axis properties
    ax.set_ylim(y_min, y_max)

    # Let Matplotlib decide the tick locations
    ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=10))

    if vrbl_col == 'sde':
        ax = add_inch_markers_and_labels(ax, y_min, y_max)
    elif vrbl_col == 'prmsl':
        ax = add_pressure_labels(ax)
    elif vrbl_col == "si10":
        # Add second x-axis with wind speed in mph
        ax = add_wind_labels(ax, y_min, y_max)
    elif vrbl_col == "t2m":
        ax = add_temperature_labels(ax, y_min, y_max)

    else:
        pass

    # Configure axes labels and title
    ax.set_xlabel("Time")

    if plot_ensemble_mean:
        # TODO - clustering and k number of clusters as variable
        ax = add_average(ax, df_dict, vrbl_col, average="mean",
                            # multiplier=vrbl_factors.get(vrbl_col, 1)
                                )

    # TODO plot 10th and 90th percentiles

    # Add a vertical faint gray line on each Monday and Friday on the plot.
    # Colour-fill with a lighter grey between the lines denoting the working week
    # Annotate Mon and Fri on the x-axis at the top in small font
    # next to the vertical lines

    # Extract date range from the first ensemble member's data
    dates = next(iter(df_dict.values())).index

    ax = add_weekday_annotations(ax, dates)

    vrbl_nice = Lookup().find_vrbl_keys(vrbl_col)['label']
    ax.set_ylabel(f"{vrbl_nice}")
    ax.set_title(title, pad=14)

    # Add top x-axis with forecast hour labels
    ax = add_forecast_hour_axis(ax, df_dict)

    # if fill_union:
    #     ax = fill_meteogram_union(ax, df_dict)

    # Add text at the bottom left of the plot with this string:
    bottom_text = "Weekday periods are shaded in light gray."
    ax.text(0.01, 0.01, bottom_text,
            transform=ax.transAxes, fontsize=8, color='black')

    if do_legend:
        # Adjust layout to make space for the legend
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.92, box.height])
        ax.legend(title="Ensemble member", loc='center left',
                    bbox_to_anchor=(1, 0.5), frameon=True, framealpha=0.5,
                    fontsize=7)

    plt.tight_layout()
    return fig, ax

def smoothing_spiky_solar(df, vrbl_col='sdswrf', window=3, *args, **kwargs):
    # Make new dataframe with same timestamps (row index) as original
    # The column will be representative value for each day of variable vrbl_col
    # Here we take the 90th percentile of each station's daily maximum insolation value
    df_repr = df.groupby(df.index.date)[vrbl_col].quantile(0.9)

    # Then we smooth this time series with a rolling mean (size = window)
    # Then interpolate from this curve the values that match the original timestamps
    smoothed = df_repr.rolling(window=window, center=True)#.mean()
    return smoothed.values

def add_average(ax, df_dict, vrbl_col, average="median", multiplier=1):
    """Add the average of all ensemble members' time series to the plot.

    This will be a black thicker line. The "average" can be mean, median...

    To do:
    * Add clustering rather than averages with variable "k" number of clusters

    Args:
        ax (matplotlib.axes.Axes): The axes object to add the average to.
        df_dict (dict): Dictionary of dataframes containing ensemble member data.
        average (str): The type of average to calculate. Defaults to "median".

    Returns:
        matplotlib.axes.Axes: The axes object with the average plotted
    """
    func_dict = {
        "mean": np.nanmean,
        "median": np.nanmedian,
        "solar_repr": smoothing_spiky_solar,
    }
    ave_func = func_dict[average]

    # Turn dictionary into 2D array (time, member) so we can take average over
    # ensemble dimension with value for each of the same times (df indices/rows)

    members = list(df_dict.keys())
    n_members = len(members)
    arbitrary_df = df_dict[members[0]]
    n_times = len(arbitrary_df.index)

    # Create a 2D array to put these values in
    ensemble_values = np.zeros((n_times, n_members))

    # Put the data dictionary into the array
    for i, member in enumerate(members):
        # The multiplier is for unit conversion - better to use pint and metpy
        ensemble_values[:, i] = df_dict[member][vrbl_col].values # * multiplier

    # Calculated the average per time step (over ensemble members)
    # Average will go in a new dataframe "ave_df".
    # Each row is a timestamp (index) same range as in arbitrary_df
    ave_df = pd.DataFrame(ave_func(ensemble_values, axis=1),
                                index=arbitrary_df.index)

    # Plot the average
    ax.plot(df_dict[list(df_dict.keys())[0]].index, ave_df,
                    color='black', lw=2, label=average)
    return ax

def add_wind_labels(ax, y_min, y_max):
    """Wnd speed labelling with mph markers.

    Args:
        ax (matplotlib.axes.Axes): The axes object to modify

    Returns:
        matplotlib.axes.Axes: Modified axes with enhanced wind speed labeling
    """
    mph_conversion = 2.23694  # m/s to mph conversion factor

    # Convert min/max to mph
    min_mph = y_min * mph_conversion
    max_mph = y_max * mph_conversion

    wind_values = np.arange(
        np.floor(min_mph),
        np.ceil(max_mph) + 1,
        1 if max_mph < 9 else 2 if max_mph < 20 else 5,
        dtype=int
    )

    # Convert back to meters for plotting
    mph_positions = wind_values / mph_conversion

    for pos in mph_positions:
        if pos < y_min or pos > y_max:
            continue

        mph = int(round(pos * mph_conversion, 0))
        if mph == 0:
            # Don't bother labelling "zero"!
            continue

        ax.axhline(y=pos, color='blue', linestyle='-', alpha=0.1, zorder=1)
        label = f"{mph} mph"
        ax.text(0.02, pos, label, transform=ax.get_yaxis_transform(),
                ha='left', va='top', fontsize=8, color='blue')
    return ax

def add_temperature_labels(ax, y_min, y_max):
    y_gap = abs(y_max - y_min)
    # We want to mark round Fahrenheit temperatures on the y-axis for ease
    temp_c_positions = np.arange(
        np.floor(y_min),
        np.ceil(y_max) + 1,
        1 if y_gap < 5 else 2 if y_gap < 10 else 3 if y_gap < 16 else 5,
        dtype=int
    )

    for pos in temp_c_positions:
        if pos < y_min or pos > y_max:
            continue

        # TODO - make this more elegant with pint package
        temp_f = int(round(pos * 9/5 + 32, 0))

        ax.axhline(y=pos, color='blue', linestyle='-', alpha=0.1, zorder=1)
        label = f"{temp_f} degF"
        ax.text(0.02, pos, label, transform=ax.get_yaxis_transform(),
                ha='left', va='top', fontsize=8, color='blue')

    # Add line for freezing
    ax.axhline(y=0, color='red', linestyle='-.', alpha=0.15, zorder=1)

    return ax


def add_forecast_hour_axis(ax, df_dict):
    """Add forecast hour axis with ticks for every forecast row/index date and labels every 12 hours.

    Args:
        ax (matplotlib.axes.Axes): The axes object to add the forecast hour axis to.
        df_dict (dict): Dictionary of dataframes containing ensemble member data.
    """
    first_df = next(iter(df_dict.values()))
    # This only works if the first forecast hour in df is 0
    # TODO ensure this! Also how to fix below
    # forecast_transition = first_df.index[first_df['fxx'] == 240][0]
    # forecast_transition = first_df.index[first_df['fxx'] == 240]
    forecast_transition = first_df.index[first_df['fxx'] == 240]
    if len(forecast_transition) > 0:
        ax.axvline(x=forecast_transition[0], color='grey', linestyle='--')
    # ax.axvline(x=forecast_transition, color='grey', linestyle='--')

    # Label this transition with a text annotation "10 days: coarser resolution"
    day10_note = "    10 days: coarser resolution hereon.   "
    ax.text(forecast_transition[0], 1-0.035, day10_note,
                transform=ax.get_xaxis_transform(), ha='left', va="center",
                fontsize=8, color='darkgray')# pad=1)

    secax = ax.secondary_xaxis('top')
    secax.set_xlabel("Forecast hour (hr)")
    secax.set_xticks(first_df.index)

    # Set labels only for every 12 hours
    labels = [str(fx) if fx % 12 == 0 else
              '' for fx in first_df['fxx']]
    secax.set_xticklabels(labels, rotation=45, ha='right')
    secax.tick_params(axis='x', colors='red')
    return ax

def add_weekday_annotations(ax, dates):
    """Add vertical lines and labels for Mondays and Fridays, and fill working week periods.

    Args:
        ax (matplotlib.axes.Axes): The axes object to add the annotations to.
        dates (pd.DatetimeIndex): The date range of the data.
    """
    # for hour, use init hour
    init_hour = dates[0].hour
    # Identify Mondays and Fridays at noon within the date range
    mondays = [date for date in dates if date.weekday() == 0 and
                        date.hour == init_hour]
    fridays = [date for date in dates if date.weekday() == 4 and
                        date.hour == init_hour]

    # Add vertical lines for Mondays and Fridays
    for monday in mondays:
        ax.axvline(x=monday, color='gray', alpha=0.3, linestyle='-', zorder=1)
        ax.text(monday, 0.97, 'Mon', transform=ax.get_xaxis_transform(),
                ha='left', va='bottom', fontsize=8, color='gray')

    for friday in fridays:
        ax.axvline(x=friday, color='gray', alpha=0.3, linestyle='-', zorder=1)
        ax.text(friday, 0.97, 'Fri', transform=ax.get_xaxis_transform(),
                ha='left', va='bottom', fontsize=8, color='gray')

    # Fill working week periods with light gray
    start_date = dates[0]
    end_date = dates[-1]

    # Handle start of time series
    if not mondays or start_date < mondays[0]:
        # If start date is before first Monday, or there are no Mondays
        next_friday = next((friday for friday in fridays if friday > start_date), None)
        if next_friday:
            ax.axvspan(start_date, next_friday, color='gray', alpha=0.08, zorder=0, hatch='//')

    # Handle middle weeks
    for monday in mondays:
        next_friday = next((friday for friday in fridays if friday > monday), None)
        if next_friday:
            ax.axvspan(monday, next_friday, color='gray', alpha=0.08, zorder=0, hatch='//')

    # Handle end of time series
    if mondays:
        last_monday = mondays[-1]
        next_friday = next((friday for friday in fridays if friday > last_monday), None)
        if not next_friday and end_date > last_monday:
            # If there's no next Friday but we have data past the last Monday
            ax.axvspan(last_monday, end_date, color='gray', alpha=0.08, zorder=0, hatch='//')

    return ax

def add_inch_markers_and_labels(ax, y_min, y_max):
    """Add inch markers and labels to the plot.

    Args:
        ax (matplotlib.axes.Axes): The axes object to add the markers and labels to.
        y_min (float): The minimum y-axis value.
        y_max (float): The maximum y-axis value.
    """
    millimeters_per_inch = 25.4

    # Convert min/max (in mm) to inches
    min_inches = y_min / millimeters_per_inch
    max_inches = y_max / millimeters_per_inch

    # Determine if we need quarter-inch or whole-inch markers
    if max_inches <= 1.5:
        # Use quarter inches
        inch_values = np.arange(
            np.floor(min_inches * 4) / 4,  # Round down to nearest quarter
            np.ceil(max_inches * 4) / 4 + 0.25,  # Round up to nearest quarter
            0.25  # Quarter inch steps
        )
        decimal_places = 2  # Show 2 decimal places for fractions
    else:
        # Use whole inches
        inch_values = np.arange(
            np.floor(min_inches),
            np.ceil(max_inches) + 1
        )
        decimal_places = 0  # Show whole numbers

    # Convert back to meters for plotting
    inch_positions = inch_values * millimeters_per_inch

    for pos in inch_positions:
        if pos < y_min or pos > y_max:
            continue

        inches = round(pos / millimeters_per_inch, decimal_places)
        if inches == 0:
            # Don't bother labelling "zero"!
            continue

        ax.axhline(y=pos, color='blue', linestyle='-', alpha=0.1, zorder=1)
        label = f"{inches} inch{'es' if inches != 1 else ''}"
        ax.text(0.02, pos, label, transform=ax.get_yaxis_transform(),
                ha='left', va='top', fontsize=8, color='blue')

    return ax

def add_pressure_labels(ax):
    pressures = [
        (1040, "Strong high pressure", 'darkgreen'),
                    (1030, "High pressure", 'green'),
                    (1015, "Average pressure", 'black'),
                    (1000, "Low pressure", 'red'),
                    (990, "Strong low pressure", 'darkred'),
        ]

    for value, label, color in pressures:
        # Only plot if within the data range
        if not (ax.get_ylim()[0] < value < ax.get_ylim()[1]):
            continue
        ax.axhline(y=value, color=color, linestyle='-', alpha=0.1, zorder=1)
        ax.text(0.02, value, label, verticalalignment='center',
                color=color, fontsize=8,
                transform=ax.get_yaxis_transform(),
                ha='left', backgroundcolor='white')
    return ax

def generate_color_dict(member_names,
                            color_map='tab20',
                            # color_map='Pastel1',
                            alpha=0.65):
    """
    Generate a dictionary mapping member names to colors.

    Args:
    - member_names (list): List of member names.
    - color_map (str): Name of the matplotlib colormap.
    - alpha (float): Transparency level for the colors.

    Returns:
    - dict: A dictionary mapping member names to RGBA colors.
    """
    cmap = plt.get_cmap(color_map)
    colors = cmap(np.linspace(0, 1, len(member_names)))
    color_dict = {member: (*color[:3], alpha) for member, color in zip(
        member_names, colors)}
    return color_dict

def get_member_color(member_name, color_dict):
    """
    Get the color for a specific member from the color dictionary.

    Args:
    - member_name (str): The name of the member.
    - color_dict (dict): Dictionary mapping member names to colors.

    Returns:
    - tuple: RGBA color for the member.
    """
    # Default to black if not found
    return color_dict.get(member_name, (0, 0, 0, 1))

def __fill_meteogram_union(ax, df_dict):
    """Fill the union (maximum) of the time series over all members per fxx.

    Shade this area in a part-transparent cyan color to indicate upper bound.

    Args:
        ax (matplotlib.axes.Axes): The axes object to add the fill to.
        df_dict (dict): Dictionary of dataframes containing ensemble member data.
    """
    raise NotImplementedError("This function is not yet implemented.")
    # Compute max for set of row (time) in column fxx from each ensemble member.
    max_df = pd.concat(df_dict.values(), axis=1).max(axis=1)
    ax.fill_between(max_df.index, max_df, color='cyan', alpha=0.1)
    return ax
