"""Tests for index fund investment vehicles."""

import pytest

from pension_vs_index.investment_vehicles.index_funds.base_index_fund import BaseIndexFund
from pension_vs_index.investment_vehicles.index_funds.msci_world import MSCIWorld
from pension_vs_index.investment_vehicles.index_funds.world_index_pp import WorldIndexPP


def test_base_index_fund_pass_year_applies_deterministic_return() -> None:
    """Annual growth updates the fund share price."""
    fund = BaseIndexFund(annual_avg_return=0.07, annual_return_std=0.0)

    fund.pass_year()
    fund.pass_year()

    assert fund.current_value == pytest.approx(1.07**2)


def test_base_index_fund_rejects_returns_below_minus_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """A sampled return cannot make the fund share price negative."""
    fund = BaseIndexFund(annual_avg_return=0.07, annual_return_std=0.1)

    monkeypatch.setattr(
        "pension_vs_index.investment_vehicles.index_funds.base_index_fund.random.gauss",
        lambda _avg, _std: -1.1,
    )

    with pytest.raises(ValueError, match="negative"):
        fund.pass_year()


def test_msci_world_uses_base_index_fund_defaults() -> None:
    """MSCI World has index-fund defaults and behavior."""
    fund = MSCIWorld()

    fund.pass_year()

    assert fund.annual_avg_return == 0.07
    assert fund.annual_return_std == 0.0
    assert fund.current_value == pytest.approx(1.07)


def test_world_index_pp_uses_base_index_fund_defaults() -> None:
    """World Index PP has index-fund defaults and behavior."""
    fund = WorldIndexPP()

    fund.pass_year()

    assert fund.annual_avg_return == 0.07
    assert fund.annual_return_std == 0.0
    assert fund.current_value == pytest.approx(1.07)
