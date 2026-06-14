"""Tests for Spanish tax calculations."""

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


def test_regular_contribution_tax_uses_marginal_salary_slice() -> None:
    """Regular contributions are reduced using the marginal after-tax salary slice."""
    tax_entity = HaciendaEspanola()

    amount_after_tax, tax_amount = tax_entity.calculate_contribution_tax(
        amount=1_000,
        gross_annual_salary=40_000,
        tags=[],
    )

    expected_after_tax = tax_entity._salary_after_income_tax(  # noqa: SLF001
        40_000
    ) - tax_entity._salary_after_income_tax(39_000)  # noqa: SLF001

    assert amount_after_tax == pytest.approx(expected_after_tax)
    assert tax_amount == pytest.approx(1_000 - expected_after_tax)


def test_pension_plan_contribution_tax_only_applies_worker_social_security() -> None:
    """Pension-plan contributions use the dedicated contribution-tax path."""
    tax_entity = HaciendaEspanola()

    amount_after_tax, tax_amount = tax_entity.calculate_contribution_tax(
        amount=1_000,
        gross_annual_salary=40_000,
        tags=["plan_de_pensiones"],
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
        tags=[],
    ) == (0.0, 0.0, 0.0)


def test_regular_extraction_tax_has_no_tax_without_capital_gain() -> None:
    """Regular extractions are untaxed when the contribution has no gain."""
    tax_entity = HaciendaEspanola()
    contributions = [Contribution(buying_price=10, amount=100)]

    gross_extraction, tax_amount, fee_amount = tax_entity.calculate_extraction_tax(
        after_tax_amount=80,
        gross_annual_salary=40_000,
        contributions=contributions,
        current_price=10,
        tags=[],
    )

    assert gross_extraction == 80
    assert tax_amount == 0
    assert fee_amount == 0


def test_regular_extraction_tax_applies_capital_gains_brackets() -> None:
    """Regular extraction taxation moves to the next capital-gains bracket."""
    tax_entity = HaciendaEspanola()
    contributions = [Contribution(buying_price=50, amount=25_000)]

    gross_extraction, tax_amount, fee_amount = tax_entity.calculate_extraction_tax(
        after_tax_amount=15_000,
        gross_annual_salary=40_000,
        contributions=contributions,
        current_price=100,
        tags=[],
    )

    assert gross_extraction == pytest.approx(16_625.698324022346)
    assert tax_amount == pytest.approx(1_625.6983240223464)
    assert fee_amount == 0


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
            tags=[],
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
            tags=[],
        )


def test_regular_extraction_tax_rejects_empty_contributions() -> None:
    """Regular extraction fails when there are no available contributions."""
    tax_entity = HaciendaEspanola()

    with pytest.raises(ValueError, match="available contributions"):
        tax_entity.calculate_extraction_tax(
            after_tax_amount=1,
            gross_annual_salary=40_000,
            contributions=[],
            current_price=1,
            tags=[],
        )


def test_regular_extraction_tax_discounts_exit_fee_from_capital_gain() -> None:
    """Capital-gains tax uses sale proceeds after exit fees."""
    tax_entity = HaciendaEspanola()
    contributions = [Contribution(buying_price=1, amount=100)]

    gross_extraction, tax_amount, fee_amount = tax_entity.calculate_extraction_tax(
        after_tax_amount=100,
        gross_annual_salary=40_000,
        contributions=contributions,
        current_price=2,
        tags=[],
        extraction_fee=0.10,
    )

    assert gross_extraction == pytest.approx(121.35922330097087)
    assert tax_amount == pytest.approx(9.223300970873787)
    assert fee_amount == pytest.approx(12.135922330097087)


def test_regular_gross_extraction_tax_returns_tax() -> None:
    """Regular gross extraction tax uses sale proceeds after fees."""
    tax_entity = HaciendaEspanola()
    contributions = [
        Contribution(buying_price=1, amount=100),
        Contribution(buying_price=1, amount=100),
    ]

    tax_amount = tax_entity.calculate_gross_extraction_tax(
        gross_amount=50,
        gross_annual_salary=40_000,
        contributions=contributions,
        current_price=2,
        tags=[],
        fee_amount=5,
    )

    assert tax_amount == pytest.approx(3.8)


