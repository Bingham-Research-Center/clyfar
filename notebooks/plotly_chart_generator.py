import plotly.express as px
import json
import os
import pandas as pd  # Required for heatmap pivoting

class PlotlyChartGenerator:

    def __init__(self):
        """Initialize the chart generator"""
        pass

    def _load_json(self, json_input):
        """
        Load JSON data from a file path or JSON string/dictionary.

        Parameters:
            json_input (str or dict or list): File path to JSON file, JSON string, or already parsed JSON data.

        Returns:
            dict or list: Parsed JSON data, or None if an error occurs.
        """
        if isinstance(json_input, str):
            if os.path.isfile(json_input):
                try:
                    with open(json_input, 'r') as file:
                        data = json.load(file)
                    return data
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON file '{json_input}': {e}")
                    return None
                except Exception as e:
                    print(f"Error reading JSON file '{json_input}': {e}")
                    return None
            else:
                try:
                    data = json.loads(json_input)
                    return data
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON string: {e}")
                    return None
        elif isinstance(json_input, (dict, list)):
            return json_input
        else:
            print("Invalid JSON input type. Must be a file path, JSON string, or a dictionary/list.")
            return None

    def get_nested_value(self, record, field):
        """
        Retrieve a value from a nested dictionary using dot notation.

        Parameters:
            record (dict): The dictionary to retrieve the value from.
            field (str): The field name, possibly with dots for nested fields (e.g., 'measurements.pm25').

        Returns:
            The value if found, else None.
        """
        keys = field.split('.')
        value = record
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def create_scatter_plot(self, json_input, x_col, y_col, title="Scatter Plot",
                            size_col=None, color_col=None, output_file="scatter_plot.html"):
        """
        Create scatter/bubble plot from JSON data and save it to a file.

        Parameters:
            json_input (str or dict or list): File path to JSON file, JSON string, or parsed JSON data.
            x_col (str): Column name for the x-axis (supports nested fields with dot notation).
            y_col (str): Column name for the y-axis (supports nested fields with dot notation).
            title (str): Title of the plot.
            size_col (str, optional): Column name to determine the size of the markers (supports nested fields).
            color_col (str, optional): Column name to determine the color of the markers (supports nested fields).
            output_file (str): Path to save the output plot (supports .html and .png).

        Returns:
            bool: True if the plot was created and saved successfully, False otherwise.
        """
        try:
            data = self._load_json(json_input)
            if data is None:
                return False

            # Ensure data is a list of dictionaries
            if not isinstance(data, list):
                print("Error: JSON data should be a list of dictionaries for scatter plots.")
                return False

            # Extract data
            df = pd.DataFrame(data)
            df['x'] = df.apply(lambda row: self.get_nested_value(row, x_col), axis=1)
            df['y'] = df.apply(lambda row: self.get_nested_value(row, y_col), axis=1)

            if size_col:
                df['size'] = df.apply(lambda row: self.get_nested_value(row, size_col), axis=1)
            else:
                df['size'] = None

            if color_col:
                df['color'] = df.apply(lambda row: self.get_nested_value(row, color_col), axis=1)
            else:
                df['color'] = None

            # Check for missing values
            if df['x'].isnull().any() or df['y'].isnull().any():
                print("Error: Missing 'x' or 'y' values in some records.")
                return False

            # Debugging: Print extracted values
            print(f"X values: {df['x'].tolist()}")
            print(f"Y values: {df['y'].tolist()}")
            if size_col:
                print(f"Size values: {df['size'].tolist()}")
            if color_col:
                print(f"Color values: {df['color'].tolist()}")

            fig = px.scatter(
                df,
                x='x',
                y='y',
                size='size' if size_col else None,
                color='color' if color_col else None,
                title=title,
                labels={'x': x_col, 'y': y_col}
            )

            fig.update_traces(marker=dict(
                opacity=0.6,
                line=dict(width=1, color="cyan")
            ))

            self._save_figure(fig, output_file)
            return True

        except Exception as e:
            print(f"Error creating scatter plot: {e}")
            return False

    def create_line_plot(self, json_input, x_col, y_col, title="Line Plot", output_file="line_plot.html"):
        """
        Create line plot from JSON data and save it to a file.

        Parameters:
            json_input (str or dict or list): File path to JSON file, JSON string, or parsed JSON data.
            x_col (str): Column name for the x-axis (supports nested fields with dot notation).
            y_col (str): Column name for the y-axis (supports nested fields with dot notation).
            title (str): Title of the plot.
            output_file (str): Path to save the output plot (supports .html and .png).

        Returns:
            bool: True if the plot was created and saved successfully, False otherwise.
        """
        try:
            data = self._load_json(json_input)
            if data is None:
                return False

            # Ensure data is a list of dictionaries
            if not isinstance(data, list):
                print("Error: JSON data should be a list of dictionaries for line plots.")
                return False

            # Extract data
            df = pd.DataFrame(data)
            df['x'] = df.apply(lambda row: self.get_nested_value(row, x_col), axis=1)
            df['y'] = df.apply(lambda row: self.get_nested_value(row, y_col), axis=1)

            # Check for missing values
            if df['x'].isnull().any() or df['y'].isnull().any():
                print("Error: Missing 'x' or 'y' values in some records.")
                return False

            # Debugging: Print extracted values
            print(f"X values: {df['x'].tolist()}")
            print(f"Y values: {df['y'].tolist()}")

            fig = px.line(
                df,
                x='x',
                y='y',
                title=title,
                labels={'x': x_col, 'y': y_col}
            )

            fig.update_traces(line=dict(
                width=2,
                dash='solid',
                shape='linear'
            ))

            self._save_figure(fig, output_file)
            return True

        except Exception as e:
            print(f"Error creating line plot: {e}")
            return False

    def create_bar_plot(self, json_input, x_col, y_col, title="Bar Plot",
                        color_col=None, horizontal=False, output_file="bar_plot.html"):
        """
        Create bar plot from JSON data and save it to a file.

        Parameters:
            json_input (str or dict or list): File path to JSON file, JSON string, or parsed JSON data.
            x_col (str): Column name for the x-axis (supports nested fields with dot notation).
            y_col (str): Column name for the y-axis (supports nested fields with dot notation).
            title (str): Title of the plot.
            color_col (str, optional): Column name to determine the color of the bars (supports nested fields).
            horizontal (bool, optional): If True, creates a horizontal bar chart.
            output_file (str): Path to save the output plot (supports .html and .png).

        Returns:
            bool: True if the plot was created and saved successfully, False otherwise.
        """
        try:
            data = self._load_json(json_input)
            if data is None:
                return False

            # Ensure data is a list of dictionaries
            if not isinstance(data, list):
                print("Error: JSON data should be a list of dictionaries for bar plots.")
                return False

            # Extract data
            df = pd.DataFrame(data)
            df['x'] = df.apply(lambda row: self.get_nested_value(row, x_col), axis=1)
            df['y'] = df.apply(lambda row: self.get_nested_value(row, y_col), axis=1)

            if color_col:
                df['color'] = df.apply(lambda row: self.get_nested_value(row, color_col), axis=1)
            else:
                df['color'] = None

            # Check for missing values
            if df['x'].isnull().any() or df['y'].isnull().any():
                print("Error: Missing 'x' or 'y' values in some records.")
                return False

            # Debugging: Print extracted values
            print(f"X values: {df['x'].tolist()}")
            print(f"Y values: {df['y'].tolist()}")
            if color_col:
                print(f"Color values: {df['color'].tolist()}")

            if horizontal:
                fig = px.bar(
                    df,
                    x='y',
                    y='x',
                    color='color' if color_col else None,
                    title=title,
                    orientation='h',
                    labels={'x': x_col, 'y': y_col}
                )
            else:
                fig = px.bar(
                    df,
                    x='x',
                    y='y',
                    color='color' if color_col else None,
                    title=title,
                    labels={'x': x_col, 'y': y_col}
                )

            fig.update_traces(marker=dict(
                opacity=0.6,
                line=dict(width=1)
            ))

            self._save_figure(fig, output_file)
            return True

        except Exception as e:
            print(f"Error creating bar plot: {e}")
            return False

    def create_histogram(self, json_input, column, title="Histogram",
                         nbins=10, output_file="histogram.html"):
        """
        Create histogram from JSON data and save it to a file.

        Parameters:
            json_input (str or dict or list): File path to JSON file, JSON string, or parsed JSON data.
            column (str): Column name for which the histogram is to be plotted (supports nested fields with dot notation).
            title (str): Title of the plot.
            nbins (int, optional): Number of bins in the histogram.
            output_file (str): Path to save the output plot (supports .html and .png).

        Returns:
            bool: True if the plot was created and saved successfully, False otherwise.
        """
        try:
            data = self._load_json(json_input)
            if data is None:
                return False

            # Ensure data is a list of dictionaries
            if not isinstance(data, list):
                print("Error: JSON data should be a list of dictionaries for histogram plots.")
                return False

            # Extract data
            df = pd.DataFrame(data)
            df['value'] = df.apply(lambda row: self.get_nested_value(row, column), axis=1)

            # Check for missing values
            if df['value'].isnull().any():
                print("Error: Missing 'value' in some records.")
                return False

            # Debugging: Print extracted values
            print(f"Values for histogram: {df['value'].tolist()}")

            fig = px.histogram(
                df,
                x='value',
                nbins=nbins,
                title=title,
                labels={'value': column}
            )

            fig.update_traces(marker=dict(
                opacity=0.6,
                line=dict(width=1)
            ))

            self._save_figure(fig, output_file)
            return True

        except ImportError:
            print("Error: pandas is required for creating histograms. Please install it using 'pip install pandas'.")
            return False
        except Exception as e:
            print(f"Error creating histogram: {e}")
            return False

    def create_heatmap(self, json_input, x_col, y_col, value_col, title="Heatmap", output_file="heatmap.html"):
        """
        Create heatmap from JSON data and save it to a file.

        Parameters:
            json_input (str or dict or list): File path to JSON file, JSON string, or parsed JSON data.
            x_col (str): Column name for the x-axis (supports nested fields with dot notation).
            y_col (str): Column name for the y-axis (supports nested fields with dot notation).
            value_col (str): Column name for the heatmap values (supports nested fields with dot notation).
            title (str): Title of the plot.
            output_file (str): Path to save the output plot (supports .html and .png).

        Returns:
            bool: True if the plot was created and saved successfully, False otherwise.
        """
        try:
            data = self._load_json(json_input)
            if data is None:
                return False

            # Ensure data is a list of dictionaries
            if not isinstance(data, list):
                print("Error: JSON data should be a list of dictionaries for heatmap plots.")
                return False

            # Extract data
            df = pd.DataFrame(data)
            df['x'] = df.apply(lambda row: self.get_nested_value(row, x_col), axis=1)
            df['y'] = df.apply(lambda row: self.get_nested_value(row, y_col), axis=1)
            df['value'] = df.apply(lambda row: self.get_nested_value(row, value_col), axis=1)

            # Check for missing values
            if df['x'].isnull().any() or df['y'].isnull().any() or df['value'].isnull().any():
                print("Error: Missing 'x', 'y', or 'value' in some records.")
                return False

            # Debugging: Print extracted values
            print(f"X values: {df['x'].tolist()}")
            print(f"Y values: {df['y'].tolist()}")
            print(f"Value values: {df['value'].tolist()}")

            # Create pivot table
            pivot_table = df.pivot(index='y', columns='x', values='value')

            fig = px.imshow(
                pivot_table,
                labels={'x': x_col, 'y': y_col, 'color': value_col},
                title=title,
                color_continuous_scale="RdBu",
                text_auto=True
            )

            fig.update_layout(
                xaxis_title=x_col,
                yaxis_title=y_col,
                title=title
            )

            self._save_figure(fig, output_file)
            return True

        except ImportError:
            print("Error: pandas is required for creating heatmaps. Please install it using 'pip install pandas'.")
            return False
        except Exception as e:
            print(f"Error creating heatmap: {e}")
            return False

    def _save_figure(self, fig, output_file):
        """
        Save the Plotly figure to a file.

        Parameters:
            fig (plotly.graph_objs._figure.Figure): The Plotly figure to save.
            output_file (str): Path to save the plot (supports .html and .png).

        Returns:
            None
        """
        try:
            _, ext = os.path.splitext(output_file)
            if ext.lower() == '.html':
                fig.write_html(output_file)
                print(f"Plot saved as {output_file}")
            elif ext.lower() in ['.png', '.jpg', '.jpeg', '.svg', '.pdf']:
                # To save as static image, you need Kaleido installed
                fig.write_image(output_file)
                print(f"Plot saved as {output_file}")
            else:
                raise ValueError("Unsupported file format. Use .html, .png, .jpg, .jpeg, .svg, or .pdf.")
        except Exception as e:
            print(f"Error saving plot to '{output_file}': {e}")