"""Plotting images related to Clyfar and fuzzy-logic inference systems.
"""

import os

import numpy as np
import matplotlib.pyplot as plt

def style_axes(ax):
    """Apply common styling to the axes."""
    ax.spines['top'].set_color('#D3D3D3')  # light grey
    ax.spines['right'].set_color('#D3D3D3')  # light grey
    ax.spines['bottom'].set_linewidth(0.8)  # thinner axis lines
    ax.spines['left'].set_linewidth(0.8)

    # Make axes ticks use Helvetica font
    for tick in ax.get_xticklabels():
        tick.set_fontname("Helvetica")

    for tick in ax.get_yticklabels():
        tick.set_fontname("Helvetica")

    return ax

def plot_mf(ax, x, y, label=None, line_color="#4B0082", plot_fill=False, linestyle='-'):
    """Plot a membership function on a given axis.

    Args:
        ax (matplotlib.axes.Axes): The axis to plot the membership function on.
        x (np.ndarray): The universe of discourse (x-axis).
        y (np.ndarray): The membership function values (y-axis).
        label (str): The label for the membership function.
        line_color (str): The color of the line.
        plot_fill (bool): Whether to fill under the curve.
        linestyle (str): The line style to use (see matplotlib)

    Returns:
        ax (matplotlib.axes.Axes): The axis with the membership function plotted.

    """
    style_axes(ax)

    # Ensure y is at least 1-dimensional
    y = np.atleast_1d(y)

    # Check if there's only one non-zero value in y
    # TODO - if any vertical lines (right-angle triangle) this should also have a delta function
    if np.count_nonzero(y) == 1:
        idx = np.atleast_1d(np.nonzero(y))[0]
        ax.axvline(x=x[idx], color=line_color, linestyle='--', alpha=0.6)
        ax.set_xlim(x[0], x[-1])
        # Add a large circle at the value of y to show the limit
        # Plot over the axes lines so it is clear
        ax.plot(x[idx], y[idx], 'o', color=line_color, markersize=10,
                zorder=10, label='Singleton', linestyle=linestyle)
    else:
        ax.plot(x, y, color=line_color, linewidth=2, label=label, linestyle=linestyle)
        if plot_fill:
            # Fill under the curve with a hatched line_color
            ax.fill_between(x, 0, y, alpha=0.3, color=line_color, hatch='//')
    ax.set_ylim(-0.01,1.01)
    ax.legend()
    return ax

def defuzzify_percentiles(x_uod, y_agg, percentiles=None,
                          do_plot=False, plot_fill=False, save_path=None):
    """Defuzzify the aggregated membership function to specific percentiles."""
    if percentiles is None:
        percentiles = [10, 50, 90]
    total_area = np.trapz(y_agg, x_uod)
    cumulative_area = np.cumsum((y_agg[:-1] + y_agg[1:]) / 2 * np.diff(x_uod))
    cumulative_area_normalized = cumulative_area / total_area

    percentile_results = {}
    for p in percentiles:
        idx = np.where(cumulative_area_normalized >= p / 100.0)[0]
        if idx.size > 0:
            percentile_results[f'{p}th percentile'] = x_uod[idx[0]]
        else:
            percentile_results[f'{p}th percentile'] = x_uod[-1]

    if do_plot:
        fig, ax = plt.subplots(1, figsize=(8, 6))
        ax.plot(x_uod, y_agg, color='#4B0082', linewidth=2)
        for p in percentiles:
            ax.axvline(x=percentile_results[f'{p}th percentile'], color='grey', linestyle='--', alpha=0.6)
        ax.set_title('Defuzzified Percentiles', fontsize=14)
        ax.set_xlabel('Ozone (ppb)', fontsize=12)
        ax.set_ylabel('Degree of membership μ', fontsize=12)
        ax.set_ylim(-0.02, 1.02)
        ax.axhline(y=1, color='grey', linestyle='--', alpha=0.7)
        ax.axhline(y=0, color='grey', linestyle='--', alpha=0.7)
        ax.grid(False)
        style_axes(ax)


        if plot_fill:
            ax.fill_between(x_uod, 0, y_agg, alpha=0.4, facecolor='#4B0082', hatch='//')

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            plt.close()
        else:
            plt.show()

    return percentile_results

