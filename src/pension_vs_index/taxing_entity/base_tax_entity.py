"""Base class for taxing entities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pension_vs_index.investment_vehicles.base_investment_vehicle import Contribution


class BaseTaxingEntity(ABC):
    """Base class for taxing entities."""

    @abstractmethod
    def calculate_contribution_tax(
        self, amount: float, gross_annual_salary: float
    ) -> tuple[float, float]:
        """
        Calculate the tax to apply to a given amount.

        Parameters
        ----------
        amount : float
            The amount of money to calculate the tax for.
        gross_annual_salary : float
            The gross annual salary.

        Returns
        -------
        float
            The amount contributed after applying the tax.
        float
            The amount of tax to apply to the given amount.
        """

    @abstractmethod
    def calculate_extraction_tax(
        self,
        after_tax_amount: float,
        gross_annual_salary: float,
        contributions: list[Contribution],
        current_price: float,
    ) -> tuple[float, float]:
        """
        Calculate the tax to apply to a given amount.

        Parameters
        ----------
        after_tax_amount : float
            The amount of money to extract after taxes.
        gross_annual_salary : float
            The gross annual salary.
        contributions : list[Contribution]
            The list of contributions made to the investment vehicle.
        current_price : float
            The current price of the investment vehicle.

        Returns
        -------
        float
            The amount extracted before applying the tax.
        float
            The amount of tax to apply to the given amount.
        """
