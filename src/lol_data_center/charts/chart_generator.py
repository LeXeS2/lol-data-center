"""Chart generation for League of Legends player statistics.

This module provides utilities for generating visual charts from player match data,
including line charts for stats over time and bar charts for comparative analysis.
"""

from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt

from lol_data_center.logging_config import get_logger

# Use non-interactive backend for server-side rendering
matplotlib.use("Agg")

logger = get_logger(__name__)


class ChartGenerator:
    """Generates statistical charts for League of Legends player data."""

    @staticmethod
    def create_line_chart(
        x_values: list[str],
        y_values: list[float],
        title: str,
        x_label: str,
        y_label: str,
        line_color: str = "#5383EC",
    ) -> BytesIO:
        """Create a line chart for stats over time.

        Args:
            x_values: X-axis labels (e.g., game numbers or dates)
            y_values: Y-axis values (stats to plot)
            title: Chart title
            x_label: X-axis label
            y_label: Y-axis label
            line_color: Line color (default: Discord blue)

        Returns:
            BytesIO buffer containing PNG image data
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot the line
        ax.plot(x_values, y_values, color=line_color, linewidth=2, marker="o", markersize=4)

        # Set labels and title
        ax.set_xlabel(x_label, fontsize=12, fontweight="bold")
        ax.set_ylabel(y_label, fontsize=12, fontweight="bold")
        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

        # Add grid for readability
        ax.grid(True, alpha=0.3, linestyle="--")

        # Rotate x-axis labels if there are many points
        if len(x_values) > 10:
            plt.xticks(rotation=45, ha="right")

        # Tight layout to prevent label cutoff
        plt.tight_layout()

        # Save to buffer
        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)
        plt.close(fig)

        logger.info(
            "Generated line chart",
            title=title,
            data_points=len(x_values),
        )

        return buffer

    @staticmethod
    def create_bar_chart(
        categories: list[str],
        values: list[float],
        title: str,
        x_label: str,
        y_label: str,
        bar_color: str = "#5383EC",
    ) -> BytesIO:
        """Create a bar chart for comparing stats across categories.

        Args:
            categories: Category names (e.g., champion names, roles)
            values: Values for each category
            title: Chart title
            x_label: X-axis label
            y_label: Y-axis label
            bar_color: Bar color (default: Discord blue)

        Returns:
            BytesIO buffer containing PNG image data
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        # Create bars
        bars = ax.bar(categories, values, color=bar_color, alpha=0.8, edgecolor="black")

        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.1f}",
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
            )

        # Set labels and title
        ax.set_xlabel(x_label, fontsize=12, fontweight="bold")
        ax.set_ylabel(y_label, fontsize=12, fontweight="bold")
        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

        # Add grid for readability
        ax.grid(True, alpha=0.3, linestyle="--", axis="y")

        # Rotate x-axis labels if there are many categories
        if len(categories) > 5:
            plt.xticks(rotation=45, ha="right")

        # Tight layout to prevent label cutoff
        plt.tight_layout()

        # Save to buffer
        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)
        plt.close(fig)

        logger.info(
            "Generated bar chart",
            title=title,
            categories=len(categories),
        )

        return buffer

    @staticmethod
    def create_grouped_bar_chart(
        categories: list[str],
        data_groups: dict[str, list[float]],
        title: str,
        x_label: str,
        y_label: str,
        colors: list[str] | None = None,
    ) -> BytesIO:
        """Create a grouped bar chart for comparing multiple stats across categories.

        Args:
            categories: Category names (e.g., champion names, roles)
            data_groups: Dictionary mapping stat names to lists of values
            title: Chart title
            x_label: X-axis label
            y_label: Y-axis label
            colors: Optional list of colors for each group

        Returns:
            BytesIO buffer containing PNG image data
        """
        if not data_groups:
            raise ValueError("data_groups cannot be empty")

        # Use default colors if not provided
        if colors is None:
            colors = ["#5383EC", "#43B581", "#FAA61A", "#F04747", "#9B59B6"]

        fig, ax = plt.subplots(figsize=(14, 7))

        num_groups = len(data_groups)
        num_categories = len(categories)
        bar_width = 0.8 / num_groups
        x_positions = range(num_categories)

        # Plot each group
        for i, (group_name, values) in enumerate(data_groups.items()):
            offset = (i - num_groups / 2) * bar_width + bar_width / 2
            positions = [x + offset for x in x_positions]
            color = colors[i % len(colors)]

            ax.bar(
                positions,
                values,
                bar_width,
                label=group_name,
                color=color,
                alpha=0.8,
                edgecolor="black",
            )

        # Set labels and title
        ax.set_xlabel(x_label, fontsize=12, fontweight="bold")
        ax.set_ylabel(y_label, fontsize=12, fontweight="bold")
        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

        # Set x-axis ticks
        ax.set_xticks(x_positions)
        ax.set_xticklabels(categories)

        # Add legend
        ax.legend(loc="upper right", fontsize=10)

        # Add grid for readability
        ax.grid(True, alpha=0.3, linestyle="--", axis="y")

        # Rotate x-axis labels if there are many categories
        if num_categories > 5:
            plt.xticks(rotation=45, ha="right")

        # Tight layout to prevent label cutoff
        plt.tight_layout()

        # Save to buffer
        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)
        plt.close(fig)

        logger.info(
            "Generated grouped bar chart",
            title=title,
            categories=num_categories,
            groups=num_groups,
        )

        return buffer
