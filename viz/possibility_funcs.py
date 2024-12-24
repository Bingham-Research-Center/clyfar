"""Functions to visualise the possibility distribution predicted by the FIS in this version of Clyfar.
"""

import os

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors


def plot_possibility_heatmap(possibility_df):
    pass

def plot_possibility_bar_timeseries(df):
    """For time series dataframe, plot possibilities as bars.

    The format of the data frame has rows as dates (index is time stamp),
    columns has values like weather variables, possibilities etc.
    """
    # Create the figure and the first axis
    fig, ax1 = plt.subplots(figsize=(10, 6), dpi=300)

    # Plot the forecast and observed ozone concentration on the first axis
    ax1.plot(df['ozone_10pc'], label='10pc')
    ax1.plot(df['ozone_50pc'], label='50pc')
    ax1.plot(df['ozone_90pc'], label='90pc')

    # Add horizontal lines for NAAQS limit and typical background
    ax1.axhline(y=70, color='magenta', linestyle=':', linewidth=1.5, label='NAAQS for Ozone', zorder=2)
    ax1.axhline(y=40, color='k', linestyle=':', linewidth=1.5, label='Typical Background', zorder=2)

    # Set the first axis labels and limits
    ax1.set_ylabel('Ozone Concentration (ppb)', fontsize=10)
    ax1.set_xlabel('Date of year', fontsize=10)
    # ax1.set_ylim(28, 75)
    # ax1.legend(loc='center left', fontsize=10)

    # Create the second y-axis and plot the bars
    ax2 = ax1.twinx()
    ax2.bar(df.index, df['extreme'], color='red', alpha=0.99, label='Possibility of Extreme Ozone', zorder=4)
    ax2.bar(df.index, df['elevated'], color='green', alpha=0.45, label='Possibility of Elevated Ozone', zorder=3)
    ax2.bar(df.index, df['moderate'], color='orange', alpha=0.3, label='Possibility of Moderate Ozone', zorder=2)
    ax2.bar(df.index, df['background'], color='blue', alpha=0.2, label='Possibility of Background Ozone', zorder=1)

    # Set the second axis labels and limits
    ax2.set_ylabel('Membership', fontsize=10)
    ax2.set_ylim(0, 1)

    # Add thick black lines with solid arrows for specific dates
    # dates = ['2022-02-27', '2022-01-02', '2021-12-14']
    # date_labels = ['27 Feb', '2 Jan', '14 Dec']
    # for date, label in zip(dates, date_labels):
    #     date_timestamp = pd.Timestamp(date)
    #     ax1.annotate('', xy=(date_timestamp, 70), xytext=(date_timestamp, 75),
    #                  arrowprops=dict(facecolor='black', shrink=0.05, width=5, headwidth=10))
    #     ax1.text(date_timestamp, 75.5, label, ha='center', fontsize=10)

    # Add legends for both axes
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper center', fontsize=10, facecolor='white')

    # Set x-axis labels as "XX mmm YY"
    # XX is the day, mmm is the 3-letter abbreviated months, and YY is the last two digits of year
    # Set x-axis labels as "XX mmm YY" with appropriate spacing
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    # ax1.xaxis.set_minor_locator(mdates.DayLocator(bymonthday=(1, 15)))
    ax1.xaxis.set_minor_locator(mdates.DayLocator(bymonthday=range(1, 34, 7)))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d %b %y'))

    # Rotate the x-axis labels for better readability
    plt.setp(ax1.get_xticklabels(), rotation=45, ha='right', fontsize=10)

    plt.grid(False, which='both')

    # Display the plot
    plt.show()

    return fig, (ax1, ax2)

