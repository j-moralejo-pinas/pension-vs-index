"""Tests for Spanish tax calculations."""

from __future__ import annotations

import math

import pytest

from pension_vs_index.investment_vehicles.base_investment_vehicle import Contribution
from pension_vs_index.taxing_entity.hacienda_espanola import HaciendaEspanola


def test_social_security_contribution_totals_are_initialized() -> None:
    """The aggregate social-security rates are calculated from their components."""
    tax_entity = HaciendaEspanola()

    assert tax_entity.contribucion_ss_empresa == pytest.approx(0.3215)
    assert tax_entity.contribucion_ss_trabajador == pytest.approx(0.065)


def test_calculate_irpf_applies_progressive_brackets() -> None:
    """IRPF is charged only on the part of income above each lower bound."""
    tax_entity = HaciendaEspanola()

    tax = tax_entity.calculate_irpf(
        annual_salary_before_tax=25_000,
        irpf_rates=((0, 0.10), (10_000, 0.20), (20_000, 0.30)),
    )

    assert tax == pytest.approx(4_500)


def test_calculate_irpf_returns_zero_below_first_bracket() -> None:
    """No IRPF is charged when income does not exceed the first lower bound."""
    tax_entity = HaciendaEspanola()

    tax = tax_entity.calculate_irpf(
        annual_salary_before_tax=4_000,
        irpf_rates=((5_000, 0.10),),
    )

    assert tax == 0


def test_regular_contribution_tax_matches_salary_after_tax_ratio() -> None:
    """Regular contributions are reduced using the salary after-tax ratio."""
    tax_entity = HaciendaEspanola()

    amount_after_tax, tax_amount = tax_entity.calculate_contribution_tax(
        amount=1_000,
        gross_annual_salary=40_000,
    )

    amount_after_ss = 40_000 * (1 - tax_entity.contingencias_comunes_trabajador)
    expected_irpf = tax_entity.calculate_irpf(
        amount_after_ss, tax_entity.irpf_estatal
    ) + tax_entity.calculate_irpf(amount_after_ss, tax_entity.irpf_autonomico)
    expected_after_tax = 1_000 * (amount_after_ss - expected_irpf) / 40_000

    assert amount_after_tax == pytest.approx(expected_after_tax)
    assert tax_amount == pytest.approx(1_000 - expected_after_tax)


def test_pension_plan_contribution_tax_only_applies_worker_social_security() -> None:
    """Pension-plan contributions use the dedicated contribution-tax path."""
    tax_entity = HaciendaEspanola()

    amount_after_tax, tax_amount = tax_entity.calculate_contribution_tax(
        amount=1_000,
        gross_annual_salary=40_000,
        is_plan_de_pensiones=True,
    )

    assert amount_after_tax == pytest.approx(953)
    assert tax_amount == pytest.approx(47)


def test_regular_extraction_tax_returns_zero_for_non_positive_amount() -> None:
    """Regular extractions of zero or less are no-ops."""
    tax_entity = HaciendaEspanola()

    assert tax_entity.calculate_extraction_tax(
        after_tax_amount=0,
        gross_annual_salary=40_000,
        contributions=[],
        current_price=1,
    ) == (0.0, 0.0)


def test_regular_extraction_tax_has_no_tax_without_capital_gain() -> None:
    """Regular extractions are untaxed when the contribution has no gain."""
    tax_entity = HaciendaEspanola()
    contributions = [Contribution(buying_price=10, amount=100)]

    gross_extraction, tax_amount = tax_entity.calculate_extraction_tax(
        after_tax_amount=80,
        gross_annual_salary=40_000,
        contributions=contributions,
        current_price=10,
    )

    assert gross_extraction == 80
    assert tax_amount == 0


def test_regular_extraction_tax_applies_capital_gains_brackets() -> None:
    """Regular extraction taxation moves to the next capital-gains bracket."""
    tax_entity = HaciendaEspanola()
    contributions = [Contribution(buying_price=50, amount=25_000)]

    gross_extraction, tax_amount = tax_entity.calculate_extraction_tax(
        after_tax_amount=15_000,
        gross_annual_salary=40_000,
        contributions=contributions,
        current_price=100,
    )

    assert gross_extraction == pytest.approx(16_625.698324022346)
    assert tax_amount == pytest.approx(1_625.6983240223464)


