"""Tests for index fund investment vehicles."""

import pytest

from pension_vs_index.investment_vehicles.base_investment_vehicle import Contribution
from pension_vs_index.investment_vehicles.index_fund import IndexFund
from pension_vs_index.taxing_entity.base_tax_entity import BaseTaxingEntity


class RecordingTaxingEntity(BaseTaxingEntity):
    """Taxing entity that records the tax tags it receives."""

    def __init__(self) -> None:
        self.contribution_tags: list[str] | None = None
        self.extraction_tags: list[str] | None = None
        self.extraction_fee: float | None = None
        self.min_extraction_fee: float | None = None
        self.gross_extraction_fee_amount: float | None = None

    def calculate_contribution_tax(
        self,
        amount: float,
        gross_annual_salary: float,
        *,
        tags: list[str],
    ) -> tuple[float, float]:
        """Record the contribution tax tags."""
        del gross_annual_salary
        self.contribution_tags = tags.copy()
        return amount, 0.0

    def calculate_extraction_tax(
        self,
        after_tax_amount: float,
        gross_annual_salary: float,
        contributions: list[Contribution],
        current_price: float,
        *,
        tags: list[str],
        extraction_fee: float = 0.0,
        min_extraction_fee: float = 0.0,
    ) -> tuple[float, float, float]:
        """Record the extraction tax tags."""
        del gross_annual_salary, contributions, current_price
        self.extraction_tags = tags.copy()
        self.extraction_fee = extraction_fee
        self.min_extraction_fee = min_extraction_fee

        if after_tax_amount <= 0:
            return 0.0, 0.0, 0.0
        if min_extraction_fee <= 0:
            gross_amount = after_tax_amount / (1 - extraction_fee)
            return gross_amount, 0.0, gross_amount * extraction_fee
        if extraction_fee <= 0:
            return after_tax_amount + min_extraction_fee, 0.0, min_extraction_fee

        percentage_fee_threshold = min_extraction_fee / extraction_fee
        gross_with_min_fee = after_tax_amount + min_extraction_fee
        if gross_with_min_fee <= percentage_fee_threshold:
            return gross_with_min_fee, 0.0, min_extraction_fee

        gross_amount = after_tax_amount / (1 - extraction_fee)
        return gross_amount, 0.0, gross_amount * extraction_fee

    def calculate_gross_extraction_tax(
        self,
        gross_amount: float,
        gross_annual_salary: float,
        contributions: list[Contribution],
        current_price: float,
        *,
        tags: list[str],
        fee_amount: float = 0.0,
    ) -> float:
        """Record the extraction tax tags for a gross extraction."""
        del gross_amount, gross_annual_salary, contributions, current_price
        self.extraction_tags = tags.copy()
        self.gross_extraction_fee_amount = fee_amount
        return 0.0


def test_index_fund_pass_year_applies_deterministic_return() -> None:
    """Annual growth updates the fund share price."""
    fund = IndexFund(annual_avg_return=0.07, annual_return_std=0.0)

    fund.pass_year()
    fund.pass_year()

    assert fund.current_value == pytest.approx(1.07**2)


def test_index_fund_pass_year_subtracts_annual_fee() -> None:
    """Annual growth subtracts the recurring fund fee from the return."""
    fund = IndexFund(annual_avg_return=0.07, annual_return_std=0.0, annual_fee=0.002)

    fund.pass_year()

    assert fund.current_value == pytest.approx(1.068)


def test_index_fund_pass_year_extracts_flat_annual_fee() -> None:
    """Annual growth removes the flat annual fee from fund holdings."""
    fund = IndexFund(annual_avg_return=0.0, annual_return_std=0.0, annual_flat_fee=10)
    fund.contributions = [Contribution(buying_price=1, amount=100)]

    fund.pass_year()

    assert fund.total == pytest.approx(90)


def test_index_fund_flat_annual_fee_is_capped_at_total() -> None:
    """A flat annual fee cannot make holdings negative."""
    fund = IndexFund(annual_avg_return=0.0, annual_return_std=0.0, annual_flat_fee=200)
    fund.contributions = [Contribution(buying_price=1, amount=100)]

    fund.pass_year()

    assert fund.total == 0


def test_index_fund_rejects_returns_below_minus_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """A sampled return cannot make the fund share price negative."""
    fund = IndexFund(annual_avg_return=0.07, annual_return_std=0.1)

    monkeypatch.setattr(
        "pension_vs_index.investment_vehicles.index_fund.random.gauss",
        lambda _avg, _std: -1.1,
    )

    with pytest.raises(ValueError, match="negative"):
        fund.pass_year()


