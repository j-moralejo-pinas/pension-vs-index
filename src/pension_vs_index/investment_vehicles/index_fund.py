"""Index fund investment vehicle."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from pension_vs_index.investment_vehicles.base_investment_vehicle import (
    BaseInvestmentVehicle,
    Contribution,
)

if TYPE_CHECKING:
    from pension_vs_index.taxing_entity.base_tax_entity import BaseTaxingEntity


class IndexFund(BaseInvestmentVehicle):
    """
    Index fund investment vehicle.

    Attributes
    ----------
    annual_avg_return : float
        The average annual return of the index fund.
    annual_return_std : float
        The standard deviation of the annual return of the index fund.
    annual_fee : float
        The annual recurring fee charged by the index fund.
    annual_flat_fee : float
        The flat annual fee charged by the index fund.
    entry_fee : float
        The fee charged over each contribution before investing it.
    min_entry_fee : float
        The minimum absolute entry fee charged over each contribution.
    exit_fee : float
        The fee charged over each extraction.
    min_exit_fee : float
        The minimum absolute exit fee charged over each extraction.
    tags : list[str]
        Tax tags associated with the index fund.

    Parameters
    ----------
    annual_avg_return : float
        The average annual return of the index fund. Default is 0.07 (7%).
    annual_return_std : float
        The standard deviation of the annual return of the index fund. Default is 0.0 (0%).
    annual_fee : float
        The annual recurring fee charged by the index fund. Default is 0.0 (0%).
    annual_flat_fee : float
        The flat annual fee charged by the index fund. Default is 0.0.
    entry_fee : float
        The fee charged over each contribution before investing it. Default is 0.0 (0%).
    min_entry_fee : float
        The minimum absolute entry fee charged over each contribution. Default is 0.0.
    exit_fee : float
        The fee charged over each extraction. Default is 0.0 (0%).
    min_exit_fee : float
        The minimum absolute exit fee charged over each extraction. Default is 0.0.
    tags : list[str] | None
        Tax tags associated with the index fund. Default is None.
    """

    annual_avg_return: float
    annual_return_std: float
    annual_fee: float
    annual_flat_fee: float
    entry_fee: float
    min_entry_fee: float
    exit_fee: float
    min_exit_fee: float
    tags: list[str]

    def __init__(
        self,
        annual_avg_return: float = 0.07,
        annual_return_std: float = 0.0,
        *,
        annual_fee: float = 0.0,
        annual_flat_fee: float = 0.0,
        entry_fee: float = 0.0,
        min_entry_fee: float = 0.0,
        exit_fee: float = 0.0,
        min_exit_fee: float = 0.0,
        tags: list[str] | None = None,
    ) -> None:
        self.annual_avg_return = annual_avg_return
        self.annual_return_std = annual_return_std
        self.annual_fee = annual_fee
        self.annual_flat_fee = annual_flat_fee
        self.entry_fee = entry_fee
        self.min_entry_fee = min_entry_fee
        self.exit_fee = exit_fee
        self.min_exit_fee = min_exit_fee
        self.tags = [] if tags is None else tags.copy()
        self.contributions = []
        self.current_value = 1.0

    def add_contribution(
        self,
        amount: float,
        taxing_entity: BaseTaxingEntity,
        gross_salary_during_contribution: float,
    ) -> tuple[float, float, float]:
        """
        Add a contribution to the index fund after taxes and entry fees.

        Parameters
        ----------
        amount : float
            The amount of money to add to the index fund before tax.
        taxing_entity : BaseTaxingEntity
            The taxing entity associated with the contribution.
        gross_salary_during_contribution : float
            The gross salary during the contribution period.

        Returns
        -------
        float
            The amount invested after applying taxes and entry fees.
        float
            The amount of tax applied to the contribution.
        float
            The amount of fees applied to the contribution.
        """
        after_tax_contribution, tax_amount = taxing_entity.calculate_contribution_tax(
            amount=amount,
            gross_annual_salary=gross_salary_during_contribution,
            tags=self.tags.copy(),
        )
        invested_amount = self._amount_after_percentage_fee(
            amount=after_tax_contribution,
            fee_rate=self.entry_fee,
            min_fee=self.min_entry_fee,
        )
        fee_amount = after_tax_contribution - invested_amount
        contribution = Contribution(
            buying_price=self.current_value,
            amount=invested_amount,
        )
        self.contributions.append(contribution)
        return contribution.amount_left(self.current_value), tax_amount, fee_amount

    def pass_year(self) -> None:
        """
        Pass a year in the index fund.

        The fund share price is multiplied by one plus the annual return, net of the percentage
        annual fee. The annual return is sampled from a normal distribution centered at
        ``annual_avg_return`` with standard deviation ``annual_return_std``. When the standard
        deviation is zero, the result is deterministic. After that growth, the flat annual fee is
        deducted from the fund holdings.

        Raises
        ------
        ValueError
            If the net annual return would make the fund value negative.
        """
        annual_return = random.gauss(self.annual_avg_return, self.annual_return_std)
        net_annual_return = annual_return - self.annual_fee
        if net_annual_return < -1:
            err_msg = (
                f"Annual return {annual_return} with fee {self.annual_fee} would make the index "
                "fund value negative."
            )
            raise ValueError(err_msg)

        self.current_value *= 1 + net_annual_return
        self._extract_flat_annual_fee()

    def extract_contribution(
        self,
        gross_salary_during_extraction: float,
        taxing_entity: BaseTaxingEntity,
        after_tax_amount: float | None = None,
    ) -> tuple[float, float, float]:
        """
        Extract from the index fund after taxes and exit fees.

        Parameters
        ----------
        gross_salary_during_extraction : float
            The gross salary during the extraction period.
        taxing_entity : BaseTaxingEntity
            The taxing entity associated with the extraction.
        after_tax_amount : float | None
            The amount of money to extract after taxes and exit fees.

        Returns
        -------
        float
            The gross amount extracted before applying taxes and exit fees.
        float
            The amount of taxes applied to the extraction.
        float
            The amount of fees applied to the extraction.

        Raises
        ------
        ValueError
            If the requested net amount is greater than the total fund value.
        """
        if after_tax_amount is None:
            after_tax_amount = self.total
        if after_tax_amount > self.total:
            err_msg = (
                f"Cannot extract {after_tax_amount} from the investment vehicle, "
                f"which only has {self.total}."
            )
            raise ValueError(err_msg)

        gross_extraction, tax_amount, fee_amount = taxing_entity.calculate_extraction_tax(
            after_tax_amount=after_tax_amount,
            gross_annual_salary=gross_salary_during_extraction,
            contributions=self.contributions,
            current_price=self.current_value,
            tags=self.tags.copy(),
            extraction_fee=self.exit_fee,
            min_extraction_fee=self.min_exit_fee,
        )
        self._extract_from_contributions(gross_extraction)

        return gross_extraction, tax_amount, fee_amount

    def extract_gross_contribution(
        self,
        gross_salary_during_extraction: float,
        taxing_entity: BaseTaxingEntity,
        gross_amount: float,
    ) -> tuple[float, float, float]:
        """
        Extract a gross amount from the index fund.

        Parameters
        ----------
        gross_salary_during_extraction : float
            The gross salary during the extraction period.
        taxing_entity : BaseTaxingEntity
            The taxing entity associated with the extraction.
        gross_amount : float
            The amount of money to extract before taxes and fees.

        Returns
        -------
        float
            The amount of money extracted after applying taxes and exit fees.
        float
            The amount of taxes applied to the extraction.
        float
            The amount of fees applied to the extraction.

        Raises
        ------
        ValueError
            If the requested gross amount is greater than the total fund value.
        """
        if gross_amount > self.total:
            err_msg = (
                f"Cannot extract {gross_amount} from the investment vehicle, "
                f"which only has {self.total}."
            )
            raise ValueError(err_msg)

        fee_amount = self._percentage_fee(
            amount=gross_amount,
            fee_rate=self.exit_fee,
            min_fee=self.min_exit_fee,
        )
        tax_amount = taxing_entity.calculate_gross_extraction_tax(
            gross_amount=gross_amount,
            gross_annual_salary=gross_salary_during_extraction,
            contributions=self.contributions,
            current_price=self.current_value,
            tags=self.tags.copy(),
            fee_amount=fee_amount,
        )
        net_amount = gross_amount - tax_amount - fee_amount
        self._extract_from_contributions(gross_amount)

        return net_amount, tax_amount, fee_amount

    def _extract_flat_annual_fee(self) -> None:
        """Extract the flat annual fee from existing holdings."""
        if self.annual_flat_fee <= 0:
            return

        amount_to_extract = min(self.annual_flat_fee, self.total)
        super()._extract_from_contributions(amount_to_extract)

    def _amount_after_percentage_fee(
        self,
        amount: float,
        fee_rate: float,
        min_fee: float,
    ) -> float:
        """
        Calculate the remaining amount after a percentage fee.

        Parameters
        ----------
        amount : float
            The amount over which the fee is charged.
        fee_rate : float
            The fee rate to charge.
        min_fee : float
            The minimum absolute fee to charge.

        Returns
        -------
        float
            The amount remaining after the fee.
        """
        return amount - self._percentage_fee(amount=amount, fee_rate=fee_rate, min_fee=min_fee)

    def _percentage_fee(self, amount: float, fee_rate: float, min_fee: float) -> float:
        """
        Calculate a percentage fee with a minimum absolute amount.

        Parameters
        ----------
        amount : float
            The amount over which the fee is charged.
        fee_rate : float
            The fee rate to charge.
        min_fee : float
            The minimum absolute fee to charge.

        Returns
        -------
        float
            The fee amount, capped at the amount being charged.
        """
        if amount <= 0:
            return 0.0

        return min(amount, max(amount * fee_rate, min_fee))
