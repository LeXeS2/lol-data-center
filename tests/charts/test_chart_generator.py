"""Tests for chart generation functionality."""

from io import BytesIO

import pytest

from lol_data_center.charts.chart_generator import ChartGenerator


class TestChartGenerator:
    """Tests for the ChartGenerator class."""

    def test_create_line_chart(self) -> None:
        """Test line chart generation."""
        chart_gen = ChartGenerator()

        x_values = ["Game 1", "Game 2", "Game 3", "Game 4", "Game 5"]
        y_values = [10.0, 12.0, 8.0, 15.0, 11.0]

        buffer = chart_gen.create_line_chart(
            x_values=x_values,
            y_values=y_values,
            title="Test Line Chart",
            x_label="Games",
            y_label="Kills",
        )

        # Verify buffer is valid PNG
        assert isinstance(buffer, BytesIO)
        buffer.seek(0)
        png_header = buffer.read(8)
        assert png_header == b"\x89PNG\r\n\x1a\n"  # PNG file signature

        # Verify buffer has content
        buffer.seek(0)
        data = buffer.read()
        assert len(data) > 0

    def test_create_line_chart_custom_color(self) -> None:
        """Test line chart with custom color."""
        chart_gen = ChartGenerator()

        x_values = ["A", "B", "C"]
        y_values = [1.0, 2.0, 3.0]

        buffer = chart_gen.create_line_chart(
            x_values=x_values,
            y_values=y_values,
            title="Custom Color Chart",
            x_label="X",
            y_label="Y",
            line_color="#FF0000",
        )

        assert isinstance(buffer, BytesIO)
        buffer.seek(0)
        assert len(buffer.read()) > 0

    def test_create_line_chart_many_points(self) -> None:
        """Test line chart with many data points (triggers x-axis rotation)."""
        chart_gen = ChartGenerator()

        x_values = [f"Game {i}" for i in range(1, 21)]
        y_values = [float(i * 2) for i in range(1, 21)]

        buffer = chart_gen.create_line_chart(
            x_values=x_values,
            y_values=y_values,
            title="Many Points Chart",
            x_label="Games",
            y_label="Value",
        )

        assert isinstance(buffer, BytesIO)
        buffer.seek(0)
        assert len(buffer.read()) > 0

    def test_create_bar_chart(self) -> None:
        """Test bar chart generation."""
        chart_gen = ChartGenerator()

        categories = ["Champion A", "Champion B", "Champion C"]
        values = [15.5, 12.3, 18.7]

        buffer = chart_gen.create_bar_chart(
            categories=categories,
            values=values,
            title="Test Bar Chart",
            x_label="Champions",
            y_label="Average Kills",
        )

        # Verify buffer is valid PNG
        assert isinstance(buffer, BytesIO)
        buffer.seek(0)
        png_header = buffer.read(8)
        assert png_header == b"\x89PNG\r\n\x1a\n"

        # Verify buffer has content
        buffer.seek(0)
        data = buffer.read()
        assert len(data) > 0

    def test_create_bar_chart_custom_color(self) -> None:
        """Test bar chart with custom color."""
        chart_gen = ChartGenerator()

        categories = ["A", "B"]
        values = [10.0, 20.0]

        buffer = chart_gen.create_bar_chart(
            categories=categories,
            values=values,
            title="Custom Color Bar Chart",
            x_label="Category",
            y_label="Value",
            bar_color="#00FF00",
        )

        assert isinstance(buffer, BytesIO)
        buffer.seek(0)
        assert len(buffer.read()) > 0

    def test_create_bar_chart_many_categories(self) -> None:
        """Test bar chart with many categories (triggers x-axis rotation)."""
        chart_gen = ChartGenerator()

        categories = [f"Cat {i}" for i in range(1, 11)]
        values = [float(i * 1.5) for i in range(1, 11)]

        buffer = chart_gen.create_bar_chart(
            categories=categories,
            values=values,
            title="Many Categories Chart",
            x_label="Categories",
            y_label="Values",
        )

        assert isinstance(buffer, BytesIO)
        buffer.seek(0)
        assert len(buffer.read()) > 0

    def test_create_grouped_bar_chart(self) -> None:
        """Test grouped bar chart generation."""
        chart_gen = ChartGenerator()

        categories = ["Champion A", "Champion B", "Champion C"]
        data_groups = {
            "Kills": [10.0, 12.0, 8.0],
            "Deaths": [5.0, 6.0, 4.0],
            "Assists": [15.0, 18.0, 12.0],
        }

        buffer = chart_gen.create_grouped_bar_chart(
            categories=categories,
            data_groups=data_groups,
            title="Test Grouped Bar Chart",
            x_label="Champions",
            y_label="Average Stats",
        )

        # Verify buffer is valid PNG
        assert isinstance(buffer, BytesIO)
        buffer.seek(0)
        png_header = buffer.read(8)
        assert png_header == b"\x89PNG\r\n\x1a\n"

        # Verify buffer has content
        buffer.seek(0)
        data = buffer.read()
        assert len(data) > 0

    def test_create_grouped_bar_chart_custom_colors(self) -> None:
        """Test grouped bar chart with custom colors."""
        chart_gen = ChartGenerator()

        categories = ["A", "B"]
        data_groups = {
            "Series 1": [10.0, 15.0],
            "Series 2": [20.0, 25.0],
        }
        colors = ["#FF0000", "#00FF00"]

        buffer = chart_gen.create_grouped_bar_chart(
            categories=categories,
            data_groups=data_groups,
            title="Custom Colors Grouped Chart",
            x_label="Category",
            y_label="Value",
            colors=colors,
        )

        assert isinstance(buffer, BytesIO)
        buffer.seek(0)
        assert len(buffer.read()) > 0

    def test_create_grouped_bar_chart_empty_data_groups(self) -> None:
        """Test grouped bar chart with empty data groups raises error."""
        chart_gen = ChartGenerator()

        categories = ["A", "B"]
        data_groups: dict[str, list[float]] = {}

        with pytest.raises(ValueError, match="data_groups cannot be empty"):
            chart_gen.create_grouped_bar_chart(
                categories=categories,
                data_groups=data_groups,
                title="Empty Data",
                x_label="X",
                y_label="Y",
            )

    def test_create_grouped_bar_chart_many_categories(self) -> None:
        """Test grouped bar chart with many categories."""
        chart_gen = ChartGenerator()

        categories = [f"Cat {i}" for i in range(1, 11)]
        data_groups = {
            "Metric 1": [float(i) for i in range(1, 11)],
            "Metric 2": [float(i * 2) for i in range(1, 11)],
        }

        buffer = chart_gen.create_grouped_bar_chart(
            categories=categories,
            data_groups=data_groups,
            title="Many Categories Grouped",
            x_label="Categories",
            y_label="Values",
        )

        assert isinstance(buffer, BytesIO)
        buffer.seek(0)
        assert len(buffer.read()) > 0
