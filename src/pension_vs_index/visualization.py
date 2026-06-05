"""Reusable visualization helpers for pension-vs-index analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.ticker import FuncFormatter, NullFormatter

if TYPE_CHECKING:
    import pandas as pd
    from matplotlib.axes import Axes

EURO_MILLION = 1_000_000
EURO_THOUSAND = 1_000
REGULAR_INDEX_FUND_LABEL = "Fondo de inversión"
PENSION_PLAN_LABEL = "Plan de pensiones"


def format_euros(value: float, _position: int | None = None) -> str:
    """Format euro-denominated chart ticks with compact suffixes."""
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
    """Apply compact euro formatting to one axis."""
    if ticks is not None:
        getattr(ax, f"set_{axis}ticks")(ticks)
    axis_obj = getattr(ax, f"{axis}axis")
    axis_obj.set_major_formatter(EURO_FORMATTER)
    axis_obj.set_minor_formatter(NullFormatter())
    ax.tick_params(axis=axis, rotation=0)


def plot_accumulation_history(history: pd.DataFrame) -> Any:
    """Plot pre-withdrawal portfolio value over time for each vehicle."""
    fig, ax = plt.subplots(figsize=(9, 5))
    for vehicle, rows in history.groupby("vehicle"):
        ax.plot(rows["year"], rows["pre_withdrawal_value"], marker="o", label=vehicle)
    ax.set_title("Valor acumulado antes del rescate")
    ax.set_xlabel("Año de inversión")
    ax.set_ylabel("Valor de la cartera")
    apply_money_axis(ax, "y")
    ax.legend()
    return fig


def plot_lump_sum_results(lump_sum: pd.DataFrame) -> Any:
    """Plot after-tax lump-sum results and liquidation breakdown."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    lump_sum.plot.bar(
        x="vehicle",
        y="final_after_tax_money",
        ax=axes[0],
        legend=False,
        color=["#4c78a8", "#f58518"],
    )
    axes[0].set_title("Dinero neto final")
    axes[0].set_xlabel("Vehículo")
    axes[0].set_ylabel("Dinero disponible")
    apply_money_axis(axes[0], "y")
    axes[0].tick_params(axis="x", rotation=0)

    stacked = lump_sum.set_index("vehicle")[
        ["final_after_tax_money", "extraction_tax", "extraction_fees"]
    ]
    stacked.plot.bar(stacked=True, ax=axes[1], color=["#54a24b", "#e45756", "#b279a2"])
    axes[1].set_title("Desglose del rescate total")
    axes[1].set_xlabel("Vehículo")
    axes[1].set_ylabel("Rescate bruto")
    apply_money_axis(axes[1], "y")
    axes[1].tick_params(axis="x", rotation=0)
    axes[1].legend(loc="best")

    fig.tight_layout()
    return fig


def plot_extraction_comparison_breakdown(
    extraction_results: pd.DataFrame,
    *,
    title: str,
    figsize: tuple[float, float] = (11, 5),
) -> Any:
    """Plot gross extraction split into after-tax money, taxes, and fees."""
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


def plot_partial_withdrawal_results(
    partial_withdrawals: pd.DataFrame,
    gross_withdrawal_amounts: list[float],
) -> Any:
    """Plot net cash, effective rate, and pension advantage for gross withdrawals."""
    partial_advantage = _pension_advantage_table(
        partial_withdrawals,
        value_column="net_received",
        index_column="requested_gross_withdrawal",
    )

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for vehicle, rows in partial_withdrawals.groupby("vehicle"):
        axes[0].plot(
            rows["requested_gross_withdrawal"],
            rows["net_received"],
            marker="o",
            label=vehicle,
        )
        axes[1].plot(
            rows["requested_gross_withdrawal"],
            rows["effective_tax_rate"],
            marker="o",
            label=vehicle,
        )

    axes[0].set_title("Dinero neto por rescate bruto")
    axes[0].set_xlabel("Rescate bruto (EUR)")
    apply_money_axis(axes[0], "x", gross_withdrawal_amounts)
    axes[0].set_ylabel("Dinero neto")
    apply_money_axis(axes[0], "y")
    axes[0].legend()

    axes[1].set_title("Tipo efectivo de impuestos y comisiones")
    axes[1].set_xlabel("Rescate bruto (EUR)")
    apply_money_axis(axes[1], "x", gross_withdrawal_amounts)
    axes[1].set_ylabel("Tipo efectivo")
    axes[1].legend()

    axes[2].bar(
        partial_advantage["requested_gross_withdrawal"],
        partial_advantage["pension_advantage"],
        width=2_500,
    )
    axes[2].axhline(0, color="black", linewidth=1)
    axes[2].set_title("Ventaja del plan por tamaño de rescate")
    axes[2].set_xlabel("Rescate bruto (EUR)")
    apply_money_axis(axes[2], "x", gross_withdrawal_amounts)
    axes[2].set_ylabel("Diferencia de dinero neto")
    apply_money_axis(axes[2], "y")

    fig.tight_layout()
    return fig


