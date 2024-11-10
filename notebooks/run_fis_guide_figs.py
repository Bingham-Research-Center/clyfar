# Created from notebook with help from GPT-4o mini!

import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

plt.switch_backend('pdf')

# Constants and Options
plt.rc('text', usetex=False)
plt.rc('font', family='Helvetica')
plt.rcParams['figure.dpi'] = 350

# Define consistent colors
LINE_COLOR = '#4B0082'  # Maroon/Purple
MY_COLORS = [
    '#FFA07A', '#20B2AA', '#778899', '#FF6347', '#4682B4',
    '#FFD700', '#8A2BE2', '#00FF7F', '#FF4500', '#00FFFF'
]

OZONE_CATEGORIES = {
    "background": "#6CA0DC",
    "elevated": "#FF8C00",
    "extreme": "#FF6F61"
}

def style_axes(ax):
    """Apply common styling to the axes."""
    ax.spines['top'].set_color('#D3D3D3')  # Light grey
    ax.spines['right'].set_color('#D3D3D3')  # Light grey
    ax.spines['bottom'].set_linewidth(0.8)  # Thinner axis lines
    ax.spines['left'].set_linewidth(0.8)

    # Set Helvetica font for tick labels
    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontname("Helvetica")

    return ax

def piecewise_linear_sigmoid(x_uod, midpoint, width, height, direction="increasing"):
    """Piecewise linear approximation of a sigmoid function."""
    y = np.zeros_like(x_uod, dtype=float)
    left = midpoint - width / 2
    right = midpoint + width / 2

    if direction == "increasing":
        y[(x_uod >= left) & (x_uod <= right)] = height * (x_uod[(x_uod >= left) & (x_uod <= right)] - left) / width
        y[x_uod > right] = height
    elif direction == "decreasing":
        y[(x_uod >= left) & (x_uod <= right)] = height * (right - x_uod[(x_uod >= left) & (x_uod <= right)]) / width
        y[x_uod > right] = 0
        y[x_uod < left] = height
    else:
        raise ValueError("Invalid direction. Use 'increasing' or 'decreasing'.")

    return y

def trapz_function(x_uod, m_lower, m_upper, alpha, beta, height):
    """Trapezoidal membership function generator."""
    assert m_lower <= m_upper, "m_lower must be <= m_upper."
    assert alpha >= 0, "alpha must be >= 0."
    assert beta >= 0, "beta must be >= 0."
    assert 0 < height <= 1, "height must be > 0 and <= 1."

    y = np.zeros(len(x_uod), dtype=float)

    if m_lower == m_upper and alpha == beta == 0:
        idx = np.nonzero(x_uod == m_lower)[0]
        y[idx] = height
        return y

    # Lower slope
    idx = np.nonzero((x_uod >= m_lower - alpha) & (x_uod < m_lower))[0]
    y[idx] = height * (x_uod[idx] - (m_lower - alpha)) / alpha

    # Flat top
    idx = np.nonzero((x_uod >= m_lower) & (x_uod <= m_upper))[0]
    y[idx] = height

    # Upper slope
    idx = np.nonzero((x_uod > m_upper) & (x_uod <= m_upper + beta))[0]
    y[idx] = height * (m_upper + beta - x_uod[idx]) / beta

    return y

def plot_step(ax, jump_x=7.5, save_path=None):
    """Plot a step function."""
    x = np.linspace(0, 15, 100)
    y = np.piecewise(x, [x < jump_x, x >= jump_x], [0.0, 1.0])

    ax.plot(x[x < jump_x], y[x < jump_x], color=LINE_COLOR, linewidth=2)
    ax.plot(x[x >= jump_x], y[x >= jump_x], color=LINE_COLOR, linewidth=2)
    ax.axvline(x=jump_x, color=LINE_COLOR, linestyle='--', alpha=0.6)

    ax.set_title('Step function for deep snow cover', fontsize=14)
    ax.set_xlabel('Snow depth (cm)', fontsize=12)
    ax.set_ylabel('Degree of membership μ', fontsize=12)
    ax.set_ylim(-0.2, 1.2)
    ax.set_xlim(5, 10)
    ax.axhline(y=1, color='grey', linestyle='--', alpha=0.6)
    ax.axhline(y=0, color='grey', linestyle='--', alpha=0.6)
    ax.text(8.5, 0.8, 'True', fontsize=10, verticalalignment='center')
    ax.text(6.0, 0.2, 'False', fontsize=10, verticalalignment='center')
    ax.grid(False)
    style_axes(ax)

    if save_path:
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()