def test_regular_extraction_tax_rejects_impossible_net_percentage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regular extraction fails when the tax rate makes net extraction impossible."""
    tax_entity = HaciendaEspanola()
    contributions = [Contribution(buying_price=50, amount=100)]
    monkeypatch.setattr(tax_entity, "_marginal_capital_gains_tax_rate", lambda _gains: 2.0)

    with pytest.raises(ValueError, match="positive net extraction"):
        tax_entity.calculate_extraction_tax(
            after_tax_amount=1,
            gross_annual_salary=40_000,
            contributions=contributions,
            current_price=100,
        )


def test_regular_extraction_tax_rejects_amount_above_available_contributions() -> None:
    """Regular extraction fails when the available contributions cannot cover the request."""
    tax_entity = HaciendaEspanola()
    contributions = [Contribution(buying_price=10, amount=100)]

    with pytest.raises(ValueError, match="available contributions"):
        tax_entity.calculate_extraction_tax(
            after_tax_amount=101,
            gross_annual_salary=40_000,
            contributions=contributions,
            current_price=10,
        )


def test_gain_percentage_is_zero_for_non_positive_current_price() -> None:
    """Gain percentage is zero when there is no positive current price."""
    tax_entity = HaciendaEspanola()

    gain_percentage = tax_entity._calculate_gain_percentage(
        Contribution(buying_price=10, amount=100),
        current_price=0,
    )

    assert gain_percentage == 0


def test_gain_percentage_is_never_negative() -> None:
    """Losses do not create a taxable negative gain percentage."""
    tax_entity = HaciendaEspanola()

    gain_percentage = tax_entity._calculate_gain_percentage(
        Contribution(buying_price=20, amount=100),
        current_price=10,
    )

    assert gain_percentage == 0


def test_marginal_capital_gains_rate_uses_last_matching_bracket() -> None:
    """Capital-gains marginal rates are selected by accumulated gains."""
    tax_entity = HaciendaEspanola()

    assert tax_entity._marginal_capital_gains_tax_rate(250_000) == 0.27


def test_next_capital_gains_bracket_returns_infinity_after_last_bracket() -> None:
    """There is no upper capital-gains bracket after the final threshold."""
    tax_entity = HaciendaEspanola()

    assert tax_entity._next_capital_gains_bracket(400_000) == float("inf")


def test_pension_plan_extraction_tax_returns_zero_for_non_positive_amount() -> None:
    """Pension-plan extractions of zero or less are no-ops."""
    tax_entity = HaciendaEspanola()

    assert tax_entity.calculate_extraction_tax(
        after_tax_amount=0,
        gross_annual_salary=40_000,
        contributions=[],
        current_price=1,
        is_plan_de_pensiones=True,
    ) == (0.0, 0.0)


def test_pension_plan_extraction_tax_applies_irpf_brackets() -> None:
    """Pension-plan extraction taxation moves to the next IRPF bracket."""
    tax_entity = HaciendaEspanola()

    gross_extraction, tax_amount = tax_entity.calculate_extraction_tax(
        after_tax_amount=100,
        gross_annual_salary=12_440,
        contributions=[],
        current_price=1,
        is_plan_de_pensiones=True,
    )

    assert gross_extraction == pytest.approx(125.47169811320755)
    assert tax_amount == pytest.approx(25.471698113207545)


def test_pension_plan_extraction_tax_rejects_impossible_net_percentage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pension-plan extraction fails when the tax rate leaves no net amount."""
    tax_entity = HaciendaEspanola()
    monkeypatch.setattr(tax_entity, "_marginal_irpf_tax_rate", lambda _income: 1.0)

    with pytest.raises(ValueError, match="positive net extraction"):
        tax_entity.calculate_extraction_tax(
            after_tax_amount=1,
            gross_annual_salary=40_000,
            contributions=[],
            current_price=1,
            is_plan_de_pensiones=True,
        )


def test_pension_plan_extraction_tax_returns_accumulated_amounts_after_nan_bracket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fallback return is used if bracket calculation produces NaN."""
    tax_entity = HaciendaEspanola()
    monkeypatch.setattr(tax_entity, "_next_irpf_bracket", lambda _income: float("nan"))

    gross_extraction, tax_amount = tax_entity.calculate_extraction_tax(
        after_tax_amount=1,
        gross_annual_salary=40_000,
        contributions=[],
        current_price=1,
        is_plan_de_pensiones=True,
    )

    assert math.isnan(gross_extraction)
    assert math.isnan(tax_amount)


def test_marginal_irpf_rate_combines_state_and_regional_rates() -> None:
    """The IRPF marginal rate combines estatal and autonomico marginal rates."""
    tax_entity = HaciendaEspanola()

    assert tax_entity._marginal_irpf_tax_rate(40_000) == pytest.approx(0.359)


def test_marginal_tax_rate_is_zero_below_first_bracket() -> None:
    """Generic marginal tax rates are zero below the first lower bound."""
    tax_entity = HaciendaEspanola()

    assert tax_entity._marginal_tax_rate(4_000, ((5_000, 0.10),)) == 0


def test_next_irpf_bracket_returns_infinity_after_last_bracket() -> None:
    """There is no upper IRPF bracket after the final threshold."""
    tax_entity = HaciendaEspanola()

    assert tax_entity._next_irpf_bracket(400_000) == float("inf")
