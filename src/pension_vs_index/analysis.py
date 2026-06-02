"""Reusable analysis routines for comparing pension plans and index funds."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

import pandas as pd

from pension_vs_index.investment_vehicles.index_fund import IndexFund
from pension_vs_index.taxing_entity.hacienda_espanola import HaciendaEspanola

REGULAR_INDEX_FUND_LABEL = "Regular index fund"
PENSION_PLAN_LABEL = "Plan de pensiones"
VEHICLE_LABELS = (REGULAR_INDEX_FUND_LABEL, PENSION_PLAN_LABEL)

GROSS_SALARY_DURING_CONTRIBUTION = 60_000.0
EXISTING_GROSS_SALARY_DURING_WITHDRAWAL = 35_000.0
ANNUAL_CONTRIBUTION = 1_500.0
INVESTMENT_HORIZON_YEARS = 25

EXPECTED_ANNUAL_RETURN = 0.06
ANNUAL_RETURN_VOLATILITY = 0.0

REGULAR_FUND_ANNUAL_FEE = 0.0012
PENSION_PLAN_ANNUAL_FEE = 0.0040

REGULAR_ENTRY_FEE = 0.0
REGULAR_EXIT_FEE = 0.0
PENSION_ENTRY_FEE = 0.0
PENSION_EXIT_FEE = 0.0


@dataclass(frozen=True)
class ScenarioConfig:
    """Inputs for one pension-vs-index comparison scenario."""

    gross_salary_during_contribution: float = GROSS_SALARY_DURING_CONTRIBUTION
    existing_gross_salary_during_withdrawal: float = EXISTING_GROSS_SALARY_DURING_WITHDRAWAL
    annual_contribution: float = ANNUAL_CONTRIBUTION
    investment_horizon_years: int = INVESTMENT_HORIZON_YEARS
    contribution_years: int | None = None
    expected_annual_return: float = EXPECTED_ANNUAL_RETURN
    annual_return_volatility: float = ANNUAL_RETURN_VOLATILITY
    regular_fund_annual_fee: float = REGULAR_FUND_ANNUAL_FEE
    pension_plan_annual_fee: float = PENSION_PLAN_ANNUAL_FEE
    regular_entry_fee: float = REGULAR_ENTRY_FEE
    regular_exit_fee: float = REGULAR_EXIT_FEE
    pension_entry_fee: float = PENSION_ENTRY_FEE
    pension_exit_fee: float = PENSION_EXIT_FEE


def make_vehicle(label: str, config: ScenarioConfig) -> IndexFund:
    """Build the investment vehicle for a notebook scenario label."""
    if label == REGULAR_INDEX_FUND_LABEL:
        return IndexFund(
            annual_avg_return=config.expected_annual_return,
            annual_return_std=config.annual_return_volatility,
            annual_fee=config.regular_fund_annual_fee,
            entry_fee=config.regular_entry_fee,
            exit_fee=config.regular_exit_fee,
            tags=[],
        )

    if label == PENSION_PLAN_LABEL:
        return IndexFund(
            annual_avg_return=config.expected_annual_return,
            annual_return_std=config.annual_return_volatility,
            annual_fee=config.pension_plan_annual_fee,
            entry_fee=config.pension_entry_fee,
            exit_fee=config.pension_exit_fee,
            tags=["plan_de_pensiones"],
        )

    msg = f"Unknown vehicle label: {label}"
    raise ValueError(msg)


def simulate_accumulation(label: str, config: ScenarioConfig) -> tuple[IndexFund, pd.DataFrame]:
    """Simulate yearly contributions and growth for one vehicle."""
    tax_entity = HaciendaEspanola()
    vehicle = make_vehicle(label, config)
    rows = []
    contribution_years = (
        config.investment_horizon_years
        if config.contribution_years is None
        else config.contribution_years
    )
    if not 0 <= contribution_years <= config.investment_horizon_years:
        msg = "contribution_years must be between 0 and investment_horizon_years."
        raise ValueError(msg)

    cumulative_gross_contributed = 0.0
    cumulative_invested = 0.0
    cumulative_contribution_tax = 0.0
    cumulative_fees = 0.0

    for year in range(1, config.investment_horizon_years + 1):
        invested_amount = 0.0
        tax_amount = 0.0
        fee_amount = 0.0
        if year <= contribution_years:
            invested_amount, tax_amount, fee_amount = vehicle.add_contribution(
                amount=config.annual_contribution,
                taxing_entity=tax_entity,
                gross_salary_during_contribution=config.gross_salary_during_contribution,
            )
        vehicle.pass_year()

        if year <= contribution_years:
            cumulative_gross_contributed += config.annual_contribution
        cumulative_invested += invested_amount
        cumulative_contribution_tax += tax_amount
        cumulative_fees += fee_amount

        rows.append(
            {
                "vehicle": label,
                "year": year,
                "gross_contributed": cumulative_gross_contributed,
                "invested_amount": cumulative_invested,
                "contribution_tax": cumulative_contribution_tax,
                "fees": cumulative_fees,
                "pre_withdrawal_value": vehicle.total,
            }
        )

    return vehicle, pd.DataFrame(rows)


def simulate_all_accumulation(config: ScenarioConfig) -> tuple[dict[str, IndexFund], pd.DataFrame]:
    """Simulate yearly accumulation for the regular fund and pension plan."""
    vehicles = {}
    histories = []
    for label in VEHICLE_LABELS:
        vehicle, history = simulate_accumulation(label, config)
        vehicles[label] = vehicle
        histories.append(history)

    return vehicles, pd.concat(histories, ignore_index=True)


def accumulation_summary(history: pd.DataFrame) -> pd.DataFrame:
    """Return one final accumulation row per vehicle."""
    return (
        history.sort_values("year")
        .groupby("vehicle", as_index=False)
        .tail(1)
        .loc[
            :,
            [
                "vehicle",
                "gross_contributed",
                "invested_amount",
                "contribution_tax",
                "fees",
                "pre_withdrawal_value",
            ],
        ]
        .sort_values("vehicle")
        .reset_index(drop=True)
    )


def calculate_gross_withdrawal(
    vehicle: IndexFund,
    gross_withdrawal: float,
    config: ScenarioConfig,
) -> tuple[float, float, float]:
    """Calculate net money, tax, and fees for a gross withdrawal without mutating holdings."""
    available_amount = sum(
        contribution.amount_left(vehicle.current_value) for contribution in vehicle.contributions
    )
    gross_withdrawal = min(gross_withdrawal, available_amount)
    if gross_withdrawal > 0 and math.isclose(gross_withdrawal, available_amount):
        gross_withdrawal = available_amount * (1 - 1e-12)
    tax_entity = HaciendaEspanola()
    fee_amount = vehicle._percentage_fee(  # noqa: SLF001
        amount=gross_withdrawal,
        fee_rate=vehicle.exit_fee,
        min_fee=vehicle.min_exit_fee,
    )
    tax_amount = tax_entity.calculate_gross_extraction_tax(
        gross_amount=gross_withdrawal,
        gross_annual_salary=config.existing_gross_salary_during_withdrawal,
        contributions=vehicle.contributions,
        current_price=vehicle.current_value,
        tags=vehicle.tags.copy(),
        fee_amount=fee_amount,
    )
    net_amount = gross_withdrawal - tax_amount - fee_amount
    return net_amount, tax_amount, fee_amount


def liquidate_lump_sum(label: str, config: ScenarioConfig) -> dict[str, float | str]:
    """Liquidate one vehicle and return the end-of-period result row."""
    vehicle, history = simulate_accumulation(label, config)
    gross_value = vehicle.total
    net_amount, tax_amount, fee_amount = calculate_gross_withdrawal(vehicle, gross_value, config)
    final_row = history.iloc[-1]
    effective_after_tax_cagr = (net_amount / final_row["gross_contributed"]) ** (
        1 / config.investment_horizon_years
    ) - 1

    return {
        "vehicle": label,
        "gross_contributed": final_row["gross_contributed"],
        "pre_withdrawal_value": gross_value,
        "gross_extraction": gross_value,
        "extraction_tax": tax_amount,
        "extraction_fees": fee_amount,
        "final_after_tax_money": net_amount,
        "effective_after_tax_cagr": effective_after_tax_cagr,
    }


def lump_sum_results(config: ScenarioConfig) -> pd.DataFrame:
    """Return full-liquidation results for both vehicles."""
    return pd.DataFrame([liquidate_lump_sum(label, config) for label in VEHICLE_LABELS])


def liquidate_percentage(
    label: str,
    config: ScenarioConfig,
    withdrawal_rate: float,
) -> dict[str, float | str]:
    """Withdraw a gross percentage of one vehicle and return the result row."""
    vehicle, history = simulate_accumulation(label, config)
    pre_withdrawal_value = vehicle.total
    gross_extraction = pre_withdrawal_value * withdrawal_rate
    net_amount, tax_amount, fee_amount = calculate_gross_withdrawal(
        vehicle,
        gross_extraction,
        config,
    )
    final_row = history.iloc[-1]

    return {
        "vehicle": label,
        "gross_contributed": final_row["gross_contributed"],
        "pre_withdrawal_value": pre_withdrawal_value,
        "withdrawal_rate": withdrawal_rate,
        "gross_extraction": gross_extraction,
        "extraction_tax": tax_amount,
        "extraction_fees": fee_amount,
        "net_received": net_amount,
        "effective_tax_rate": (tax_amount + fee_amount) / gross_extraction
        if gross_extraction
        else 0.0,
    }


def percentage_withdrawal_results(config: ScenarioConfig, withdrawal_rate: float) -> pd.DataFrame:
    """Return percentage-withdrawal results for both vehicles."""
    return pd.DataFrame(
        [liquidate_percentage(label, config, withdrawal_rate) for label in VEHICLE_LABELS]
    )


def normalize_lump_sum_extraction_results(
    results: pd.DataFrame,
    *,
    scenario_name: str,
) -> pd.DataFrame:
    """Normalize lump-sum results for extraction decomposition plots."""
    return pd.DataFrame(
        [
            {
                "scenario": scenario_name,
                "extraction_mode": "Lump sum",
                "withdrawal_rate": None,
                "vehicle": row["vehicle"],
                "gross_contributed": row["gross_contributed"],
                "pre_withdrawal_value": row["pre_withdrawal_value"],
                "gross_extraction": row["gross_extraction"],
                "after_tax_money": row["final_after_tax_money"],
                "extraction_tax": row["extraction_tax"],
                "extraction_fees": row["extraction_fees"],
                "effective_tax_rate": (row["extraction_tax"] + row["extraction_fees"])
                / row["gross_extraction"]
                if row["gross_extraction"]
                else 0.0,
            }
            for row in results.to_dict("records")
        ]
    )


def normalize_percentage_extraction_results(
    results: pd.DataFrame,
    *,
    scenario_name: str,
) -> pd.DataFrame:
    """Normalize percentage-withdrawal results for extraction decomposition plots."""
    return pd.DataFrame(
        [
            {
                "scenario": scenario_name,
                "extraction_mode": f"{row['withdrawal_rate']:.0%} extraction",
                "withdrawal_rate": row["withdrawal_rate"],
                "vehicle": row["vehicle"],
                "gross_contributed": row["gross_contributed"],
                "pre_withdrawal_value": row["pre_withdrawal_value"],
                "gross_extraction": row["gross_extraction"],
                "after_tax_money": row["net_received"],
                "extraction_tax": row["extraction_tax"],
                "extraction_fees": row["extraction_fees"],
                "effective_tax_rate": row["effective_tax_rate"],
            }
            for row in results.to_dict("records")
        ]
    )


def lump_sum_extraction_comparison_results(
    scenario_configs: dict[str, ScenarioConfig],
) -> pd.DataFrame:
    """Return normalized lump-sum extraction results for multiple named scenarios."""
    rows = []
    for scenario_name, config in scenario_configs.items():
        result = lump_sum_results(config)
        rows.extend(
            {
                "scenario": scenario_name,
                "annual_contribution": config.annual_contribution,
                "extraction_mode": "Lump sum",
                "withdrawal_rate": None,
                "vehicle": row["vehicle"],
                "gross_contributed": row["gross_contributed"],
                "pre_withdrawal_value": row["pre_withdrawal_value"],
                "gross_extraction": row["gross_extraction"],
                "after_tax_money": row["final_after_tax_money"],
                "extraction_tax": row["extraction_tax"],
                "extraction_fees": row["extraction_fees"],
                "effective_tax_rate": (row["extraction_tax"] + row["extraction_fees"])
                / row["gross_extraction"]
                if row["gross_extraction"]
                else 0.0,
            }
            for row in result.to_dict("records")
        )

    return pd.DataFrame(rows)


def percentage_extraction_comparison_results(
    scenario_configs: dict[str, ScenarioConfig],
    withdrawal_rate: float,
) -> pd.DataFrame:
    """Return normalized percentage extraction results for multiple named scenarios."""
    rows = []
    for scenario_name, config in scenario_configs.items():
        result = percentage_withdrawal_results(config, withdrawal_rate)
        rows.extend(
            {
                "scenario": scenario_name,
                "annual_contribution": config.annual_contribution,
                "extraction_mode": f"{withdrawal_rate:.0%} extraction",
                "withdrawal_rate": withdrawal_rate,
                "vehicle": row["vehicle"],
                "gross_contributed": row["gross_contributed"],
                "pre_withdrawal_value": row["pre_withdrawal_value"],
                "gross_extraction": row["gross_extraction"],
                "after_tax_money": row["net_received"],
                "extraction_tax": row["extraction_tax"],
                "extraction_fees": row["extraction_fees"],
                "effective_tax_rate": row["effective_tax_rate"],
            }
            for row in result.to_dict("records")
        )

    return pd.DataFrame(rows)


def working_retirement_salary_sensitivity_results(
    scenario_configs: dict[str, ScenarioConfig],
    heatmap_parameters: dict[str, dict[str, Any]],
    *,
    steps: int,
    min_model_gross_salary: float = 1.0,
    withdrawal_rate: float | None = None,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """Calculate pension advantage by working-years salary and retirement salary."""
    axes_by_scenario = {}
    rows = []
    for scenario_name, config in scenario_configs.items():
        parameters = heatmap_parameters[scenario_name]
        contribution_salary_sweep = linear_spaced_values(
            parameters["contribution_salary_min"],
            parameters["contribution_salary_max"],
            steps,
        )
        withdrawal_salary_sweep = linear_spaced_values(
            parameters["withdrawal_salary_min"],
            parameters["withdrawal_salary_max"],
            steps,
        )
        axes_by_scenario[scenario_name] = {
            "scenario": {"name": scenario_name, **parameters},
            "contribution_salary_sweep": contribution_salary_sweep,
            "withdrawal_salary_sweep": withdrawal_salary_sweep,
            "contribution_salary_edges": linear_cell_edges(
                parameters["contribution_salary_min"],
                parameters["contribution_salary_max"],
                steps,
            ),
            "withdrawal_salary_edges": linear_cell_edges(
                parameters["withdrawal_salary_min"],
                parameters["withdrawal_salary_max"],
                steps,
            ),
        }

        for contribution_salary in contribution_salary_sweep:
            contribution_config = replace(
                config,
                gross_salary_during_contribution=max(
                    contribution_salary,
                    min_model_gross_salary,
                ),
            )
            for withdrawal_salary in withdrawal_salary_sweep:
                scenario_config = replace(
                    contribution_config,
                    existing_gross_salary_during_withdrawal=max(
                        withdrawal_salary,
                        min_model_gross_salary,
                    ),
                )
                if withdrawal_rate is None:
                    result = final_after_tax_for_config(scenario_config)
                    value_column = "final_after_tax_money"
                else:
                    result = percentage_withdrawal_results(scenario_config, withdrawal_rate)
                    value_column = "net_received"
                wide = result.pivot_table(columns="vehicle", values=value_column, aggfunc="first")
                rows.append(
                    {
                        "scenario": scenario_name,
                        "annual_contribution": config.annual_contribution,
                        "withdrawal_rate": withdrawal_rate,
                        "contribution_salary": contribution_salary,
                        "withdrawal_salary": withdrawal_salary,
                        "pension_advantage": wide[PENSION_PLAN_LABEL].iloc[0]
                        - wide[REGULAR_INDEX_FUND_LABEL].iloc[0],
                    }
                )

    return pd.DataFrame(rows), axes_by_scenario


def partial_withdrawal_results(
    config: ScenarioConfig,
    gross_withdrawals: list[float],
) -> pd.DataFrame:
    """Return independent gross-withdrawal rows for each requested amount."""
    rows = []
    for label in VEHICLE_LABELS:
        for requested_gross_withdrawal in gross_withdrawals:
            vehicle, _history = simulate_accumulation(label, config)
            gross_withdrawal = min(requested_gross_withdrawal, vehicle.total)
            net_amount, tax_amount, fee_amount = calculate_gross_withdrawal(
                vehicle,
                gross_withdrawal,
                config,
            )
            effective_tax_rate = (
                (tax_amount + fee_amount) / gross_withdrawal if gross_withdrawal else 0.0
            )
            rows.append(
                {
                    "vehicle": label,
                    "requested_gross_withdrawal": requested_gross_withdrawal,
                    "gross_withdrawal": gross_withdrawal,
                    "net_received": net_amount,
                    "tax_paid": tax_amount,
                    "fees_paid": fee_amount,
                    "effective_tax_rate": effective_tax_rate,
                    "existing_gross_salary": config.existing_gross_salary_during_withdrawal,
                }
            )

    return pd.DataFrame(rows)


def gross_withdrawal_for_target_net(
    vehicle: IndexFund,
    target_net_withdrawal: float,
    config: ScenarioConfig,
) -> tuple[float, float, float, bool]:
    """Find the gross withdrawal needed to deliver a target net withdrawal."""
    available_amount = sum(
        contribution.amount_left(vehicle.current_value) for contribution in vehicle.contributions
    )
    max_gross_withdrawal = available_amount * (1 - 1e-12)
    max_net_withdrawal, max_tax_amount, max_fee_amount = calculate_gross_withdrawal(
        vehicle,
        max_gross_withdrawal,
        config,
    )
    if target_net_withdrawal > max_net_withdrawal:
        return max_gross_withdrawal, max_tax_amount, max_fee_amount, False

    low = 0.0
    high = max_gross_withdrawal
    tax_amount = 0.0
    fee_amount = 0.0
    for _ in range(80):
        midpoint = (low + high) / 2
        net_amount, tax_amount, fee_amount = calculate_gross_withdrawal(vehicle, midpoint, config)
        if net_amount < target_net_withdrawal:
            low = midpoint
        else:
            high = midpoint

    gross_withdrawal = high
    _net_amount, tax_amount, fee_amount = calculate_gross_withdrawal(
        vehicle,
        gross_withdrawal,
        config,
    )
    return gross_withdrawal, tax_amount, fee_amount, True


def target_net_withdrawal_pressure_results(
    config: ScenarioConfig,
    target_net_withdrawals: list[float],
) -> pd.DataFrame:
    """Calculate asset pressure required to deliver each target net withdrawal."""
    rows = []
    for label in VEHICLE_LABELS:
        for target_net_withdrawal in target_net_withdrawals:
            vehicle, _history = simulate_accumulation(label, config)
            pre_withdrawal_value = vehicle.total
            gross_withdrawal, tax_amount, fee_amount, feasible = gross_withdrawal_for_target_net(
                vehicle,
                target_net_withdrawal,
                config,
            )
            net_received = gross_withdrawal - tax_amount - fee_amount
            rows.append(
                {
                    "vehicle": label,
                    "target_net_withdrawal": target_net_withdrawal,
                    "feasible": feasible,
                    "pre_withdrawal_value": pre_withdrawal_value,
                    "gross_withdrawal_required": gross_withdrawal,
                    "net_received": net_received,
                    "tax_paid": tax_amount,
                    "fees_paid": fee_amount,
                    "percentage_of_assets_liquidated": gross_withdrawal / pre_withdrawal_value
                    if pre_withdrawal_value
                    else 0.0,
                    "existing_gross_salary": config.existing_gross_salary_during_withdrawal,
                }
            )

    return pd.DataFrame(rows)


def pension_advantage_table(
    results: pd.DataFrame,
    value_column: str,
    index_column: str,
) -> pd.DataFrame:
    """Calculate pension-minus-regular advantage for a result table."""
    wide = results.pivot_table(index=index_column, columns="vehicle", values=value_column)
    wide["pension_advantage"] = wide[PENSION_PLAN_LABEL] - wide[REGULAR_INDEX_FUND_LABEL]
    return wide.reset_index()


def final_after_tax_for_config(config: ScenarioConfig) -> pd.DataFrame:
    """Return only the final after-tax money column for a scenario."""
    return lump_sum_results(config).loc[:, ["vehicle", "final_after_tax_money"]]


def horizon_sensitivity_results(
    base_config: ScenarioConfig,
    horizon_years: list[int],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate final after-tax money and pension advantage across investment horizons."""
    rows = []
    for years in horizon_years:
        result = final_after_tax_for_config(replace(base_config, investment_horizon_years=years))
        result["years"] = years
        rows.append(result)

    horizon_results = pd.concat(rows, ignore_index=True)
    horizon_advantage = pension_advantage_table(horizon_results, "final_after_tax_money", "years")
    return horizon_results, horizon_advantage


