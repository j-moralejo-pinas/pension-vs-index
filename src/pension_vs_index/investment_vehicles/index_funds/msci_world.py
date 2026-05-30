"""MSCI World index investment vehicle."""

from pension_vs_index.investment_vehicles.index_funds.base_index_fund import BaseIndexFund


class MSCIWorld(BaseIndexFund):
    """
    MSCI World index investment vehicle.

    Attributes
    ----------
    annual_avg_return : float
        The average annual return of the MSCI World index.
    annual_return_std : float
        The standard deviation of the annual return of the MSCI World index.

    Parameters
    ----------
    annual_return : float
        The annual return of the MSCI World index. Default is 0.07 (7%).
    annual_return_std : float
        The standard deviation of the annual return of the MSCI World index. Default is 0.15 (15%).
    """

    annual_avg_return: float
    annual_return_std: float

    def __init__(self, annual_return: float = 0.07, annual_return_std: float = 0.15) -> None:
        self.annual_avg_return = annual_return
        self.annual_return_std = annual_return_std
        self.contributions = []
        self.current_value = 1.0

    def pass_year(self) -> None:
        """Simulate the passage of one year for the investment vehicle."""
        self.current_value *= 1 + self.annual_avg_return
