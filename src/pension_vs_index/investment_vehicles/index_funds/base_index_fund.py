"""Base class for index funds."""

import random

from pension_vs_index.investment_vehicles.base_investment_vehicle import BaseInvestmentVehicle


class BaseIndexFund(BaseInvestmentVehicle):
    """
    Base class for index funds.

    Attributes
    ----------
    annual_avg_return : float
        The average annual return of the index fund.
    annual_return_std : float
        The standard deviation of the annual return of the index fund.

    Parameters
    ----------
    annual_avg_return : float
        The average annual return of the index fund.
    annual_return_std : float
        The standard deviation of the annual return of the index fund.
    """

    annual_avg_return: float
    annual_return_std: float

    def __init__(self, annual_avg_return: float, annual_return_std: float) -> None:
        self.annual_avg_return = annual_avg_return
        self.annual_return_std = annual_return_std
        self.contributions = []
        self.current_value = 1.0

    def pass_year(self) -> None:
        """
        Pass a year in the index fund.

        The fund share price is multiplied by one plus an annual return sampled from a normal
        distribution centered at ``annual_avg_return`` with standard deviation
        ``annual_return_std``. When the standard deviation is zero, the result is deterministic.

        Raises
        ------
        ValueError
            If the sampled annual return would make the fund value negative.
        """
        annual_return = random.gauss(self.annual_avg_return, self.annual_return_std)
        if annual_return < -1:
            err_msg = f"Annual return {annual_return} would make the index fund value negative."
            raise ValueError(err_msg)

        self.current_value *= 1 + annual_return
