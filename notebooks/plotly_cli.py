import argparse
from plotly_chart_generator import PlotlyChartGenerator

def main():
    parser = argparse.ArgumentParser(
        description="Generate Plotly charts from JSON data with a single command."
    )

    # Global arguments
    parser.add_argument(
        "--json_input",
        type=str,
        required=True,
        help="Path to JSON file or JSON string."
    )

    parser.add_argument(
        "--output_file",
        type=str,
        default=None,
        help="Path to save the output plot (e.g., plot.html, plot.png). Defaults to [plot_type]_plot.html."
    )

    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Title of the plot."
    )

    # Subparsers for plot types
    subparsers = parser.add_subparsers(title="Plot Types", dest="plot_type", required=True)

    # Scatter Plot Subparser
    scatter_parser = subparsers.add_parser("scatter", help="Create a scatter/bubble plot.")
    scatter_parser.add_argument(
        "--x",
        type=str,
        required=True,
        help="Field name for the x-axis (supports nested fields with dot notation)."
    )
    scatter_parser.add_argument(
        "--y",
        type=str,
        required=True,
        help="Field name for the y-axis (supports nested fields with dot notation)."
    )
    scatter_parser.add_argument(
        "--size",
        type=str,
        default=None,
        help="Field name to determine the size of the markers (supports nested fields)."
    )
    scatter_parser.add_argument(
        "--color",
        type=str,
        default=None,
        help="Field name to determine the color of the markers (supports nested fields)."
    )

    # Line Plot Subparser
    line_parser = subparsers.add_parser("line", help="Create a line plot.")
    line_parser.add_argument(
        "--x",
        type=str,
        required=True,
        help="Field name for the x-axis (supports nested fields with dot notation)."
    )
    line_parser.add_argument(
        "--y",
        type=str,
        required=True,
        help="Field name for the y-axis (supports nested fields with dot notation)."
    )

    # Bar Plot Subparser
    bar_parser = subparsers.add_parser("bar", help="Create a bar plot.")
    bar_parser.add_argument(
        "--x",
        type=str,
        required=True,
        help="Field name for the x-axis (supports nested fields with dot notation)."
    )
    bar_parser.add_argument(
        "--y",
        type=str,
        required=True,
        help="Field name for the y-axis (supports nested fields with dot notation)."
    )
    bar_parser.add_argument(
        "--color",
        type=str,
        default=None,
        help="Field name to determine the color of the bars (supports nested fields)."
    )
    bar_parser.add_argument(
        "--horizontal",
        action="store_true",
        help="Create a horizontal bar chart."
    )

    # Histogram Subparser
    histogram_parser = subparsers.add_parser("histogram", help="Create a histogram.")
    histogram_parser.add_argument(
        "--column",
        type=str,
        required=True,
        help="Field name for the histogram (supports nested fields with dot notation)."
    )
    histogram_parser.add_argument(
        "--nbins",
        type=int,
        default=10,
        help="Number of bins in the histogram."
    )

    # Heatmap Subparser
    heatmap_parser = subparsers.add_parser("heatmap", help="Create a heatmap.")
    heatmap_parser.add_argument(
        "--x",
        type=str,
        required=True,
        help="Field name for the x-axis (supports nested fields with dot notation)."
    )
    heatmap_parser.add_argument(
        "--y",
        type=str,
        required=True,
        help="Field name for the y-axis (supports nested fields with dot notation)."
    )
    heatmap_parser.add_argument(
        "--value",
        type=str,
        required=True,
        help="Field name for the heatmap values (supports nested fields with dot notation)."
    )

    args = parser.parse_args()

    # Initialize the chart generator
    chart_gen = PlotlyChartGenerator()

    # Determine output file name if not provided
    if args.output_file is None:
        args.output_file = f"{args.plot_type}_plot.html"

    # Generate the appropriate plot
    success = False

    if args.plot_type == "scatter":
        success = chart_gen.create_scatter_plot(
            json_input=args.json_input,
            x_col=args.x,
            y_col=args.y,
            size_col=args.size,
            color_col=args.color,
            title=args.title if args.title else "Scatter Plot",
            output_file=args.output_file
        )

    elif args.plot_type == "line":
        success = chart_gen.create_line_plot(
            json_input=args.json_input,
            x_col=args.x,
            y_col=args.y,
            title=args.title if args.title else "Line Plot",
            output_file=args.output_file
        )

    elif args.plot_type == "bar":
        success = chart_gen.create_bar_plot(
            json_input=args.json_input,
            x_col=args.x,
            y_col=args.y,
            color_col=args.color,
            horizontal=args.horizontal,
            title=args.title if args.title else "Bar Plot",
            output_file=args.output_file
        )

    elif args.plot_type == "histogram":
        success = chart_gen.create_histogram(
            json_input=args.json_input,
            column=args.column,
            nbins=args.nbins,
            title=args.title if args.title else "Histogram",
            output_file=args.output_file
        )

    elif args.plot_type == "heatmap":
        success = chart_gen.create_heatmap(
            json_input=args.json_input,
            x_col=args.x,
            y_col=args.y,
            value_col=args.value,
            title=args.title if args.title else "Heatmap",
            output_file=args.output_file
        )

    else:
        print(f"Unsupported plot type: {args.plot_type}")
        exit(1)

    if success:
        print(f"Plot successfully created and saved to '{args.output_file}'.")
    else:
        print("Failed to create the plot.")

if __name__ == "__main__":
    main()