def test_index_fund_rejects_returns_that_are_negative_after_annual_fee() -> None:
    """The annual percentage fee is included in the negative-value guard."""
    fund = IndexFund(annual_avg_return=0.0, annual_return_std=0.0, annual_fee=1.1)

    with pytest.raises(ValueError, match="negative"):
        fund.pass_year()


def test_index_fund_uses_default_return_settings() -> None:
    """Index funds have default return settings."""
    fund = IndexFund()

    fund.pass_year()

    assert fund.annual_avg_return == 0.07
    assert fund.annual_return_std == 0.0
    assert fund.annual_fee == 0.0
    assert fund.annual_flat_fee == 0.0
    assert fund.entry_fee == 0.0
    assert fund.min_entry_fee == 0.0
    assert fund.exit_fee == 0.0
    assert fund.min_exit_fee == 0.0
    assert fund.tags == []
    assert fund.current_value == pytest.approx(1.07)


def test_index_fund_entry_fee_reduces_invested_contribution() -> None:
    """Entry fees reduce the contribution invested in the index fund."""
    fund = IndexFund(entry_fee=0.02)

    invested_amount, tax_amount, fee_amount = fund.add_contribution(
        amount=100,
        taxing_entity=RecordingTaxingEntity(),
        gross_salary_during_contribution=40_000,
    )

    assert invested_amount == pytest.approx(98)
    assert tax_amount == 0
    assert fee_amount == pytest.approx(2)
    assert fund.total == pytest.approx(98)


def test_index_fund_entry_fee_uses_minimum_absolute_fee() -> None:
    """Entry fees use the minimum absolute fee when it is higher than the percentage fee."""
    fund = IndexFund(entry_fee=0.01, min_entry_fee=10)

    invested_amount, _tax_amount, fee_amount = fund.add_contribution(
        amount=100,
        taxing_entity=RecordingTaxingEntity(),
        gross_salary_during_contribution=40_000,
    )

    assert invested_amount == pytest.approx(90)
    assert fee_amount == pytest.approx(10)
    assert fund.total == pytest.approx(90)


def test_index_fund_entry_fee_is_capped_at_contribution_amount() -> None:
    """The minimum entry fee cannot make an invested contribution negative."""
    fund = IndexFund(min_entry_fee=10)

    invested_amount, _tax_amount, fee_amount = fund.add_contribution(
        amount=5,
        taxing_entity=RecordingTaxingEntity(),
        gross_salary_during_contribution=40_000,
    )

    assert invested_amount == 0
    assert fee_amount == 5
    assert fund.total == 0


def test_index_fund_entry_fee_is_zero_for_non_positive_contribution() -> None:
    """Entry fees are not charged when the contribution amount is not positive."""
    fund = IndexFund(entry_fee=0.01, min_entry_fee=10)

    invested_amount, _tax_amount, fee_amount = fund.add_contribution(
        amount=0,
        taxing_entity=RecordingTaxingEntity(),
        gross_salary_during_contribution=40_000,
    )

    assert invested_amount == 0
    assert fee_amount == 0
    assert fund.total == 0


def test_index_fund_exit_fee_removes_extra_amount_from_holdings() -> None:
    """Exit fees remove extra value from holdings during extraction."""
    fund = IndexFund(exit_fee=0.10)
    fund.contributions = [Contribution(buying_price=1, amount=100)]

    gross_extraction, tax_amount, fee_amount = fund.extract_contribution(
        gross_salary_during_extraction=40_000,
        taxing_entity=RecordingTaxingEntity(),
        after_tax_amount=50,
    )

    assert gross_extraction == pytest.approx(55.55555555555556)
    assert tax_amount == 0
    assert fee_amount == pytest.approx(5.55555555555556)
    assert fund.total == pytest.approx(44.44444444444444)


def test_index_fund_exit_fee_uses_minimum_absolute_fee() -> None:
    """Exit fees use the minimum absolute fee when it is higher than the percentage fee."""
    fund = IndexFund(exit_fee=0.01, min_exit_fee=10)
    fund.contributions = [Contribution(buying_price=1, amount=100)]

    gross_extraction, tax_amount, fee_amount = fund.extract_contribution(
        gross_salary_during_extraction=40_000,
        taxing_entity=RecordingTaxingEntity(),
        after_tax_amount=50,
    )

    assert gross_extraction == pytest.approx(60)
    assert tax_amount == 0
    assert fee_amount == 10
    assert fund.total == pytest.approx(40)


