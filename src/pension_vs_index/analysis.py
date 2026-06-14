"""Reusable analysis routines for comparing pension plans and index funds."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

import pandas as pd

from pension_vs_index.investment_vehicles.index_fund import IndexFund
from pension_vs_index.taxing_entity.hacienda_espanola import HaciendaEspanola

REGULAR_INDEX_FUND_LABEL = "Fondo de inversión"
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
    """
    Inputs for one pension-vs-index comparison scenario.

    Attributes
    ----------
    gross_salary_during_contribution : float
        Gross annual salary while contributions are made.
    existing_gross_salary_during_withdrawal : float
        Gross annual income already present while withdrawals are made.
    annual_contribution : float
        Gross annual amount contributed to each investment vehicle.
    investment_horizon_years : int
        Number of years the investment is held.
    contribution_years : int | None
        Number of years with contributions. If None, contributions are made for the full horizon.
    expected_annual_return : float
        Expected annual gross return before recurring fees.
    annual_return_volatility : float
        Standard deviation of annual returns.
    regular_fund_annual_fee : float
        Annual recurring fee for the regular index fund.
    pension_plan_annual_fee : float
        Annual recurring fee for the pension plan.
    regular_entry_fee : float
        Percentage entry fee for the regular index fund.
    regular_exit_fee : float
        Percentage exit fee for the regular index fund.
    pension_entry_fee : float
        Percentage entry fee for the pension plan.
    pension_exit_fee : float
        Percentage exit fee for the pension plan.
    """

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
    """
    Build the investment vehicle for a notebook scenario label.

    Parameters
    ----------
    label : str
        Vehicle label to build. Must be one of ``VEHICLE_LABELS``.
    config : ScenarioConfig
        Scenario inputs used to configure returns, fees, and tax tags.

    Returns
    -------
    IndexFund
        Configured investment vehicle matching the requested label.

    Raises
    ------
    ValueError
        If ``label`` is not a known vehicle label.
    """
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
    """
    Simulate yearly contributions and growth for one vehicle.

    Parameters
    ----------
    label : str
        Vehicle label to simulate.
    config : ScenarioConfig
        Scenario inputs used for contributions, tax treatment, returns, and fees.

    Returns
    -------
    tuple[IndexFund, pd.DataFrame]
        The final vehicle object and a yearly accumulation history table.

    Raises
    ------
    ValueError
        If ``contribution_years`` is outside the investment horizon.
    """
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
    """
    Simulate yearly accumulation for the regular fund and pension plan.

    Parameters
    ----------
    config : ScenarioConfig
        Scenario inputs shared by both vehicles.

    Returns
    -------
    tuple[dict[str, IndexFund], pd.DataFrame]
        Vehicles keyed by label and a combined yearly accumulation history.
    """
    vehicles = {}
    histories = []
    for label in VEHICLE_LABELS:
        vehicle, history = simulate_accumulation(label, config)
        vehicles[label] = vehicle
        histories.append(history)

    return vehicles, pd.concat(histories, ignore_index=True)


def accumulation_summary(history: pd.DataFrame) -> pd.DataFrame:
    """
    Return one final accumulation row per vehicle.

    Parameters
    ----------
    history : pd.DataFrame
        Yearly accumulation history returned by ``simulate_all_accumulation``.

    Returns
    -------
    pd.DataFrame
        Final accumulation metrics for each vehicle.
    """
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
    """
    Calculate net money, tax, and fees for a gross withdrawal without mutating holdings.

    Parameters
    ----------
    vehicle : IndexFund
        Vehicle whose current holdings define the withdrawal tax base.
    gross_withdrawal : float
        Gross withdrawal requested before taxes and exit fees.
    config : ScenarioConfig
        Scenario inputs, including existing gross income during withdrawal.

    Returns
    -------
    tuple[float, float, float]
        Net amount received, tax paid, and exit fees paid.
    """
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
    """
    Liquidate one vehicle and return the end-of-period result row.

    Parameters
    ----------
    label : str
        Vehicle label to simulate and liquidate.
    config : ScenarioConfig
        Scenario inputs used for accumulation and withdrawal taxation.

    Returns
    -------
    dict[str, float | str]
        Result row with accumulation, extraction, tax, fee, and final net money fields.
    """
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
    """
    Return full-liquidation results for both vehicles.

    Parameters
    ----------
    config : ScenarioConfig
        Scenario inputs used for both vehicles.

    Returns
    -------
    pd.DataFrame
        Full-liquidation result table for the regular fund and pension plan.
    """
    return pd.DataFrame([liquidate_lump_sum(label, config) for label in VEHICLE_LABELS])


def liquidate_percentage(
    label: str,
    config: ScenarioConfig,
    withdrawal_rate: float,
) -> dict[str, float | str]:
    """
    Withdraw a gross percentage of one vehicle and return the result row.

    Parameters
    ----------
    label : str
        Vehicle label to simulate and withdraw from.
    config : ScenarioConfig
        Scenario inputs used for accumulation and withdrawal taxation.
    withdrawal_rate : float
        Gross percentage of pre-withdrawal portfolio value to withdraw.

    Returns
    -------
    dict[str, float | str]
        Result row with gross extraction, tax, fees, net money, and effective tax rate.
    """
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
    """
    Return percentage-withdrawal results for both vehicles.

    Parameters
    ----------
    config : ScenarioConfig
        Scenario inputs used for both vehicles.
    withdrawal_rate : float
        Gross percentage of pre-withdrawal portfolio value to withdraw.

    Returns
    -------
    pd.DataFrame
        Percentage-withdrawal result table for the regular fund and pension plan.
    """
    return pd.DataFrame(
        [liquidate_percentage(label, config, withdrawal_rate) for label in VEHICLE_LABELS]
    )


def normalize_lump_sum_extraction_results(
    results: pd.DataFrame,
    *,
    scenario_name: str,
) -> pd.DataFrame:
    """
    Normalize lump-sum results for extraction decomposition plots.

    Parameters
    ----------
    results : pd.DataFrame
        Full-liquidation result table returned by ``lump_sum_results``.
    scenario_name : str
        Name to attach to each normalized result row.

    Returns
    -------
    pd.DataFrame
        Normalized extraction table with shared plotting columns.
    """
    return _normalize_extraction_results(
        results,
        scenario_name=scenario_name,
        extraction_mode="Rescate total",
        withdrawal_rate=None,
        after_tax_column="final_after_tax_money",
    )


def normalize_percentage_extraction_results(
    results: pd.DataFrame,
    *,
    scenario_name: str,
) -> pd.DataFrame:
    """
    Normalize percentage-withdrawal results for extraction decomposition plots.

    Parameters
    ----------
    results : pd.DataFrame
        Percentage-withdrawal result table returned by ``percentage_withdrawal_results``.
    scenario_name : str
        Name to attach to each normalized result row.

    Returns
    -------
    pd.DataFrame
        Normalized extraction table with shared plotting columns.
    """
    withdrawal_rate = results["withdrawal_rate"].iloc[0] if not results.empty else 0.0
    return _normalize_extraction_results(
        results,
        scenario_name=scenario_name,
        extraction_mode=f"Rescate {withdrawal_rate:.0%}",
        withdrawal_rate=withdrawal_rate,
        after_tax_column="net_received",
        effective_tax_rate_column="effective_tax_rate",
    )


def _normalize_extraction_results(
    results: pd.DataFrame,
    *,
    scenario_name: str,
    extraction_mode: str,
    withdrawal_rate: float | None,
    after_tax_column: str,
    effective_tax_rate_column: str | None = None,
) -> pd.DataFrame:
    """
    Normalize extraction result tables into a shared plotting schema.

    Parameters
    ----------
    results : pd.DataFrame
        Source result table with vehicle, contribution, extraction, tax, and fee columns.
    scenario_name : str
        Scenario name to write into every output row.
    extraction_mode : str
        Human-readable extraction mode label.
    withdrawal_rate : float | None
        Withdrawal rate for percentage withdrawals, or None for lump-sum extraction.
    after_tax_column : str
        Source column containing the after-tax money value.
    effective_tax_rate_column : str | None
        Source column containing the effective tax rate. If None, the rate is calculated from tax,
        fees, and gross extraction.

    Returns
    -------
    pd.DataFrame
        Normalized extraction rows ready for decomposition plots.
    """
    return pd.DataFrame(
        [
            {
                "scenario": scenario_name,
                "extraction_mode": extraction_mode,
                "withdrawal_rate": withdrawal_rate,
                "vehicle": row["vehicle"],
                "gross_contributed": row["gross_contributed"],
                "pre_withdrawal_value": row["pre_withdrawal_value"],
                "gross_extraction": row["gross_extraction"],
                "after_tax_money": row[after_tax_column],
                "extraction_tax": row["extraction_tax"],
                "extraction_fees": row["extraction_fees"],
                "effective_tax_rate": row[effective_tax_rate_column]
                if effective_tax_rate_column is not None
                else _effective_extraction_rate(row),
            }
            for row in results.to_dict("records")
        ]
    )


def _effective_extraction_rate(row: dict[str, Any]) -> float:
    """
    Calculate effective extraction tax and fee rate for one result row.

    Parameters
    ----------
    row : dict[str, Any]
        Result row containing ``extraction_tax``, ``extraction_fees``, and ``gross_extraction``.

    Returns
    -------
    float
        Tax plus fee amount divided by gross extraction, or zero for a zero extraction.
    """
    return (
        (row["extraction_tax"] + row["extraction_fees"]) / row["gross_extraction"]
        if row["gross_extraction"]
        else 0.0
    )


def working_retirement_salary_sensitivity_results(
    scenario_configs: dict[str, ScenarioConfig],
    heatmap_parameters: dict[str, dict[str, Any]],
    *,
    steps: int,
    min_model_gross_salary: float = 1.0,
    withdrawal_rate: float | None = None,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """
    Calculate pension advantage by working-years salary and retirement salary.

    Parameters
    ----------
    scenario_configs : dict[str, ScenarioConfig]
        Scenario configurations keyed by scenario name.
    heatmap_parameters : dict[str, dict[str, Any]]
        Heatmap bounds, ticks, and display metadata keyed by scenario name.
    steps : int
        Number of grid cells per salary axis.
    min_model_gross_salary : float, optional
        Minimum salary passed into the tax model, by default 1.0.
    withdrawal_rate : float | None, optional
        Percentage withdrawal rate. If None, the comparison uses full liquidation.

    Returns
    -------
    tuple[pd.DataFrame, dict[str, dict[str, Any]]]
        Pension-advantage rows and axis metadata used to render salary heatmaps.
    """
    axes_by_scenario = {}
    rows = []
    tax_entity = HaciendaEspanola()
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
                if not _salary_can_fund_annual_contribution(
                    contribution_salary,
                    config.annual_contribution,
                    tax_entity,
                ):
                    rows.append(
                        {
                            "scenario": scenario_name,
                            "annual_contribution": config.annual_contribution,
                            "withdrawal_rate": withdrawal_rate,
                            "contribution_salary": contribution_salary,
                            "withdrawal_salary": withdrawal_salary,
                            "pension_advantage": math.nan,
                        }
                    )
                    continue

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
                rows.append(
                    {
                        "scenario": scenario_name,
                        "annual_contribution": config.annual_contribution,
                        "withdrawal_rate": withdrawal_rate,
                        "contribution_salary": contribution_salary,
                        "withdrawal_salary": withdrawal_salary,
                        "pension_advantage": pension_advantage_value(result, value_column),
                    }
                )

    return pd.DataFrame(rows), axes_by_scenario


def _salary_can_fund_annual_contribution(
    gross_annual_salary: float,
    annual_contribution: float,
    tax_entity: HaciendaEspanola,
) -> bool:
    """
    Return whether a salary can fund the modeled annual contribution before IRPF.

    Parameters
    ----------
    gross_annual_salary : float
        Gross salary during the contribution period.
    annual_contribution : float
        Gross annual contribution modeled for each vehicle.
    tax_entity : HaciendaEspanola
        Tax entity providing the worker social-security contribution rate.

    Returns
    -------
    bool
        True when the salary after worker social-security contribution is at least the
        contribution amount after worker social-security contribution.
    """
    salary_before_irpf = gross_annual_salary * (1 - tax_entity.contingencias_comunes_trabajador)
    contribution_before_irpf = annual_contribution * (
        1 - tax_entity.contingencias_comunes_trabajador
    )

    return salary_before_irpf >= contribution_before_irpf


def pension_advantage_value(results: pd.DataFrame, value_column: str) -> float:
    """
    Return the plan-minus-fund value from a two-vehicle result table.

    Parameters
    ----------
    results : pd.DataFrame
        Result table containing one row per vehicle.
    value_column : str
        Column used to compare the pension plan against the regular fund.

    Returns
    -------
    float
        Pension plan value minus regular fund value.
    """
    wide = results.pivot_table(columns="vehicle", values=value_column, aggfunc="first")
    return wide[PENSION_PLAN_LABEL].iloc[0] - wide[REGULAR_INDEX_FUND_LABEL].iloc[0]


def final_after_tax_for_config(config: ScenarioConfig) -> pd.DataFrame:
    """
    Return only the final after-tax money column for a scenario.

    Parameters
    ----------
    config : ScenarioConfig
        Scenario inputs used for full liquidation.

    Returns
    -------
    pd.DataFrame
        Two-column result table with vehicle label and final after-tax money.
    """
    return lump_sum_results(config).loc[:, ["vehicle", "final_after_tax_money"]]


def percentage_fee_return_sensitivity_results(
    base_config: ScenarioConfig,
    expected_returns: list[float],
    pension_fee_premiums: list[float],
    withdrawal_rate: float,
) -> pd.DataFrame:
    """
    Calculate percentage-withdrawal pension advantage by return and fee premium.

    Parameters
    ----------
    base_config : ScenarioConfig
        Base scenario inputs. Expected return and pension fee are varied from this configuration.
    expected_returns : list[float]
        Expected annual return values to evaluate.
    pension_fee_premiums : list[float]
        Pension-plan annual fee premiums over the regular fund annual fee.
    withdrawal_rate : float
        Gross percentage of pre-withdrawal portfolio value to withdraw.

    Returns
    -------
    pd.DataFrame
        Pension-advantage rows for each return and fee-premium combination.
    """
    rows = []
    for expected_return in expected_returns:
        for fee_premium in pension_fee_premiums:
            config = replace(
                base_config,
                expected_annual_return=expected_return,
                pension_plan_annual_fee=base_config.regular_fund_annual_fee + fee_premium,
            )
            result = percentage_withdrawal_results(config, withdrawal_rate)
            rows.append(
                {
                    "withdrawal_rate": withdrawal_rate,
                    "expected_return": expected_return,
                    "pension_fee_premium": fee_premium,
                    "pension_advantage": pension_advantage_value(result, "net_received"),
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
    """
    Calculate percentage-withdrawal pension advantage over a dense fee-return grid.

    Parameters
    ----------
    base_config : ScenarioConfig
        Base scenario inputs. Expected return and pension fee are varied from this configuration.
    expected_return_min : float
        Lower bound for expected annual return.
    expected_return_max : float
        Upper bound for expected annual return.
    pension_fee_premium_min : float
        Lower bound for pension-plan fee premium.
    pension_fee_premium_max : float
        Upper bound for pension-plan fee premium.
    steps : int
        Number of grid cells per axis.
    withdrawal_rate : float
        Gross percentage of pre-withdrawal portfolio value to withdraw.

    Returns
    -------
    tuple[pd.DataFrame, dict[str, list[float]]]
        Pension-advantage grid rows and pcolormesh edge coordinates.
    """
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
    """
    Return centered values for a linear grid.

    Parameters
    ----------
    min_value : float
        Lower edge of the full grid range.
    max_value : float
        Upper edge of the full grid range.
    points : int
        Number of centered values to return.

    Returns
    -------
    list[float]
        Center value for each equal-width grid cell.
    """
    step = (max_value - min_value) / points
    return [min_value + step * (index + 0.5) for index in range(points)]


def linear_cell_edges(min_value: float, max_value: float, points: int) -> list[float]:
    """
    Return cell edges for a linear grid.

    Parameters
    ----------
    min_value : float
        Lower edge of the full grid range.
    max_value : float
        Upper edge of the full grid range.
    points : int
        Number of grid cells.

    Returns
    -------
    list[float]
        Edge coordinates for each grid cell, including both outer bounds.
    """
    step = (max_value - min_value) / points
    return [min_value + step * index for index in range(points + 1)]