def plot_sigmoid(ax, save_path=None):
    """Plot a sigmoid function."""
    x = np.linspace(0, 15, 100)
    y = 1 / (1 + np.exp(-(x - 7.5)))
    ax.plot(x, y, color=LINE_COLOR, linewidth=2)
    ax.axvline(x=7.5, color="black", linestyle='--', alpha=0.6)

    ax.set_title('Sigmoid function for deep snow cover', fontsize=14)
    ax.set_xlabel('Snow depth (cm)', fontsize=12)
    ax.set_ylabel('Degree of membership $μ$', fontsize=12)
    ax.set_ylim(-0.2, 1.2)
    ax.set_xlim(0, 15)
    ax.axhline(y=1, color='grey', linestyle='--', alpha=0.6)
    ax.axhline(y=0, color='grey', linestyle='--', alpha=0.6)
    ax.text(8.3, 0.55, r'More plausibly true $\longrightarrow$', fontsize=10, verticalalignment='center', multialignment='center')
    ax.text(1.0, 0.45, r'$\longleftarrow$ Less plausibly true', fontsize=10, verticalalignment='center', multialignment='center')
    ax.grid(False)
    style_axes(ax)

    if save_path:
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()

def make_binary_figure(shapes=["step", "sigmoid"], save_path="binary_figure.pdf"):
    """Create a figure comparing binary step and sigmoid functions."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    plot_functions = {
        "step": plot_step,
        "sigmoid": plot_sigmoid
    }

    for ax, shape in zip(axes, shapes):
        plot_functions[shape](ax)

    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()
    return fig, axes

def plot_mf(ax, x, y, label=None, line_color=LINE_COLOR, plot_fill=False, linestyle='-'):
    """Plot a membership function on a given axis."""
    style_axes(ax)
    y = np.atleast_1d(y)

    if np.count_nonzero(y) == 1:
        idx = np.nonzero(y)[0][0]
        ax.axvline(x=x[idx], color=line_color, linestyle='--', alpha=0.6)
        ax.plot(x[idx], y[idx], 'o', color=line_color, markersize=10,
                zorder=10, label='Singleton', linestyle=linestyle)
    else:
        ax.plot(x, y, color=line_color, linewidth=2, label=label, linestyle=linestyle)
        if plot_fill:
            ax.fill_between(x, 0, y, alpha=0.4, facecolor=line_color, hatch='//')

    ax.set_ylim(-0.01, 1.01)
    ax.legend()
    return ax

def plot_activation(x_uod, mf_func, y_value, fuzz_color=LINE_COLOR,
                    category_label=None, variable_name="snow depth",
                    vrbl_unit="cm",
                    return_activation_y=False, save_path=None):
    """Plot the activation of a fuzzy set based on input value."""
    fig, ax = plt.subplots(figsize=(8, 6))

    if isinstance(mf_func, np.ndarray):
        y = mf_func
    else:
        raise ValueError("mf_func must be a numpy array.")

    ax.plot(x_uod, y, color=fuzz_color, linewidth=2)
    ax.fill_between(x_uod, np.minimum(y, y_value), facecolor=fuzz_color, alpha=0.4, hatch='//')
    ax.axhline(y=y_value, color='grey', linestyle='--', alpha=0.6)

    ax.set_title(f'Activation of {vrbl_unit} {variable_name} \nCategory: {category_label}', fontsize=14)
    ax.set_xlabel(f'{variable_name} ({vrbl_unit})', fontsize=12)
    ax.set_ylabel('Degree of membership μ', fontsize=12)
    ax.set_ylim(-0.1, 1.1)
    ax.axhline(y=1, color='grey', linestyle='--', alpha=0.7)
    ax.axhline(y=0, color='grey', linestyle='--', alpha=0.7)
    ax.grid(False)
    style_axes(ax)

    if return_activation_y:
        y_return = np.minimum(y, y_value)
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            plt.close()
        return fig, ax, y_return

    if save_path:
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()

    return fig, ax

def defuzzify_percentiles(x_uod, y_agg, percentiles=[10, 50, 90],
                          do_plot=False, plot_fill=False, save_path=None):
    """Defuzzify the aggregated membership function to specific percentiles."""
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
        ax.plot(x_uod, y_agg, color=LINE_COLOR, linewidth=2)
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
            ax.fill_between(x_uod, 0, y_agg, alpha=0.4, facecolor=LINE_COLOR, hatch='//')

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            plt.close()
        else:
            plt.show()

    return percentile_results

def make_mf_figure(x_uod, mf_arrays, plot_union=False, plot_intersection=False,
                   plot_colors=None, return_aggregated=False, save_path="mf_figure.pdf"):
    """Create a figure for multiple membership functions."""
    fig, ax = plt.subplots(1)
    style_axes(ax)
    ys = []

    for shape, y_ in mf_arrays.items():
        lc = plot_colors.get(shape, LINE_COLOR) if plot_colors else LINE_COLOR
        plot_mf(ax, x_uod, y_, label=shape, line_color=lc)
        ys.append(y_)

    if plot_union:
        y_union = np.maximum.reduce(ys)
        plot_mf(ax, x_uod, y_union, label="Union", line_color="black", linestyle='--')
        ax.fill_between(x_uod, 0, y_union, facecolor="grey", alpha=0.3, hatch='//')

        if return_aggregated:
                plt.savefig(save_path, bbox_inches='tight')
                plt.close()
                return fig, ax, y_union

    if plot_intersection:
        y_intersection = np.minimum.reduce(ys)
        plot_mf(ax, x_uod, y_intersection, label="Intersection", line_color="black", linestyle='--')
        ax.fill_between(x_uod, 0, y_intersection, facecolor="grey", alpha=0.3, hatch='//')
        if return_aggregated:
            plt.savefig(save_path, bbox_inches='tight')
            plt.close()
            return fig, ax, y_intersection

    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()
    if return_aggregated:
        return fig, ax, None
    return fig, ax

def normalize_possibility(pi):
    """Normalize a possibility distribution so that max(pi) = 1."""
    pi_normalized = np.copy(pi)
    finite_values = pi[(np.isfinite(pi)) & (pi > 0)]

    if finite_values.size > 0:
        max_value = np.max(finite_values)
        pi_normalized[(np.isfinite(pi)) & (pi > 0)] /= max_value

    return pi_normalized

def plot_possibility(poss_dict, necess_dict=None, colors=None, save_path="possibility_plot.pdf"):
    """Plot the possibility and optionally necessity of each category."""
    fig, ax = plt.subplots(1)
    categories = list(poss_dict.keys())
    values = list(poss_dict.values())
    bar_colors = list(colors) if colors else MY_COLORS[:len(categories)]
    ax.bar(categories, values, color=bar_colors, label='Possibility ($\Pi$')

    if necess_dict:
        necess_values = [necess_dict[cat] for cat in categories]
        ax.bar(categories, necess_values, color=bar_colors, alpha=0.5, hatch='//', label='Necessity')

    ax.set_title('Possibility of Each Category of Ozone', fontsize=14)
    ax.set_ylabel('Possibility', fontsize=12)
    ax.set_ylim(0, 1.1)
    ax.grid(False)
    style_axes(ax)

    if necess_dict:
        possibility_patch = mpatches.Patch(facecolor='none', edgecolor='black', label='Possibility $\Pi$')
        necessity_patch = mpatches.Patch(facecolor='none', edgecolor='black', hatch='//', label='Necessity $N$')
        ax.legend(handles=[possibility_patch, necessity_patch])

    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()

def plot_fuzzification(x_uod, x_value, mf_func="pl_sigmoid", fuzz_color=LINE_COLOR,
                       category_label=None, variable_name="snow depth", vrbl_unit="cm",
                       direction="increasing", xlim=None, save_path=None):
    """Plot the fuzzification of a specific input value."""
    fig, ax = plt.subplots(figsize=(8, 6))

    if isinstance(mf_func, np.ndarray):
        y = mf_func
    elif mf_func == "pl_sigmoid":
        y = piecewise_linear_sigmoid(x_uod, x_value - 1, 4, 1.0, direction=direction)
    elif mf_func == "Trapezium":
        y = trapz_function(x_uod, 5, 10, 2, 2, 0.9)
    else:
        raise ValueError(f"Unknown membership function shape: {mf_func}")

    ax.plot(x_uod, y, color=fuzz_color, linewidth=2)
    ax.axvline(x=x_value, color='grey', linestyle='--', alpha=0.6)

    y_at_intersection = y[np.argmin(np.abs(x_uod - x_value))]
    ax.axhline(y=y_at_intersection, color='grey', linestyle='--', alpha=0.6)

    if direction == "increasing":
        y_combined = np.where(x_uod <= x_value, y, y_at_intersection)
    elif direction == "decreasing":
        y_combined = np.where(x_uod >= x_value, y, y_at_intersection)

    ax.fill_between(x_uod, 0, y_combined, facecolor=fuzz_color, alpha=0.4, hatch='//')

    ax.set_title(f'Fuzzification of {x_value} {vrbl_unit} {variable_name} \nCategory: {category_label}', fontsize=14)
    ax.set_xlabel(f'{variable_name} ({vrbl_unit})', fontsize=12)
    ax.set_ylabel('Degree of membership μ', fontsize=12)
    ax.set_ylim(-0.1, 1.1)
    if xlim:
        ax.set_xlim(xlim)
    ax.axhline(y=1, color='grey', linestyle='--', alpha=0.7)
    ax.axhline(y=0, color='grey', linestyle='--', alpha=0.7)
    ax.grid(False)
    style_axes(ax)

    if save_path:
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()

    return fig, ax

def create_output_dir(directory="fis_guide_figures"):
    """Create a directory to save figures if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory

