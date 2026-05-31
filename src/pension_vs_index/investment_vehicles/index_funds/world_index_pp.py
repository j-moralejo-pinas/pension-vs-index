"""World Index PP index investment vehicle."""

from pension_vs_index.investment_vehicles.index_funds.base_index_fund import BaseIndexFund


class WorldIndexPP(BaseIndexFund):
    """
    World Index PP investment vehicle.

    Attributes
    ----------
    annual_avg_return : float
        The average annual return of the World Index PP.
    annual_return_std : float
        The standard deviation of the annual return of the World Index PP.

    Parameters
    ----------
    annual_avg_return : float
        The annual return of the World Index PP. Default is 0.07 (7%).
    annual_return_std : float
        The standard deviation of the annual return of the World Index PP. Default is 0.0 (0%).
    """

    annual_avg_return: float
    annual_return_std: float

    def __init__(self, annual_avg_return: float = 0.07, annual_return_std: float = 0.0) -> None:
        super().__init__(
            annual_avg_return=annual_avg_return,
            annual_return_std=annual_return_std,
        )
