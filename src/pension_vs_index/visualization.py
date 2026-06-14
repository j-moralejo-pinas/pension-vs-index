"""Reusable visualization helpers for pension-vs-index analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.ticker import FuncFormatter, NullFormatter

if TYPE_CHECKING:
    import pandas as pd
    from matplotlib.axes import Axes

EURO_MILLION = 1_000_000
EURO_THOUSAND = 1_000


def _format_compact_decimal(value: float) -> str:
    """
    Format a decimal number with one decimal place, removing trailing zeros.

    Parameters
    ----------
    value : float
        The number to format.

    Returns
    -------
    str
        The formatted number as a string, with one decimal place and trailing zeros removed.
    """
    return f"{value:.1f}".rstrip("0").rstrip(".").replace(".", ",")


def _format_scenario_euros(value: float) -> str:
    """
    Format a euro amount for scenario labels.

    Parameters
    ----------
    value : float
        The euro amount to format.

    Returns
    -------
    str
        The formatted euro amount as a string.
    """
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= EURO_MILLION:
        return f"{sign}{_format_compact_decimal(abs_value / EURO_MILLION)}M"
    if abs_value >= EURO_THOUSAND:
        return f"{sign}{_format_compact_decimal(abs_value / EURO_THOUSAND)}k"
    return f"{value:.0f}"


def format_extraction_rate_label(withdrawal_rate: float | None) -> str:
    """
    Format an extraction rate for chart names.

    Parameters
    ----------
    withdrawal_rate : float | None
        The withdrawal rate to format, or None for total extraction.

    Returns
    -------
    str
        The formatted extraction rate as a string.
    """
    if withdrawal_rate is None:
        return "total"
    return f"{_format_compact_decimal(withdrawal_rate * 100)}%"


def format_salary_extraction_chart_name(
    *,
    salary_before_retirement: float,
    salary_after_retirement: float,
    withdrawal_rate: float | None,
) -> str:
    """
    Build normalized chart names for salary and extraction scenarios.

    Parameters
    ----------
    salary_before_retirement : float
        Gross salary used for the contribution period.
    salary_after_retirement : float
        Existing gross income used for the withdrawal period.
    withdrawal_rate : float | None
        Withdrawal rate to include in the chart name, or None for total extraction.

    Returns
    -------
    str
        Normalized Spanish chart name describing salaries and extraction mode.
    """
    salary_before = _format_scenario_euros(salary_before_retirement)
    salary_after = _format_scenario_euros(salary_after_retirement)
    extraction_rate = format_extraction_rate_label(withdrawal_rate)
    return (
        f"Salario antes del retiro {salary_before} · "
        f"salario después del retiro {salary_after} · "
        f"extracción {extraction_rate}"
    )


def format_euros(value: float, _position: int | None = None) -> str:
    """
    Format euro-denominated chart ticks with compact suffixes.

    Parameters
    ----------
    value : float
        Euro-denominated value to format.
    _position : int | None, optional
        Tick position supplied by Matplotlib. It is unused.

    Returns
    -------
    str
        Compact euro label using ``k`` or ``M`` suffixes when appropriate.
    """
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= EURO_MILLION:
        return f"{sign}{abs_value / EURO_MILLION:.1f}M"
    if abs_value >= EURO_THOUSAND:
        return f"{sign}{abs_value / EURO_THOUSAND:.0f}k"
    return f"{value:.0f}"


EURO_FORMATTER = FuncFormatter(format_euros)


def apply_money_axis(
    ax: Axes,
    axis: Literal["x", "y"],
    ticks: list[float] | None = None,
) -> None:
    """
    Apply compact euro formatting to one axis.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes object to format.
    axis : Literal["x", "y"]
        Axis to format.
    ticks : list[float] | None, optional
        Explicit tick values to set before applying the formatter.

    Returns
    -------
    None
        The axes object is modified in place.
    """
    if ticks is not None:
        getattr(ax, f"set_{axis}ticks")(ticks)
    axis_obj = getattr(ax, f"{axis}axis")
    axis_obj.set_major_formatter(EURO_FORMATTER)
    axis_obj.set_minor_formatter(NullFormatter())
    ax.tick_params(axis=axis, rotation=0)


def _symmetric_color_limit(values: Any) -> float:
    """
    Return a symmetric color scale limit for signed heatmap values.

    Parameters
    ----------
    values : Any
        Array-like values supporting ``min`` and ``max``.

    Returns
    -------
    float
        Maximum absolute value across the input array.
    """
    finite_values = values[np.isfinite(values)]
    if finite_values.size == 0:
        return 0.0

    return max(abs(finite_values.max()), abs(finite_values.min()))


def plot_accumulation_history(history: pd.DataFrame) -> Any:
    """
    Plot pre-withdrawal portfolio value over time for each vehicle.

    Parameters
    ----------
    history : pd.DataFrame
        Yearly accumulation history with vehicle, year, and pre-withdrawal value columns.

    Returns
    -------
    Any
        Matplotlib figure containing the accumulation line chart.
    """
    fig, ax = plt.subplots(figsize=(9, 5))
    for vehicle, rows in history.groupby("vehicle"):
        ax.plot(rows["year"], rows["pre_withdrawal_value"], marker="o", label=vehicle)
    ax.set_title("Valor acumulado antes del rescate")
    ax.set_xlabel("Año de inversión")
    ax.set_ylabel("Valor de la cartera")
    apply_money_axis(ax, "y")
    ax.legend()
    return fig


def plot_extraction_comparison_breakdown(
    extraction_results: pd.DataFrame,
    *,
    title: str,
    figsize: tuple[float, float] = (11, 5),
) -> Any:
    """
    Plot gross extraction split into after-tax money, taxes, and fees.

    Parameters
    ----------
    extraction_results : pd.DataFrame
        Normalized extraction rows with scenario, vehicle, after-tax money, tax, and fee columns.
    title : str
        Chart title.
    figsize : tuple[float, float], optional
        Matplotlib figure size, by default ``(11, 5)``.

    Returns
    -------
    Any
        Matplotlib figure containing the stacked extraction breakdown.
    """
    plot_data = extraction_results.copy()
    single_scenario = plot_data["scenario"].drop_duplicates().shape[0] == 1
    if single_scenario:
        plot_data["label"] = plot_data["vehicle"]
    else:
        plot_data["label"] = plot_data["scenario"] + "\n" + plot_data["vehicle"]
    value_columns = ["after_tax_money", "extraction_tax"]
    colors = ["#54a24b", "#e45756"]
    if plot_data["extraction_fees"].abs().sum() > 0:
        value_columns.append("extraction_fees")
        colors.append("#b279a2")

    fig, ax = plt.subplots(figsize=figsize)
    plot_data.set_index("label")[value_columns].plot.bar(stacked=True, ax=ax, color=colors)
    ax.set_title(title)
    ax.set_xlabel("Vehículo")
    ax.set_ylabel("Rescate bruto")
    apply_money_axis(ax, "y")
    ax.tick_params(axis="x", rotation=0)
    ax.legend(
        ["Dinero neto", "Impuestos del rescate", "Comisiones de salida"][: len(value_columns)]
    )
    fig.tight_layout()
    return fig


def add_sign_boundary(
    ax: Axes,
    x_edges: list[float],
    y_edges: list[float],
    values: Any,
) -> None:
    """
    Draw grid-cell boundaries where values change sign.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes where boundary segments are added.
    x_edges : list[float]
        Cell edge coordinates for the x-axis.
    y_edges : list[float]
        Cell edge coordinates for the y-axis.
    values : Any
        Two-dimensional array-like values whose sign changes define boundaries.

    Returns
    -------
    None
        Boundary segments are added to ``ax`` in place.
    """
    finite_cells = np.isfinite(values)
    positive_cells = values > 0
    boundary_segments = []
    for row in range(positive_cells.shape[0]):
        for column in range(positive_cells.shape[1] - 1):
            if not (finite_cells[row, column] and finite_cells[row, column + 1]):
                continue
            if positive_cells[row, column] != positive_cells[row, column + 1]:
                boundary_segments.extend(
                    (
                        [
                            (x_edges[column + 1], y_edges[row]),
                            (x_edges[column + 1], y_edges[row + 1]),
                        ],
                    )
                )
    for row in range(positive_cells.shape[0] - 1):
        for column in range(positive_cells.shape[1]):
            if not (finite_cells[row, column] and finite_cells[row + 1, column]):
                continue
            if positive_cells[row, column] != positive_cells[row + 1, column]:
                boundary_segments.extend(
                    (
                        [
                            (x_edges[column], y_edges[row + 1]),
                            (x_edges[column + 1], y_edges[row + 1]),
                        ],
                    )
                )
    if boundary_segments:
        ax.add_collection(LineCollection(boundary_segments, colors="#1900ff", linewidths=1.6))


def plot_salary_heatmap_panel(
    ax: Axes,
    scenario: dict[str, Any],
    salary_data: pd.DataFrame,
    axes_by_scenario: dict[str, dict[str, Any]],
) -> Any:
    """
    Plot one salary-pair pension-advantage heatmap panel.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes where the panel is drawn.
    scenario : dict[str, Any]
        Salary heatmap settings for one scenario.
    salary_data : pd.DataFrame
        Pension-advantage data over contribution and withdrawal salary pairs.
    axes_by_scenario : dict[str, dict[str, Any]]
        Axis sweeps and cell edges keyed by scenario name.

    Returns
    -------
    Any
        Matplotlib image object returned by ``pcolormesh``.
    """
    axis_data = axes_by_scenario[scenario["name"]]
    salary_grid = salary_data[salary_data["scenario"] == scenario["name"]].pivot_table(
        index="withdrawal_salary",
        columns="contribution_salary",
        values="pension_advantage",
        dropna=False,
    )
    salary_values = salary_grid.to_numpy()
    color_limit = _symmetric_color_limit(salary_values)
    image = ax.pcolormesh(
        axis_data["contribution_salary_edges"],
        axis_data["withdrawal_salary_edges"],
        salary_values,
        cmap="RdYlGn",
        shading="flat",
        vmin=-color_limit,
        vmax=color_limit,
    )
    add_sign_boundary(
        ax,
        axis_data["contribution_salary_edges"],
        axis_data["withdrawal_salary_edges"],
        salary_values,
    )
    ax.set_title(scenario["name"])
    ax.set_xlabel("Salario antes del retiro (EUR)")
    ax.set_ylabel("Salario después del retiro (EUR)")
    apply_money_axis(ax, "x", scenario["contribution_salary_ticks"])
    apply_money_axis(ax, "y", scenario["withdrawal_salary_ticks"])
    ax.set_xlim(scenario["contribution_salary_min"], scenario["contribution_salary_max"])
    ax.set_ylim(scenario["withdrawal_salary_min"], scenario["withdrawal_salary_max"])
    return image


def plot_salary_heatmaps(
    scenarios: list[dict[str, Any]],
    salary_data: pd.DataFrame,
    axes_by_scenario: dict[str, dict[str, Any]],
    *,
    figsize: tuple[float, float],
    colorbar_label: str,
    title: str,
) -> Any:
    """
    Plot a row of salary-pair heatmap panels.

    Parameters
    ----------
    scenarios : list[dict[str, Any]]
        Salary heatmap settings, one dictionary per panel.
    salary_data : pd.DataFrame
        Pension-advantage data for all panels.
    axes_by_scenario : dict[str, dict[str, Any]]
        Axis sweeps and cell edges keyed by scenario name.
    figsize : tuple[float, float]
        Matplotlib figure size.
    colorbar_label : str
        Label for each panel colorbar.
    title : str
        Figure title.

    Returns
    -------
    Any
        Matplotlib figure containing all salary heatmap panels.
    """
    fig, axes = plt.subplots(
        1,
        len(scenarios),
        figsize=figsize,
        dpi=160,
        squeeze=False,
    )

    for column, scenario in enumerate(scenarios):
        image = plot_salary_heatmap_panel(
            axes[0, column],
            scenario,
            salary_data,
            axes_by_scenario,
        )
        fig.colorbar(image, ax=axes[0, column], label=colorbar_label)

    fig.suptitle(title, y=1.02)
    return fig


def plot_fee_return_sensitivity(
    fee_return_sensitivity: pd.DataFrame,
    *,
    title: str = "Ventaja del plan por rentabilidad y sobrecoste de comisión",
    colorbar_label: str = "Ventaja neta después de impuestos",
    expected_return_edges: list[float] | None = None,
    pension_fee_premium_edges: list[float] | None = None,
    expected_return_ticks: list[float] | None = None,
    pension_fee_premium_ticks: list[float] | None = None,
) -> Any:
    """
    Plot pension advantage by expected return and pension fee premium.

    Parameters
    ----------
    fee_return_sensitivity : pd.DataFrame
        Pension-advantage data over expected return and pension fee premium.
    title : str, optional
        Chart title.
    colorbar_label : str, optional
        Colorbar label.
    expected_return_edges : list[float] | None, optional
        Expected-return cell edges for ``pcolormesh``. If None, ``imshow`` is used.
    pension_fee_premium_edges : list[float] | None, optional
        Pension-fee-premium cell edges for ``pcolormesh``. If None, ``imshow`` is used.
    expected_return_ticks : list[float] | None, optional
        Expected-return tick values. Defaults to the provided edges.
    pension_fee_premium_ticks : list[float] | None, optional
        Pension-fee-premium tick values. Defaults to the provided edges.

    Returns
    -------
    Any
        Matplotlib figure containing the fee-return sensitivity heatmap.
    """
    fee_return_grid = fee_return_sensitivity.pivot_table(
        index="pension_fee_premium",
        columns="expected_return",
        values="pension_advantage",
    )
    fee_return_values = fee_return_grid.to_numpy()
    color_limit = _symmetric_color_limit(fee_return_values)

    fig, ax = plt.subplots(figsize=(8, 5))
    if expected_return_edges is not None and pension_fee_premium_edges is not None:
        image = ax.pcolormesh(
            expected_return_edges,
            pension_fee_premium_edges,
            fee_return_values,
            cmap="RdYlGn",
            shading="flat",
            vmin=-color_limit,
            vmax=color_limit,
        )
        add_sign_boundary(
            ax,
            expected_return_edges,
            pension_fee_premium_edges,
            fee_return_values,
        )
        ax.set_xticks(
            expected_return_ticks if expected_return_ticks is not None else expected_return_edges
        )
        ax.set_yticks(
            pension_fee_premium_ticks
            if pension_fee_premium_ticks is not None
            else pension_fee_premium_edges
        )
        ax.set_xticklabels([f"{value:.1%}" for value in ax.get_xticks()])
        ax.set_yticklabels([f"{value:.2%}" for value in ax.get_yticks()])
    else:
        image = ax.imshow(
            fee_return_values,
            aspect="auto",
            cmap="RdYlGn",
            vmin=-color_limit,
            vmax=color_limit,
        )
        ax.set_xticks(
            range(len(fee_return_grid.columns)),
            [f"{value:.1%}" for value in fee_return_grid.columns],
        )
        ax.set_yticks(
            range(len(fee_return_grid.index)),
            [f"{value:.2%}" for value in fee_return_grid.index],
        )

    ax.set_title(title)
    ax.set_xlabel("Rentabilidad anual esperada")
    ax.set_ylabel("Sobrecoste de comisión del plan")
    fig.colorbar(image, ax=ax, label=colorbar_label)
    return fig