def salary_heatmap_settings(
    scenarios: list[dict[str, Any]],
    steps: int,
) -> pd.DataFrame:
    """Summarize salary heatmap grid settings for display in the notebook."""
    settings = pd.DataFrame(
        [
            {
                "annual_contribution": scenario["annual_contribution"],
                "scenario": scenario["name"],
                "contribution_salary_min": scenario["contribution_salary_min"],
                "contribution_salary_max": scenario["contribution_salary_max"],
                "withdrawal_salary_min": scenario["withdrawal_salary_min"],
                "withdrawal_salary_max": scenario["withdrawal_salary_max"],
                "salary_scale": "linear",
                "grid_points_per_axis": steps,
                "salary_pairs": steps**2,
            }
            for scenario in scenarios
        ]
    )
    settings["total_scenarios"] = settings["salary_pairs"]
    return settings


def salary_heatmap_axes(
    scenarios: list[dict[str, Any]],
    steps: int,
) -> dict[str, dict[str, Any]]:
    """Build salary heatmap axis sweeps and cell edges for each scenario."""
    axes_by_scenario = {}
    for scenario in scenarios:
        axes_by_scenario[scenario["name"]] = {
            "scenario": scenario,
            "contribution_salary_sweep": linear_spaced_values(
                scenario["contribution_salary_min"],
                scenario["contribution_salary_max"],
                steps,
            ),
            "withdrawal_salary_sweep": linear_spaced_values(
                scenario["withdrawal_salary_min"],
                scenario["withdrawal_salary_max"],
                steps,
            ),
            "contribution_salary_edges": linear_cell_edges(
                scenario["contribution_salary_min"],
                scenario["contribution_salary_max"],
                steps,
            ),
            "withdrawal_salary_edges": linear_cell_edges(
                scenario["withdrawal_salary_min"],
                scenario["withdrawal_salary_max"],
                steps,
            ),
        }
    return axes_by_scenario


