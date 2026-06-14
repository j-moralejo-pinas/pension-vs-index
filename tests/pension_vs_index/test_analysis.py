"""Tests for reusable analysis routines."""

import math

from pension_vs_index.analysis import (
    ScenarioConfig,
    _salary_can_fund_annual_contribution,
    working_retirement_salary_sensitivity_results,
)
from pension_vs_index.taxing_entity.hacienda_espanola import HaciendaEspanola


def test_salary_sensitivity_skips_salaries_that_cannot_fund_contribution() -> None:
    """Salary heatmaps leave unaffordable contribution cells uncomputed."""
    scenario_name = "Scenario"
    config = ScenarioConfig(
        annual_contribution=50,
        investment_horizon_years=1,
        contribution_years=1,
        expected_annual_return=0.0,
        annual_return_volatility=0.0,
        regular_fund_annual_fee=0.0,
        pension_plan_annual_fee=0.0,
    )

    results, _axes = working_retirement_salary_sensitivity_results(
        {scenario_name: config},
        {
            scenario_name: {
                "contribution_salary_min": 0.0,
                "contribution_salary_max": 100.0,
                "withdrawal_salary_min": 0.0,
                "withdrawal_salary_max": 100.0,
            }
        },
        steps=4,
        min_model_gross_salary=1.0,
        withdrawal_rate=0.04,
    )

    invalid_row = results[
        (results["contribution_salary"] == 12.5) & (results["withdrawal_salary"] == 12.5)
    ].iloc[0]
    valid_row_above_diagonal = results[
        (results["contribution_salary"] == 62.5) & (results["withdrawal_salary"] == 87.5)
    ].iloc[0]

    assert math.isnan(invalid_row["pension_advantage"])
    assert not math.isnan(valid_row_above_diagonal["pension_advantage"])


def test_salary_can_fund_annual_contribution_compares_amounts_before_irpf() -> None:
    """Contribution feasibility is based on salary and contribution after worker SS."""
    tax_entity = HaciendaEspanola()

    assert _salary_can_fund_annual_contribution(10_000, 10_000, tax_entity)
    assert not _salary_can_fund_annual_contribution(9_999, 10_000, tax_entity)