def test_index_fund_extract_contribution_defaults_to_total() -> None:
    """Index fund extraction uses the full total when no net amount is provided."""
    fund = IndexFund()
    fund.contributions = [Contribution(buying_price=1, amount=100)]

    gross_extraction, tax_amount, fee_amount = fund.extract_contribution(
        gross_salary_during_extraction=40_000,
        taxing_entity=RecordingTaxingEntity(),
    )

    assert gross_extraction == 100
    assert tax_amount == 0
    assert fee_amount == 0
    assert fund.total == 0


def test_index_fund_extract_contribution_rejects_amount_above_total() -> None:
    """Index fund extraction cannot request more net cash than the fund total."""
    fund = IndexFund()
    fund.contributions = [Contribution(buying_price=1, amount=100)]

    with pytest.raises(ValueError, match="Cannot extract 101"):
        fund.extract_contribution(
            gross_salary_during_extraction=40_000,
            taxing_entity=RecordingTaxingEntity(),
            after_tax_amount=101,
        )


def test_index_fund_extract_gross_contribution_returns_net_tax_and_fee() -> None:
    """Gross extraction returns the net amount, tax amount, and fee amount."""
    fund = IndexFund(exit_fee=0.10)
    taxing_entity = RecordingTaxingEntity()
    fund.contributions = [Contribution(buying_price=1, amount=100)]

    net_amount, tax_amount, fee_amount = fund.extract_gross_contribution(
        gross_salary_during_extraction=40_000,
        taxing_entity=taxing_entity,
        gross_amount=50,
    )

    assert net_amount == 45
    assert tax_amount == 0
    assert fee_amount == 5
    assert taxing_entity.gross_extraction_fee_amount == 5
    assert fund.total == 50


def test_index_fund_extract_gross_contribution_precalculates_minimum_exit_fee() -> None:
    """Gross extraction passes the precomputed minimum exit fee to the tax entity."""
    fund = IndexFund(exit_fee=0.01, min_exit_fee=10)
    taxing_entity = RecordingTaxingEntity()
    fund.contributions = [Contribution(buying_price=1, amount=100)]

    net_amount, tax_amount, fee_amount = fund.extract_gross_contribution(
        gross_salary_during_extraction=40_000,
        taxing_entity=taxing_entity,
        gross_amount=50,
    )

    assert net_amount == 40
    assert tax_amount == 0
    assert fee_amount == 10
    assert taxing_entity.gross_extraction_fee_amount == 10
    assert fund.total == 50


def test_index_fund_extract_gross_contribution_rejects_amount_above_total() -> None:
    """Index fund gross extraction cannot request more than the fund total."""
    fund = IndexFund()
    fund.contributions = [Contribution(buying_price=1, amount=100)]

    with pytest.raises(ValueError, match="Cannot extract 101"):
        fund.extract_gross_contribution(
            gross_salary_during_extraction=40_000,
            taxing_entity=RecordingTaxingEntity(),
            gross_amount=101,
        )


def test_index_fund_copies_tags() -> None:
    """Index fund stores its own copy of the supplied tags."""
    tags = ["plan_de_pensiones"]

    fund = IndexFund(tags=tags)
    tags.append("mutated")

    assert fund.tags == ["plan_de_pensiones"]


def test_index_fund_passes_tags_to_contribution_tax() -> None:
    """Index fund contribution tax receives the fund tags."""
    fund = IndexFund(tags=["plan_de_pensiones"])
    taxing_entity = RecordingTaxingEntity()

    fund.add_contribution(
        amount=100,
        taxing_entity=taxing_entity,
        gross_salary_during_contribution=40_000,
    )

    assert taxing_entity.contribution_tags == ["plan_de_pensiones"]


def test_index_fund_passes_tags_to_extraction_tax() -> None:
    """Index fund extraction tax receives the fund tags."""
    fund = IndexFund(tags=["plan_de_pensiones"])
    taxing_entity = RecordingTaxingEntity()
    fund.contributions = [Contribution(buying_price=1, amount=100)]

    fund.extract_contribution(
        gross_salary_during_extraction=40_000,
        taxing_entity=taxing_entity,
        after_tax_amount=50,
    )

    assert taxing_entity.extraction_tags == ["plan_de_pensiones"]