def salary_lump_sum_sensitivity_results(
    base_config: ScenarioConfig,
    scenarios: list[dict[str, Any]],
    steps: int,
    *,
    min_model_gross_salary: float = 1.0,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """Calculate lump-sum pension advantage over contribution and withdrawal salary pairs."""
    axes_by_scenario = salary_heatmap_axes(scenarios, steps)
    rows = []
    for scenario in scenarios:
        axis_data = axes_by_scenario[scenario["name"]]
        for contribution_salary in axis_data["contribution_salary_sweep"]:
            for withdrawal_salary in axis_data["withdrawal_salary_sweep"]:
                config = replace(
                    base_config,
                    gross_salary_during_contribution=max(
                        contribution_salary,
                        min_model_gross_salary,
                    ),
                    existing_gross_salary_during_withdrawal=withdrawal_salary,
                    annual_contribution=scenario["annual_contribution"],
                )
                result = final_after_tax_for_config(config)
                wide = result.pivot_table(
                    columns="vehicle",
                    values="final_after_tax_money",
                    aggfunc="first",
                )
                rows.append(
                    {
                        "annual_contribution": scenario["annual_contribution"],
                        "scenario": scenario["name"],
                        "contribution_salary": contribution_salary,
                        "withdrawal_salary": withdrawal_salary,
                        "pension_advantage": wide[PENSION_PLAN_LABEL].iloc[0]
                        - wide[REGULAR_INDEX_FUND_LABEL].iloc[0],
                    }
                )

    return pd.DataFrame(rows), axes_by_scenario


def salary_percentage_withdrawal_sensitivity_results(
    base_config: ScenarioConfig,
    scenarios: list[dict[str, Any]],
    steps: int,
    withdrawal_rate: float,
    *,
    min_model_gross_salary: float = 1.0,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """Calculate net pension advantage for a percentage withdrawal over salary pairs."""
    axes_by_scenario = salary_heatmap_axes(scenarios, steps)
    rows = []
    for scenario in scenarios:
        axis_data = axes_by_scenario[scenario["name"]]
        for contribution_salary in axis_data["contribution_salary_sweep"]:
            for withdrawal_salary in axis_data["withdrawal_salary_sweep"]:
                config = replace(
                    base_config,
                    gross_salary_during_contribution=max(
                        contribution_salary,
                        min_model_gross_salary,
                    ),
                    existing_gross_salary_during_withdrawal=withdrawal_salary,
                    annual_contribution=scenario["annual_contribution"],
                )
                result = percentage_withdrawal_results(config, withdrawal_rate)
                wide = result.pivot_table(columns="vehicle", values="net_received", aggfunc="first")
                rows.append(
                    {
                        "annual_contribution": scenario["annual_contribution"],
                        "scenario": scenario["name"],
                        "contribution_salary": contribution_salary,
                        "withdrawal_salary": withdrawal_salary,
                        "pension_advantage": wide[PENSION_PLAN_LABEL].iloc[0]
                        - wide[REGULAR_INDEX_FUND_LABEL].iloc[0],
                    }
                )

    return pd.DataFrame(rows), axes_by_scenario


def fee_return_sensitivity_results(
    base_config: ScenarioConfig,
    expected_returns: list[float],
    pension_fee_premiums: list[float],
) -> pd.DataFrame:
    """Calculate pension advantage across expected returns and pension fee premiums."""
    rows = []
    for expected_return in expected_returns:
        for fee_premium in pension_fee_premiums:
            config = replace(
                base_config,
                expected_annual_return=expected_return,
                pension_plan_annual_fee=base_config.regular_fund_annual_fee + fee_premium,
            )
            result = final_after_tax_for_config(config)
            wide = result.pivot_table(
                columns="vehicle",
                values="final_after_tax_money",
                aggfunc="first",
            )
            rows.append(
                {
                    "expected_return": expected_return,
                    "pension_fee_premium": fee_premium,
                    "pension_advantage": wide[PENSION_PLAN_LABEL].iloc[0]
                    - wide[REGULAR_INDEX_FUND_LABEL].iloc[0],
                }
            )

    return pd.DataFrame(rows)


def percentage_fee_return_sensitivity_results(
    base_config: ScenarioConfig,
    expected_returns: list[float],
    pension_fee_premiums: list[float],
    withdrawal_rate: float,
) -> pd.DataFrame:
    """Calculate percentage-withdrawal pension advantage by return and fee premium."""
    rows = []
    for expected_return in expected_returns:
        for fee_premium in pension_fee_premiums:
            config = replace(
                base_config,
                expected_annual_return=expected_return,
                pension_plan_annual_fee=base_config.regular_fund_annual_fee + fee_premium,
            )
            result = percentage_withdrawal_results(config, withdrawal_rate)
            wide = result.pivot_table(columns="vehicle", values="net_received", aggfunc="first")
            rows.append(
                {
                    "withdrawal_rate": withdrawal_rate,
                    "expected_return": expected_return,
                    "pension_fee_premium": fee_premium,
                    "pension_advantage": wide[PENSION_PLAN_LABEL].iloc[0]
                    - wide[REGULAR_INDEX_FUND_LABEL].iloc[0],
                }
            )

    return pd.DataFrame(rows)


def percentage_fee_return_sensitivity_grid_results(
    base_config: ScenarioConfig,
    *,
    expected_return_min: float,
    expected_return_max: float,
    pension_fee_premium_min: float,
    pension_fee_premium_max: float,
    steps: int,
    withdrawal_rate: float,
) -> tuple[pd.DataFrame, dict[str, list[float]]]:
    """Calculate percentage-withdrawal pension advantage over a dense fee-return grid."""
    expected_returns = linear_spaced_values(expected_return_min, expected_return_max, steps)
    pension_fee_premiums = linear_spaced_values(
        pension_fee_premium_min,
        pension_fee_premium_max,
        steps,
    )
    sensitivity = percentage_fee_return_sensitivity_results(
        base_config,
        expected_returns=expected_returns,
        pension_fee_premiums=pension_fee_premiums,
        withdrawal_rate=withdrawal_rate,
    )
    axes = {
        "expected_return_edges": linear_cell_edges(expected_return_min, expected_return_max, steps),
        "pension_fee_premium_edges": linear_cell_edges(
            pension_fee_premium_min,
            pension_fee_premium_max,
            steps,
        ),
    }
    return sensitivity, axes


def linear_spaced_values(min_value: float, max_value: float, points: int) -> list[float]:
    """Return centered values for a linear grid."""
    step = (max_value - min_value) / points
    return [min_value + step * (index + 0.5) for index in range(points)]


def linear_cell_edges(min_value: float, max_value: float, points: int) -> list[float]:
    """Return cell edges for a linear grid."""
    step = (max_value - min_value) / points
    return [min_value + step * index for index in range(points + 1)]