def test_gross_extraction_tax_returns_zero_for_non_positive_amount() -> None:
    """Gross extraction of zero or less is a no-op."""
    tax_entity = HaciendaEspanola()

    assert (
        tax_entity.calculate_gross_extraction_tax(
            gross_amount=0,
            gross_annual_salary=40_000,
            contributions=[],
            current_price=1,
            tags=[],
        )
        == 0.0
    )


def test_regular_gross_extraction_tax_rejects_amount_above_available_contributions() -> None:
    """Regular gross extraction fails when available contributions cannot cover the request."""
    tax_entity = HaciendaEspanola()

    with pytest.raises(ValueError, match="available contributions"):
        tax_entity.calculate_gross_extraction_tax(
            gross_amount=101,
            gross_annual_salary=40_000,
            contributions=[Contribution(buying_price=1, amount=100)],
            current_price=1,
            tags=[],
            fee_amount=0,
        )


def test_regular_extraction_tax_stops_after_needed_contributions() -> None:
    """Regular extraction stops processing contributions once the gross amount is covered."""
    tax_entity = HaciendaEspanola()
    contributions = [
        Contribution(buying_price=1, amount=100),
        Contribution(buying_price=1, amount=100),
    ]

    gross_extraction, tax_amount, fee_amount = tax_entity.calculate_extraction_tax(
        after_tax_amount=50,
        gross_annual_salary=40_000,
        contributions=contributions,
        current_price=1,
        tags=[],
    )

    assert gross_extraction == pytest.approx(50)
    assert tax_amount == pytest.approx(0)
    assert fee_amount == 0


def test_hacienda_percentage_fee_is_zero_for_non_positive_amount() -> None:
    """Hacienda fee calculation is zero for non-positive amounts."""
    tax_entity = HaciendaEspanola()

    assert tax_entity._percentage_fee(amount=0, fee_rate=0.1, min_fee=10) == 0


def test_hacienda_percentage_fee_applies_minimum_and_cap() -> None:
    """Hacienda fee calculation applies minimums without exceeding the amount."""
    tax_entity = HaciendaEspanola()

    assert tax_entity._percentage_fee(amount=100, fee_rate=0.1, min_fee=20) == 20
    assert tax_entity._percentage_fee(amount=5, fee_rate=0.1, min_fee=20) == 5


def test_regular_tax_for_gross_extraction_returns_zero_for_non_positive_amount() -> None:
    """Regular gross-extraction tax is zero when no positive gross amount is extracted."""
    tax_entity = HaciendaEspanola()

    assert (
        tax_entity._regular_tax_for_gross_extraction(
            gross_extraction=0,
            contributions=[Contribution(buying_price=1, amount=100)],
            current_price=1,
            fee_amount=0,
        )
        == 0
    )


def test_regular_tax_for_gross_extraction_rejects_amount_above_available() -> None:
    """Regular gross-extraction tax fails when gross extraction exceeds holdings."""
    tax_entity = HaciendaEspanola()

    with pytest.raises(ValueError, match="available contributions"):
        tax_entity._regular_tax_for_gross_extraction(
            gross_extraction=101,
            contributions=[Contribution(buying_price=1, amount=100)],
            current_price=1,
            fee_amount=0,
        )


def test_cost_basis_percentage_is_zero_for_non_positive_current_price() -> None:
    """Cost basis percentage is zero when there is no positive current price."""
    tax_entity = HaciendaEspanola()

    cost_basis_percentage = tax_entity._cost_basis_percentage(
        Contribution(buying_price=1, amount=100),
        current_price=0,
    )

    assert cost_basis_percentage == 0


def test_marginal_fee_rate_covers_fee_modes() -> None:
    """Marginal fee rates move through minimum, flat, percentage, and capped modes."""
    tax_entity = HaciendaEspanola()

    assert tax_entity._marginal_fee_rate(5, 0.1, 10) == 1.0
    assert tax_entity._marginal_fee_rate(20, 0.0, 10) == 0.0
    assert tax_entity._marginal_fee_rate(20, 1.1, 10) == 1.0
    assert tax_entity._marginal_fee_rate(20, 0.1, 10) == 0.0
    assert tax_entity._marginal_fee_rate(120, 0.1, 10) == 0.1


