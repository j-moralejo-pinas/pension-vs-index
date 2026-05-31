"""Base class for investment vehicles."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pension_vs_index.taxing_entity.base_tax_entity import BaseTaxingEntity


class Contribution:
    """
    Class representing a contribution to an investment vehicle.

    Attributes
    ----------
    buying_price : float
        The price at which the contribution was made.
    shares : float
        The number of shares bought with the contribution.

    Parameters
    ----------
    buying_price : float
        The price at which the contribution is made.
    amount : float
        The amount of money in the contribution.
    """

    buying_price: float
    shares: float

    def __init__(self, buying_price: float, amount: float) -> None:
        self.buying_price = buying_price
        self.shares = amount / buying_price

    def amount_left(self, current_price: float) -> float:
        """
        Calculate the amount of money left in the contribution.

        Parameters
        ----------
        current_price : float
            The current price of the investment vehicle.

        Returns
        -------
        float
            The amount of money left in the contribution.
        """
        return self.shares * current_price

    def extract(self, amount: float, current_price: float) -> float:
        """
        Extract a specified amount from the contribution.

        Parameters
        ----------
        amount : float
            The amount of money to extract.
        current_price : float
            The current price of the investment vehicle.

        Returns
        -------
        float
            The amount of money extracted from the contribution.
        """
        if amount <= 0:
            return 0
        amount_left = self.amount_left(current_price)
        if amount >= amount_left:
            self.shares = 0
            return amount_left
        self.shares -= amount / current_price
        return amount


class BaseInvestmentVehicle(ABC):
    """
    Base class for investment vehicles.

    Attributes
    ----------
    contributions : list[Contribution]
        The list of contributions made to the investment vehicle.
        Each contribution is represented as a Contribution object.
    current_value : float
        The current value of the investment vehicle.
    tags : list[str]
        Tax tags associated with the investment vehicle.
    """

    contributions: list[Contribution]
    current_value: float
    tags: list[str]

    @property
    def total(self) -> float:
        """
        Calculate the total value of the investment vehicle.

        Returns
        -------
        float
            The total value of the investment vehicle.
        """
        return sum(
            contribution.amount_left(self.current_value) for contribution in self.contributions
        )

    def add_contribution(
        self,
        amount: float,
        taxing_entity: BaseTaxingEntity,
        gross_salary_during_contribution: float,
    ) -> tuple[float, float, float]:
        """
        Add a contribution to the investment vehicle.

        It corresponds to the amount of money before any tax is applied.

        Parameters
        ----------
        amount : float
            The amount of money to add to the investment vehicle.
        taxing_entity : BaseTaxingEntity
            The taxing entity associated with the contribution.
        gross_salary_during_contribution : float
            The gross salary during the contribution period.

        Returns
        -------
        float
            The amount of money contributed to the investment vehicle after applying the tax.
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
        contribution = Contribution(
            buying_price=self.current_value,
            amount=after_tax_contribution,
        )
        self.contributions.append(contribution)
        return after_tax_contribution, tax_amount, 0.0

    def extract_contribution(
        self,
        gross_salary_during_extraction: float,
        taxing_entity: BaseTaxingEntity,
        after_tax_amount: float | None = None,
    ) -> tuple[float, float, float]:
        """
        Extract a contribution from the investment vehicle.

        It corresponds to the amount of money after every tax is applied.

        Parameters
        ----------
        gross_salary_during_extraction : float
            The gross salary during the extraction period.
        taxing_entity : BaseTaxingEntity
            The taxing entity associated with the extraction.
        after_tax_amount : float | None
            The amount of money to extract from the investment vehicle after taxes.
            If None, it corresponds to the total amount of money in the investment vehicle.
            Default is None.

        Returns
        -------
        float
            The amount of money extracted from the investment vehicle.
        float
            The amount of taxes applied to the extraction.
        float
            The amount of fees applied to the extraction.

        Raises
        ------
        ValueError
            If the amount to extract is greater than the total amount of money in the investment
            vehicle.
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
            extraction_fee=0.0,
            min_extraction_fee=0.0,
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
        Extract a gross amount from the investment vehicle.

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
            The amount of money extracted after applying taxes and fees.
        float
            The amount of taxes applied to the extraction.
        float
            The amount of fees applied to the extraction.

        Raises
        ------
        ValueError
            If the gross amount to extract is greater than the total amount of money in the
            investment vehicle.
        """
        if gross_amount > self.total:
            err_msg = (
                f"Cannot extract {gross_amount} from the investment vehicle, "
                f"which only has {self.total}."
            )
            raise ValueError(err_msg)

        fee_amount = 0.0
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

    def _extract_from_contributions(self, amount: float) -> None:
        """
        Extract a gross amount from contributions using FIFO order.

        Parameters
        ----------
        amount : float
            The gross amount of money to extract from the contributions.

        Raises
        ------
        ValueError
            If the amount to extract is greater than the total amount of money in the contributions.
        """
        left_to_extract = amount
        contribution_index = 0

        while left_to_extract > 0 and contribution_index < len(self.contributions):
            contribution = self.contributions[contribution_index]
            extracted_amount = contribution.extract(left_to_extract, self.current_value)
            left_to_extract -= extracted_amount

            if contribution.amount_left(self.current_value) <= 0:
                self.contributions.pop(contribution_index)
            else:
                contribution_index += 1

        if left_to_extract > 0:
            err_msg = f"Cannot extract {amount} from the available contributions."
            raise ValueError(err_msg)

    @abstractmethod
    def pass_year(self) -> None:
        """Pass a year in the investment vehicle."""

    def grow_lump_sum_contribution(
        self,
        amount: float,
        years: int,
        gross_salary_during_contribution: float,
        taxing_entity: BaseTaxingEntity,
    ) -> float:
        """
        Grow a lump sum contribution in the investment vehicle.

        Parameters
        ----------
        amount : float
            The amount of money to grow in the investment vehicle.
        years : int
            The number of years to grow the money in the investment vehicle.
        gross_salary_during_contribution : float
            The gross salary during the contribution period.
        taxing_entity : BaseTaxingEntity
            The taxing entity associated with the contribution.

        Returns
        -------
        float
            The amount of money after growing in the investment vehicle.
        """
        self.add_contribution(
            amount=amount,
            taxing_entity=taxing_entity,
            gross_salary_during_contribution=gross_salary_during_contribution,
        )
        for _ in range(years):
            self.pass_year()

        return self.total

    def grow_annual_contribution(
        self,
        amount: float,
        years: int,
        gross_salary_during_contribution: float,
        taxing_entity: BaseTaxingEntity,
    ) -> float:
        """
        Grow an annual contribution in the investment vehicle.

        Parameters
        ----------
        amount : float
            The amount of money to grow in the investment vehicle.
        years : int
            The number of years to grow the money in the investment vehicle.
        gross_salary_during_contribution : float
            The gross salary during the contribution period.
        taxing_entity : BaseTaxingEntity
            The taxing entity associated with the contribution.

        Returns
        -------
        float
            The amount of money after growing in the investment vehicle.
        """
        for _ in range(years):
            self.add_contribution(
                amount=amount,
                taxing_entity=taxing_entity,
                gross_salary_during_contribution=gross_salary_during_contribution,
            )

            self.pass_year()

        return self.total
