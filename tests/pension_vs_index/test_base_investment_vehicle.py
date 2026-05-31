"""Tests for base investment vehicle mechanics."""

from __future__ import annotations

import pytest

from pension_vs_index.investment_vehicles.base_investment_vehicle import (
    BaseInvestmentVehicle,
    Contribution,
)
from pension_vs_index.taxing_entity.base_tax_entity import BaseTaxingEntity


class FixedTaxingEntity(BaseTaxingEntity):
    """Taxing entity with fixed contribution and extraction rates for tests."""

    def __init__(
        self,
        contribution_tax_rate: float = 0.0,
        extraction_tax_rate: float = 0.0,
    ) -> None:
        self.contribution_tax_rate = contribution_tax_rate
        self.extraction_tax_rate = extraction_tax_rate
        self.contribution_calls: list[tuple[float, float]] = []
        self.extraction_calls: list[tuple[float, float, float, float]] = []

    def calculate_contribution_tax(
        self,
        amount: float,
        gross_annual_salary: float,
    ) -> tuple[float, float]:
        """Calculate fixed-rate contribution tax."""
        self.contribution_calls.append((amount, gross_annual_salary))
        tax = amount * self.contribution_tax_rate
        return amount - tax, tax

    def calculate_extraction_tax(
        self,
        after_tax_amount: float,
        gross_annual_salary: float,
        contributions: list[Contribution],
        current_price: float,
    ) -> tuple[float, float]:
        """Calculate fixed-rate extraction tax."""
        self.extraction_calls.append(
            (after_tax_amount, gross_annual_salary, len(contributions), current_price)
        )
        if self.extraction_tax_rate == 0:
            return after_tax_amount, 0.0

        gross_amount = after_tax_amount / (1 - self.extraction_tax_rate)
        return gross_amount, gross_amount - after_tax_amount


class DoublingInvestmentVehicle(BaseInvestmentVehicle):
    """Concrete investment vehicle that doubles in value every year."""

    def __init__(self) -> None:
        self.contributions: list[Contribution] = []
        self.current_value = 1.0

    def pass_year(self) -> None:
        """Double the current share value."""
        self.current_value *= 2


def test_contribution_tracks_amount_left_at_current_price() -> None:
    """A contribution stores shares and values them at the current price."""
    contribution = Contribution(buying_price=10, amount=100)

    assert contribution.shares == 10
    assert contribution.amount_left(current_price=12) == 120


def test_contribution_extract_ignores_non_positive_amount() -> None:
    """Extracting a non-positive amount leaves the contribution unchanged."""
    contribution = Contribution(buying_price=10, amount=100)

    extracted = contribution.extract(amount=0, current_price=20)

    assert extracted == 0
    assert contribution.shares == 10


def test_contribution_extracts_partial_amount() -> None:
    """Partial extraction removes only the needed shares."""
    contribution = Contribution(buying_price=10, amount=100)

    extracted = contribution.extract(amount=40, current_price=20)

    assert extracted == 40
    assert contribution.shares == 8
    assert contribution.amount_left(current_price=20) == 160


def test_contribution_extracts_remaining_amount_when_request_exceeds_value() -> None:
    """Over-extraction drains the contribution and returns the available value."""
    contribution = Contribution(buying_price=10, amount=100)

    extracted = contribution.extract(amount=250, current_price=20)

    assert extracted == 200
    assert contribution.shares == 0


def test_base_investment_vehicle_is_abstract() -> None:
    """The base investment vehicle cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseInvestmentVehicle()  # type: ignore[abstract]


def test_vehicle_total_sums_all_contributions_at_current_price() -> None:
    """Total is the value of every contribution at the current share price."""
    vehicle = DoublingInvestmentVehicle()
    vehicle.contributions = [
        Contribution(buying_price=1, amount=100),
        Contribution(buying_price=2, amount=100),
    ]
    vehicle.current_value = 4

    assert vehicle.total == 600


def test_add_contribution_applies_tax_and_records_buying_price() -> None:
    """Adding a contribution stores the after-tax amount at the current share price."""
    vehicle = DoublingInvestmentVehicle()
    vehicle.current_value = 5
    taxing_entity = FixedTaxingEntity(contribution_tax_rate=0.25)

    after_tax_amount, tax_amount = vehicle.add_contribution(
        amount=100,
        taxing_entity=taxing_entity,
        gross_salary_during_contribution=50_000,
    )

    assert after_tax_amount == 75
    assert tax_amount == 25
    assert taxing_entity.contribution_calls == [(100, 50_000)]
    assert vehicle.contributions[0].buying_price == 5
    assert vehicle.contributions[0].shares == 15


def test_extract_contribution_defaults_to_total_amount() -> None:
    """Extraction uses the full total when no after-tax amount is provided."""
    vehicle = DoublingInvestmentVehicle()
    vehicle.contributions = [Contribution(buying_price=1, amount=100)]
    vehicle.current_value = 2
    taxing_entity = FixedTaxingEntity()

    gross_extraction, tax_amount = vehicle.extract_contribution(
        gross_salary_during_extraction=40_000,
        taxing_entity=taxing_entity,
    )

    assert gross_extraction == 200
    assert tax_amount == 0
    assert taxing_entity.extraction_calls == [(200, 40_000, 1, 2)]
    assert vehicle.contributions == []


def test_extract_contribution_rejects_after_tax_amount_above_total() -> None:
    """An extraction cannot request more after-tax money than the vehicle total."""
    vehicle = DoublingInvestmentVehicle()
    vehicle.contributions = [Contribution(buying_price=1, amount=100)]

    with pytest.raises(ValueError, match="Cannot extract 101"):
        vehicle.extract_contribution(
            gross_salary_during_extraction=40_000,
            taxing_entity=FixedTaxingEntity(),
            after_tax_amount=101,
        )


def test_extract_from_contributions_uses_fifo_order() -> None:
    """Gross extraction removes older contributions before newer ones."""
    vehicle = DoublingInvestmentVehicle()
    vehicle.current_value = 2
    vehicle.contributions = [
        Contribution(buying_price=1, amount=100),
        Contribution(buying_price=2, amount=100),
    ]

    vehicle._extract_from_contributions(amount=250)

    assert len(vehicle.contributions) == 1
    assert vehicle.contributions[0].buying_price == 2
    assert vehicle.contributions[0].amount_left(current_price=2) == 50


def test_extract_from_contributions_rejects_amount_above_available_value() -> None:
    """Gross extraction fails when contributions cannot satisfy the request."""
    vehicle = DoublingInvestmentVehicle()
    vehicle.contributions = [Contribution(buying_price=1, amount=100)]

    with pytest.raises(ValueError, match="available contributions"):
        vehicle._extract_from_contributions(amount=101)


def test_grow_lump_sum_contribution_adds_once_then_passes_years() -> None:
    """Lump-sum growth contributes once and then advances the requested years."""
    vehicle = DoublingInvestmentVehicle()

    total = vehicle.grow_lump_sum_contribution(
        amount=100,
        years=3,
        gross_salary_during_contribution=50_000,
        taxing_entity=FixedTaxingEntity(),
    )

    assert total == 800


def test_grow_annual_contribution_adds_before_each_year_passes() -> None:
    """Annual growth contributes once per year before annual growth is applied."""
    vehicle = DoublingInvestmentVehicle()

    total = vehicle.grow_annual_contribution(
        amount=100,
        years=2,
        gross_salary_during_contribution=50_000,
        taxing_entity=FixedTaxingEntity(),
    )

    assert total == 600
