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
        self,
        amount: float,
        gross_annual_salary: float,
        *,
        tags: list[str],
    ) -> tuple[float, float]:
        """
        Calculate the tax to apply to a given amount.

        Parameters
        ----------
        amount : float
            The amount of money to calculate the tax for.
        gross_annual_salary : float
            The gross annual salary.
        tags : list[str]
            Tax tags associated with the investment vehicle.

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
        *,
        tags: list[str],
        extraction_fee: float = 0.0,
        min_extraction_fee: float = 0.0,
    ) -> tuple[float, float, float]:
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
        tags : list[str]
            Tax tags associated with the investment vehicle.
        extraction_fee : float, optional
            The fee charged over the gross extraction amount, by default 0.0.
        min_extraction_fee : float, optional
            The minimum absolute extraction fee, by default 0.0.

        Returns
        -------
        float
            The amount extracted before applying the tax.
        float
            The amount of tax to apply to the given amount.
        float
            The amount of fees applied to the extraction.
        """

    @abstractmethod
    def calculate_gross_extraction_tax(
        self,
        gross_amount: float,
        gross_annual_salary: float,
        contributions: list[Contribution],
        current_price: float,
        *,
        tags: list[str],
        extraction_fee: float = 0.0,
        min_extraction_fee: float = 0.0,
    ) -> tuple[float, float, float]:
        """
        Calculate the tax and fees for a gross extraction.

        Parameters
        ----------
        gross_amount : float
            The amount of money to extract before taxes and fees.
        gross_annual_salary : float
            The gross annual salary.
        contributions : list[Contribution]
            The list of contributions made to the investment vehicle.
        current_price : float
            The current price of the investment vehicle.
        tags : list[str]
            Tax tags associated with the investment vehicle.
        extraction_fee : float, optional
            The fee charged over the gross extraction amount, by default 0.0.
        min_extraction_fee : float, optional
            The minimum absolute extraction fee, by default 0.0.

        Returns
        -------
        float
            The amount extracted after applying taxes and fees.
        float
            The amount of tax to apply to the gross extraction.
        float
            The amount of fees applied to the gross extraction.
        """
