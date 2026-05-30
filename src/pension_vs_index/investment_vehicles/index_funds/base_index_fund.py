"""Base class for index funds."""

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