def test_gross_until_next_fee_boundary_covers_fee_modes() -> None:
    """Fee boundaries account for minimum-fee and percentage-fee thresholds."""
    tax_entity = HaciendaEspanola()

    assert tax_entity._gross_until_next_fee_boundary(0, 0.1, 0) == float("inf")
    assert tax_entity._gross_until_next_fee_boundary(5, 0.1, 10) == 5
    assert tax_entity._gross_until_next_fee_boundary(20, 0.0, 10) == float("inf")
    assert tax_entity._gross_until_next_fee_boundary(20, 1.1, 10) == float("inf")
    assert tax_entity._gross_until_next_fee_boundary(20, 0.1, 10) == 80
    assert tax_entity._gross_until_next_fee_boundary(120, 0.1, 10) == float("inf")


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
        tags=["plan_de_pensiones"],
    ) == (0.0, 0.0, 0.0)


def test_pension_plan_extraction_tax_applies_irpf_brackets() -> None:
    """Pension-plan extraction taxation moves to the next IRPF bracket."""
    tax_entity = HaciendaEspanola()

    gross_extraction, tax_amount, fee_amount = tax_entity.calculate_extraction_tax(
        after_tax_amount=100,
        gross_annual_salary=12_440,
        contributions=[Contribution(buying_price=1, amount=1_000)],
        current_price=1,
        tags=["plan_de_pensiones"],
    )

    assert gross_extraction == pytest.approx(125.47169811320755)
    assert tax_amount == pytest.approx(25.471698113207545)
    assert fee_amount == 0


def test_pension_plan_extraction_tax_taxes_exit_fee() -> None:
    """IRPF taxes the full gross extraction, including the exit-fee part."""
    tax_entity = HaciendaEspanola()

    gross_extraction, tax_amount, fee_amount = tax_entity.calculate_extraction_tax(
        after_tax_amount=100,
        gross_annual_salary=40_000,
        contributions=[Contribution(buying_price=1, amount=1_000)],
        current_price=1,
        tags=["plan_de_pensiones"],
        extraction_fee=0.10,
    )

    assert gross_extraction == pytest.approx(184.84288354898337)
    assert tax_amount == pytest.approx(66.35859519408501)
    assert fee_amount == pytest.approx(18.484288354898338)


def test_pension_plan_gross_extraction_tax_ignores_fee_for_irpf_base() -> None:
    """Gross pension-plan extraction tax uses the full gross amount."""
    tax_entity = HaciendaEspanola()

    tax_amount = tax_entity.calculate_gross_extraction_tax(
        gross_amount=100,
        gross_annual_salary=40_000,
        contributions=[Contribution(buying_price=1, amount=1_000)],
        current_price=1,
        tags=["plan_de_pensiones"],
        fee_amount=10,
    )

    assert tax_amount == pytest.approx(35.9)


def test_pension_plan_gross_extraction_tax_rejects_impossible_tax_rate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gross pension-plan extraction fails when the tax rate leaves no net amount."""
    tax_entity = HaciendaEspanola()
    monkeypatch.setattr(tax_entity, "_marginal_irpf_tax_rate", lambda _income: 1.0)

    with pytest.raises(ValueError, match="positive net extraction"):
        tax_entity.calculate_gross_extraction_tax(
            gross_amount=1,
            gross_annual_salary=40_000,
            contributions=[Contribution(buying_price=1, amount=1_000)],
            current_price=1,
            tags=["plan_de_pensiones"],
        )


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
            contributions=[Contribution(buying_price=1, amount=1_000)],
            current_price=1,
            tags=["plan_de_pensiones"],
        )


def test_pension_plan_extraction_tax_rejects_amount_above_available_contributions() -> None:
    """Pension-plan extraction fails when available contributions cannot cover the request."""
    tax_entity = HaciendaEspanola()

    with pytest.raises(ValueError, match="available contributions"):
        tax_entity.calculate_extraction_tax(
            after_tax_amount=2_000,
            gross_annual_salary=40_000,
            contributions=[Contribution(buying_price=1, amount=1_000)],
            current_price=1,
            tags=["plan_de_pensiones"],
        )


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