def plot_ozone_heatmap(df):
    """For time series dataframe, plot ozone categories as a heatmap.

    The format of the data frame has rows as dates (index is time stamp),
    columns containing the possibility values for each category.
    Categories are plotted from bottom to top: background, moderate, elevated, extreme,
    each with its own colorblind-friendly color.
    """
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 3), dpi=300)

    # Define colorblind-friendly colors for each category
    category_colors = {
        'background': '#2b8cbe',  # Blue
        'moderate': '#f16913',    # Orange
        'elevated': '#fec44f',    # Yellow
        # 'extreme': '#de2d26'      # Red
        'extreme': '#6a0dad',      # Purple
    }

    categories = ['background', 'moderate', 'elevated', 'extreme']

    # Create a 2D array where rows are categories and columns are timestamps
    heatmap_data = np.array([df[cat].values for cat in categories])

    # Create meshgrid for plotting
    x = np.arange(len(df.index))
    y = np.arange(len(categories))
    X, Y = np.meshgrid(x, y)

    # Create a custom colormap for each category
    for i, category in enumerate(categories):
        mask = np.zeros_like(heatmap_data, dtype=bool)
        mask[i, :] = True

        # Plot each row with its own color
        im = ax.pcolormesh(X, Y,
                           np.where(mask, heatmap_data, np.nan),
                           cmap=mcolors.LinearSegmentedColormap.from_list('',
                                                                          ['white', category_colors[category]]),
                           vmin=0, vmax=1,
                           shading='auto')

    # Customize axes
    # ax.set_yticks(np.arange(len(categories)))
    # ax.set_yticklabels(categories)

    # Set x-axis ticks and labels
    tick_locations = np.arange(0, len(df.index), len(df.index)//8)
    ax.set_xticks(tick_locations)
    ax.set_xticklabels([df.index[i].strftime('%d %b %y') for i in tick_locations],
                       rotation=45, ha='right')

    # Add colorbar
    # cbar = plt.colorbar(im)
    # cbar.set_label('Possibility Value', rotation=270, labelpad=15)

    # Labels and title
    ax.set_xlabel('Date')
    ax.set_ylabel('Ozone Categories')
    plt.title('Ozone Category Possibilities Over Time')

    ax.grid(True, which='major', axis='y', linestyle='-',
                    color='grey', alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(False)  # Make grid appear above the heatmap
    ax.set_yticks(np.arange(len(categories) + 1) - 0.5)  # Grid lines between categories
    ax.set_yticks(np.arange(len(categories)), minor=True)  # Category labels in center
    ax.set_yticklabels(categories, minor=True)  # Put labels on minor ticks
    ax.set_yticklabels([], minor=False)  # Hide major tick labels
    ax.tick_params(axis='y', which='both', length=0)  # Hide y-axis ticks


    # Add faint vertical grey line for 10 days (240 hours) into the forecast
    xpos = int(240/3)
    ax.axvline(x=xpos, color='grey', linestyle='--', alpha=0.6)
    # Annotate at the top of the axis to the right of 10 days with note
    ax.text(xpos, len(category_colors.keys()),
                    "10 days: coarser resolution hereon.", ha='left',
                    va='top', fontsize=8, color='darkgray')

    # Adjust layout
    plt.tight_layout()
    return fig, ax

def plot_percentile_meteogram(df, fig=None, ax=None,
                                transition_hour=240):
    if fig is None:
        fig,ax = plt.subplots(figsize=(10, 5))

    # Define the maroon/purple color for the example lines
    fave_color = '#4B0082'

    pc_colors = {
        # 10th percentile, low estimate of ozone, "green"
        10: '#00FF7F',
        # 50th percentile, middle estimate of ozone, "orange"
        50: '#FFA07A',
        # 90th percentile, high estimate of ozone, "red"
        90: '#FF6347',
    }

    # Plot best-, average-, and worst-case scenarios (10th, 50th, 90th percentiles)
    # Use plot colours defined in pc_colors
    ax.plot(df.index, df['ozone_10pc'], label="Optimistic (10th pc)",
            color=pc_colors[10], lw=1)
    ax.plot(df.index, df['ozone_50pc'], label="Neutral (50th pc)",
            color=pc_colors[50], lw=1)
    ax.plot(df.index, df['ozone_90pc'], label="Pessimistic (90th pc)",
            color=pc_colors[90], lw=1)

    # Shade between the 10th and 90th with a very faint fave_color
    ax.fill_between(df.index, df['ozone_10pc'], df['ozone_90pc'],
                    color=fave_color, alpha=0.2)

    # Label this is Clyfar ozone hindcasts for 2021/2022, perfect inputs (obs)
    # x-axis is date, y-axis is ozone concentration (ppb)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Ozone Concentration (ppb)", fontsize=12)
    ax.set_title(f"Clyfar Ozone Predictions", fontsize=14)
    ax.set_ylim(20, 140)

    # Mark horizontal line at 70 ppb as grey dashed line in background (low z order)
    ax.axhline(y=70, color='grey', linestyle='--', alpha=0.6, zorder=0)

    # What x-axis value corresponds to transition_hour?
    # if isinstance(transition_hour,int):
    #     forecast_transition = df.index[transition_hour]

    # day10_note = "    10 days: coarser resolution hereon.   "
    # ax.text(forecast_transition[0], 0.035, day10_note,
    #     transform=ax.get_xaxis_transform(), ha='left', va='top',
    #     fontsize=8, color='darkgray')# pad=1)

    ax.legend()
    plt.show()
    return fig,ax