def main():
    """Main procedure for fuzzy inference."""
    # Create output directory
    output_dir = create_output_dir()

    # Define universe of discourse
    x_uod = np.arange(0, 121, 1)

    # Plot membership functions
    default_mf_arrays = {
        "Trapezium": trapz_function(np.arange(0, 121, 1), 30, 60, 15, 30, 0.8),
        "Piecewise Linear (Sigmoid-like)": piecewise_linear_sigmoid(np.arange(0, 121, 1), 75, 20, 1.0)
    }
    plot_colors = {
        "Trapezium": "#6CA0DC",  # Pastel Medium Blue
        "Piecewise Linear (Sigmoid-like)": "#FF6F61"  # Pastel Medium Red (Color-blind friendly)
    }
    make_mf_figure(
        x_uod, default_mf_arrays, plot_colors=plot_colors,
        save_path=os.path.join(output_dir, "default_mf_figure.pdf")
    )

    # Plot union of membership functions
    make_mf_figure(
        x_uod, default_mf_arrays, plot_union=True, plot_colors=plot_colors,
        save_path=os.path.join(output_dir, "mf_union_figure.pdf")
    )

    # Plot intersection of membership functions
    make_mf_figure(
        x_uod, default_mf_arrays, plot_intersection=True, plot_colors=plot_colors,
        save_path=os.path.join(output_dir, "mf_intersection_figure.pdf")
    )

    # Test trapezoidal function with various sources
    sources = {
        "A": (100, 100, 0, 0, 1),   # Singleton
        "B": (50, 70, 10, 30, 0.9), # Trapezoid
        "C": (100, 110, 0, 0, 1),   # Top hat
        "D": (20, 20, 0, 10, 0.8),  # Right-angled triangle
        "E": (60, 60, 20, 20, 0.5), # Symmetrical triangle
        "F": (50, 20, 0.88)          # Piecewise linear sigmoid
    }

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    for idx, (M, params) in enumerate(sources.items()):
        ax = axes[idx]
        ax.set_title(f"Example Function {M}")

        if M == "F":
            y = piecewise_linear_sigmoid(x_uod, *params)
        else:
            y = trapz_function(x_uod, *params)

        plot_mf(ax, x_uod, y, plot_fill=True)
        ax.tick_params(axis='both', which='both', bottom=False, top=False, left=False,
                       right=False, labelbottom=False, labelleft=False)
        ax.grid(True, linestyle=':', alpha=0.5)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "multiple_mf_sources.pdf"), bbox_inches='tight')
    plt.close()

    # Show binary comparison figure
    make_binary_figure(
        shapes=["step", "sigmoid"],
        save_path=os.path.join(output_dir, "binary_comparison.pdf")
    )

    # Plot fuzzification example
    plot_fuzzification(
        x_uod=np.arange(0, 10, 0.1),
        x_value=6.3,
        mf_func="pl_sigmoid",
        xlim=(0, 9),
        save_path=os.path.join(output_dir, "fuzzification_example.pdf")
    )

    # Define variables for fuzzy inference
    snow_uod = np.arange(0, 30.1, 0.1)
    wind_uod = np.arange(0, 5, 0.125)
    ozone_uod = np.arange(20, 140, 0.1)

    # Create wind membership functions
    wind_calm = piecewise_linear_sigmoid(wind_uod, 2.0, 1.5, 1.0, direction="decreasing")
    wind_breezy = piecewise_linear_sigmoid(wind_uod, 2.0, 1.5, 1.0, direction="increasing")

    # Plot wind membership functions
    MEMBERSHIP_COLORS = {
        "Calm": "#87CEEB",  # Light Sky Blue
        "Breezy": "#228B22",  # Forest Green
        "Shallow": "#CD5C5C",  # Indian Red
        "Deep": "#4682B4"  # Steel Blue
    }

    fig, ax = plt.subplots(1)
    plot_mf(ax, wind_uod, wind_calm, label="Calm", line_color=MEMBERSHIP_COLORS["Calm"], plot_fill=True)
    plot_mf(ax, wind_uod, wind_breezy, label="Breezy", line_color=MEMBERSHIP_COLORS["Breezy"], plot_fill=True)
    ax.legend()
    plt.savefig(os.path.join(output_dir, "wind_membership.pdf"), bbox_inches='tight')
    plt.close()

    # Create snow membership functions
    snow_deep = piecewise_linear_sigmoid(snow_uod, 10, 6, 1.0)
    snow_shallow = piecewise_linear_sigmoid(snow_uod, 10, 6, 1.0, direction="decreasing")

    # Plot snow membership functions
    fig, ax = plt.subplots(1)
    plot_mf(ax, snow_uod, snow_shallow, label="Shallow", line_color=MEMBERSHIP_COLORS["Shallow"], plot_fill=True)
    plot_mf(ax, snow_uod, snow_deep, label="Deep", line_color=MEMBERSHIP_COLORS["Deep"], plot_fill=True)
    ax.legend()
    plt.savefig(os.path.join(output_dir, "snow_membership.pdf"), bbox_inches='tight')
    plt.close()

    # Create ozone membership functions
    ozone_mfs = {
        "background": trapz_function(ozone_uod, 25, 40, 5, 15, 1.0),
        "elevated": trapz_function(ozone_uod, 55, 65, 15, 20, 1.0),
        "extreme": trapz_function(ozone_uod, 85, 95, 15, 45, 1.0)
    }

    fig, ax = plt.subplots(1)
    for category, color in OZONE_CATEGORIES.items():
        plot_mf(ax, ozone_uod, ozone_mfs[category], label=category, line_color=color, plot_fill=True)
    ax.legend()
    plt.savefig(os.path.join(output_dir, "ozone_membership.pdf"), bbox_inches='tight')
    plt.close()

    # Fuzzify inputs
    snow_value = 9.3
    wind_value = 1.6

    # Fuzzify snow value
    snow_membership = np.interp(snow_value, snow_uod, snow_deep)
    print(f"Snow Membership (Deep) at {snow_value} cm: {snow_membership}")

    fig, ax = plot_fuzzification(
        x_uod=snow_uod,
        x_value=snow_value,
        mf_func=snow_deep,
        category_label="deep",
        xlim=(0, 20),
        variable_name="snow depth",
        vrbl_unit="cm",
        save_path=os.path.join(output_dir, "fuzzification_snow.pdf")
    )

    # Fuzzify wind value (calm)
    wind_membership_calm = np.interp(wind_value, wind_uod, wind_calm)
    print(f"Wind Membership (Calm) at {wind_value} m/s: {wind_membership_calm}")

    fig, ax = plot_fuzzification(
        x_uod=wind_uod,
        x_value=wind_value,
        mf_func=wind_calm,
        fuzz_color="blue",
        category_label="calm",
        variable_name="wind speed",
        vrbl_unit="m/s",
        direction="decreasing",
        save_path=os.path.join(output_dir, "fuzzification_wind_calm.pdf")
    )

    # Activation of ozone based on Rule 1: If snow is deep AND wind is calm, then ozone is elevated
    activation1 = min(snow_membership, wind_membership_calm)
    print(f"Activation1 (Elevated Ozone): {activation1}")

    fig, ax, y1 = plot_activation(
        x_uod=ozone_uod,
        mf_func=ozone_mfs["elevated"],
        y_value=activation1,
        fuzz_color=OZONE_CATEGORIES["elevated"],
        category_label="elevated",
        variable_name="ozone",
        vrbl_unit="ppb",
        direction="increasing",
        return_activation_y=True,
        save_path=os.path.join(output_dir, "activation_elevated.pdf")
    )

    # Fuzzify wind value (breezy) for Rule 2: If wind is breezy, then ozone is background
    wind_membership_breezy = np.interp(wind_value, wind_uod, wind_breezy)
    print(f"Wind Membership (Breezy) at {wind_value} m/s: {wind_membership_breezy}")

    fig, ax = plot_fuzzification(
        x_uod=wind_uod,
        x_value=wind_value,
        mf_func=wind_breezy,
        fuzz_color="green",
        category_label="breezy",
        variable_name="wind speed",
        vrbl_unit="m/s",
        direction="increasing",
        save_path=os.path.join(output_dir, "fuzzification_wind_breezy.pdf")
    )

    # Activation of ozone based on Rule 2
    activation2 = wind_membership_breezy
    print(f"Activation2 (Background Ozone): {activation2}")

    fig, ax, y2 = plot_activation(
        x_uod=ozone_uod,
        mf_func=ozone_mfs["background"],
        y_value=activation2,
        fuzz_color=OZONE_CATEGORIES["background"],
        category_label="background",
        variable_name="ozone",
        vrbl_unit="ppb",
        direction="increasing",
        return_activation_y=True,
        save_path=os.path.join(output_dir, "activation_background.pdf")
    )

    # Combine the two activations using maximum (OR operation)
    combined_activation = max(activation1, activation2)
    print(f"Combined Activation: {combined_activation}")

    activation_mf_arrays = {
        "Rule 1": y1,
        "Rule 2": y2,
    }

    # Make these the same as the rule examples above depending on rule itself
    plot_colors = {
        "Rule 1": OZONE_CATEGORIES["elevated"],
        "Rule 2": OZONE_CATEGORIES["background"],
    }

    fig, ax, y_agg = make_mf_figure(
        ozone_uod,
        activation_mf_arrays,
        plot_union=True,
        plot_colors=plot_colors,
        return_aggregated=True,
        save_path=os.path.join(output_dir, "combined_activation_union.pdf")
    )

    # Defuzzify to obtain percentiles
    percentiles = defuzzify_percentiles(
        ozone_uod,
        y_agg,
        percentiles=[10, 50, 90],
        do_plot=True,
        plot_fill=True,
        save_path=os.path.join(output_dir, "defuzzified_percentiles.pdf")
    )

    print("10th Percentile (Risk-Averse):", percentiles['10th percentile'])
    print("50th Percentile (Best Guess/Neutral):", percentiles['50th percentile'])
    print("90th Percentile (Risk-Tolerant):", percentiles['90th percentile'])

    # Possibilistic Risk Communication
    poss_dict = {"Background": activation2, "Elevated": activation1, "Extreme": 0}
    plot_possibility(
        poss_dict,
        colors=list(OZONE_CATEGORIES.values()),
        save_path=os.path.join(output_dir, "possibility_initial.pdf")
    )

    # Add "Extreme" category and "Unsure"
    poss_dict["Extreme"] = 0.6
    poss_dict["Unsure"] = 1 - max(poss_dict.values())

    norm_poss = normalize_possibility(np.array(list(poss_dict.values())))
    norm_poss_dict = dict(zip(poss_dict.keys(), norm_poss))

    bar_colors = list(OZONE_CATEGORIES.values()) + ['grey']
    plot_possibility(
        norm_poss_dict,
        colors=bar_colors,
        save_path=os.path.join(output_dir, "possibility_normalized.pdf")
    )

    # Compute Necessity
    norm_necess_dict = {}
    for category in norm_poss_dict.keys():
        max_other = max([norm_poss_dict[cat] for cat in norm_poss_dict if cat != category], default=0)
        norm_necess_dict[category] = 1 - max_other

    # Plot Necessity
    plot_possibility(
        norm_poss_dict,
        necess_dict=norm_necess_dict,
        colors=bar_colors,
        save_path=os.path.join(output_dir, "possibility_necessity.pdf")
    )

if __name__ == "__main__":
    main()