def make_mf_figure(x_uod, mf_arrays, plot_union=False, plot_intersection=False,
                   plot_colors=None, return_aggregated=False, save_path="mf_figure.pdf"):
    """Create a figure for multiple membership functions.

    Args:
        x_uod (np.ndarray): Universe of discourse for the x-axis.
        mf_arrays (dict): Dictionary of {shape: membership function}.
        plot_union (bool): Whether to plot the union of the membership functions.
        plot_intersection (bool): Whether to plot the intersection of the membership functions.
        plot_colors (dict): Dictionary of {shape: color} for the line colors.
        return_aggregated (bool): Whether to return the aggregated membership function.
        save_path (str): Path to save the figure to.

    Returns:
        fig (matplotlib.figure.Figure): The figure object.
        ax (matplotlib.axes.Axes): The axis object.
        y_union (np.ndarray): The aggregated membership function if requested.

    """
    fig, ax = plt.subplots(1)
    ax = style_axes(ax)
    ys = []

    for shape, y_ in mf_arrays.items():
        print(shape)
        lc = plot_colors.get(shape, '#4B0082') if plot_colors else '#4B0082'
        plot_mf(ax, x_uod, y_, label=shape, line_color=lc)
        ys.append(y_)

    if plot_union:
        y_union = np.maximum.reduce(ys)
        plot_mf(ax, x_uod, y_union, label="Union", line_color="black", linestyle='--')
        ax.fill_between(x_uod, 0, y_union, facecolor="grey", alpha=0.3, hatch='//')

        if return_aggregated:
            # plt.savefig(save_path, bbox_inches='tight')
            # plt.close()
            return fig, ax, y_union

    if plot_intersection:
        y_intersection = np.minimum.reduce(ys)
        plot_mf(ax, x_uod, y_intersection, label="Intersection", line_color="black", linestyle='--')
        ax.fill_between(x_uod, 0, y_intersection, facecolor="grey", alpha=0.3, hatch='//')
        if return_aggregated:
            # plt.savefig(save_path, bbox_inches='tight')
            # plt.close()
            return fig, ax, y_intersection

    plt.tight_layout()
    # plt.savefig(save_path, bbox_inches='tight')
    # plt.close()
    if return_aggregated:
        return fig, ax, None
    return fig, ax

def plot_all_categories(ax, variable, line_colors=None, plot_fill=True):
    """Plot all categories of a given variable on a given axis.

    TODO: remove skfuzzy code

    Args:
        ax (matplotlib.axes.Axes): The axis to plot the membership functions on.
        variable (skfuzzy.control.Antecedent or skfuzzy.control.Consequent): The variable with categories to plot.
        line_colors (dict, optional): Dictionary for line colors in format {label: color}. Defaults to None.
        plot_fill (bool, optional): Whether to fill under the curves. Defaults to False.

    Returns:
        ax (matplotlib.axes.Axes): The axis with the membership functions plotted.
    """
    # if line_colors is None:
    #     line_colors = [None] * len(variable.terms)

    for label, term in variable.terms.items():
        print(label, term)
        color = line_colors[label] if line_colors is not None else None
        ax = plot_mf(ax, variable.universe, term.mf, label=label, line_color=color, plot_fill=plot_fill)

        # Special markers for ozone levels
        if label == "ozone":
            ax.axvline(x=40, color=fave_color, linestyle='--', alpha=0.6)
            ax.axvline(x=70, color=fave_color, linestyle='--', alpha=0.6)

    return ax