def plot_target_net_pressure_results(
    target_net_pressure: pd.DataFrame,
    target_net_withdrawal_amounts: list[float],
) -> Any:
    """Plot asset pressure required to deliver target net withdrawals."""
    asset_pressure = _pension_advantage_table(
        target_net_pressure,
        value_column="percentage_of_assets_liquidated",
        index_column="target_net_withdrawal",
    )
    asset_pressure = asset_pressure.rename(
        columns={"pension_advantage": "pension_extra_asset_pressure"}
    )

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for vehicle, rows in target_net_pressure.groupby("vehicle"):
        axes[0].plot(
            rows["target_net_withdrawal"],
            rows["percentage_of_assets_liquidated"],
            marker="o",
            label=vehicle,
        )

    axes[0].set_title("Cartera necesaria para obtener un neto objetivo")
    axes[0].set_xlabel("Rescate neto objetivo (EUR)")
    apply_money_axis(axes[0], "x", target_net_withdrawal_amounts)
    axes[0].set_ylabel("Cartera liquidada")
    axes[0].legend()

    axes[1].bar(
        asset_pressure["target_net_withdrawal"],
        asset_pressure["pension_extra_asset_pressure"],
        width=2_500,
    )
    axes[1].axhline(0, color="black", linewidth=1)
    axes[1].set_title("Cartera adicional exigida por el plan")
    axes[1].set_xlabel("Rescate neto objetivo (EUR)")
    apply_money_axis(axes[1], "x", target_net_withdrawal_amounts)
    axes[1].set_ylabel("Plan menos fondo")

    fig.tight_layout()
    return fig


def plot_horizon_sensitivity_results(
    horizon_results: pd.DataFrame,
    horizon_advantage: pd.DataFrame,
) -> Any:
    """Plot final after-tax money and pension advantage by investment horizon."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for vehicle, rows in horizon_results.groupby("vehicle"):
        axes[0].plot(rows["years"], rows["final_after_tax_money"], label=vehicle)

    axes[0].set_title("Dinero neto final por horizonte")
    axes[0].set_xlabel("Horizonte de inversión (años)")
    axes[0].set_ylabel("Dinero neto final")
    apply_money_axis(axes[0], "y")
    axes[0].legend()

    axes[1].plot(
        horizon_advantage["years"],
        horizon_advantage["pension_advantage"],
        color="#f58518",
    )
    axes[1].axhline(0, color="black", linewidth=1)
    axes[1].set_title("Ventaja del plan por horizonte")
    axes[1].set_xlabel("Horizonte de inversión (años)")
    axes[1].set_ylabel("Diferencia neta después de impuestos")
    apply_money_axis(axes[1], "y")

    fig.tight_layout()
    return fig


def add_sign_boundary(
    ax: Axes,
    x_edges: list[float],
    y_edges: list[float],
    values: Any,
) -> None:
    """Draw grid-cell boundaries where values change sign."""
    positive_cells = values > 0
    boundary_segments = []
    for row in range(positive_cells.shape[0]):
        for column in range(positive_cells.shape[1] - 1):
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
    """Plot one salary-pair pension-advantage heatmap panel."""
    axis_data = axes_by_scenario[scenario["name"]]
    salary_grid = salary_data[salary_data["scenario"] == scenario["name"]].pivot_table(
        index="withdrawal_salary",
        columns="contribution_salary",
        values="pension_advantage",
    )
    salary_values = salary_grid.to_numpy()
    max_value = salary_values.max()
    min_value = salary_values.min()
    color_limit = max_value if abs(max_value) >= abs(min_value) else abs(min_value)
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
    ax.set_xlabel("Salario durante aportación (EUR)")
    ax.set_ylabel("Pensión pública / ingresos (EUR)")
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
    """Plot a row of salary-pair heatmap panels."""
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
    """Plot pension advantage by expected return and pension fee premium."""
    fee_return_grid = fee_return_sensitivity.pivot_table(
        index="pension_fee_premium",
        columns="expected_return",
        values="pension_advantage",
    )
    fee_return_values = fee_return_grid.to_numpy()
    max_value = fee_return_values.max()
    min_value = fee_return_values.min()
    color_limit = max_value if abs(max_value) >= abs(min_value) else abs(min_value)

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


def _pension_advantage_table(
    results: pd.DataFrame,
    *,
    value_column: str,
    index_column: str,
) -> pd.DataFrame:
    wide = results.pivot_table(index=index_column, columns="vehicle", values=value_column)
    wide["pension_advantage"] = wide[PENSION_PLAN_LABEL] - wide[REGULAR_INDEX_FUND_LABEL]
    return wide.reset_index()
