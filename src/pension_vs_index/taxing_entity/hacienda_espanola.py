"""Class for handling tax calculations in Spain."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pension_vs_index.taxing_entity.base_tax_entity import BaseTaxingEntity

if TYPE_CHECKING:
    from pension_vs_index.investment_vehicles.base_investment_vehicle import Contribution


class HaciendaEspanola(BaseTaxingEntity):
    """
    Class for handling tax calculations in Spain.

    Attributes
    ----------
    contingencias_comunes_empresa : float
        The percentage of the employer's contribution to common contingencies.
    contingencias_profesionales_empresa : float
        The percentage of the employer's contribution to professional contingencies.
    desempleo_empresa : float
        The percentage of the employer's contribution to unemployment.
    fogasa_empresa : float
        The percentage of the employer's contribution to the Wage Guarantee Fund (FOGASA).
    formacion_profesional_empresa : float
        The percentage of the employer's contribution to professional training.
    mei_empresa : float
        The percentage of the employer's contribution to the Employment Incentives Fund (MEI).
    contingencias_comunes_trabajador : float
        The percentage of the worker's contribution to common contingencies.
    desempleo_trabajador : float
        The percentage of the worker's contribution to unemployment.
    formacion_profesional_trabajador : float
        The percentage of the worker's contribution to professional training.
    mei_trabajador : float
        The percentage of the worker's contribution to the Employment Incentives Fund (MEI).
    minimo_personal_estatal : float
        The personal minimum for the estatal IRPF tax.
    minimo_personal_autonomico : float
        The personal minimum for the autonomic IRPF tax.
    irpf_estatal : tuple[tuple[float, float], ...]
        The brackets and rates for the estatal IRPF tax.
    irpf_autonomico : tuple[tuple[float, float], ...]
        The brackets and rates for the autonomic IRPF tax.
    contribucion_ss_empresa : float
        The total percentage of the employer's contribution to social security.
    contribucion_ss_trabajador : float
        The total percentage of the worker's contribution to social security.
    ganancias_patrimoniales : tuple[tuple[float, float], ...]
        The brackets and rates for the capital gains tax.
    """

    contingencias_comunes_empresa: float = 0.236
    contingencias_profesionales_empresa: float = 0.015
    desempleo_empresa: float = 0.055
    fogasa_empresa: float = 0.002
    formacion_profesional_empresa: float = 0.006
    mei_empresa: float = 0.0075

    contingencias_comunes_trabajador: float = 0.047
    desempleo_trabajador: float = 0.0155
    formacion_profesional_trabajador: float = 0.001
    mei_trabajador: float = 0.0015

    minimo_personal_estatal: float = 5550.0
    minimo_personal_autonomico: float = 5956.65

    irpf_estatal: tuple[tuple[float, float], ...] = (
        (minimo_personal_estatal, 0.095),
        (12450.0, 0.12),
        (20200.0, 0.15),
        (35200.0, 0.185),
        (60000.0, 0.225),
        (300000.0, 0.245),
    )

    irpf_autonomico: tuple[tuple[float, float], ...] = (
        (minimo_personal_autonomico, 0.085),
        (13362.22, 0.107),
        (19004.63, 0.128),
        (35425.68, 0.174),
        (57320.4, 0.205),
    )

    contribucion_ss_empresa: float
    contribucion_ss_trabajador: float

    ganancias_patrimoniales: tuple[tuple[float, float], ...] = (
        (0, 0.19),
        (6000, 0.21),
        (50000, 0.23),
        (200000, 0.27),
        (300000, 0.30),
    )

    def __init__(self) -> None:
        self.contribucion_ss_empresa = (
            self.contingencias_comunes_empresa
            + self.contingencias_profesionales_empresa
            + self.desempleo_empresa
            + self.fogasa_empresa
            + self.formacion_profesional_empresa
            + self.mei_empresa
        )
        self.contribucion_ss_trabajador = (
            self.contingencias_comunes_trabajador
            + self.desempleo_trabajador
            + self.formacion_profesional_trabajador
            + self.mei_trabajador
        )

    def calculate_irpf(
        self, annual_salary_before_tax: float, irpf_rates: tuple[tuple[float, float], ...]
    ) -> float:
        """
        Calculate the IRPF tax to apply to a given annual salary.

        Parameters
        ----------
        annual_salary_before_tax : float
            The annual salary before tax.
        irpf_rates : tuple[tuple[float, float], ...]
            The IRPF tax rates to apply to the given annual salary.

        Returns
        -------
        float
            The amount of IRPF tax to apply to the given annual salary.
        """
        irpf = 0.0
        for i in range(len(irpf_rates)):
            if annual_salary_before_tax > irpf_rates[i][0]:
                if i + 1 < len(irpf_rates):
                    upper_bracket_amount = min(annual_salary_before_tax, irpf_rates[i + 1][0])
                else:
                    upper_bracket_amount = annual_salary_before_tax
                irpf += (upper_bracket_amount - irpf_rates[i][0]) * irpf_rates[i][1]
            else:
                break

        return irpf

    def calculate_contribution_tax(
        self, amount: float, gross_annual_salary: float, *, is_plan_de_pensiones: bool = False
    ) -> tuple[float, float]:
        """
        Calculate the tax to apply to a given amount.

        Parameters
        ----------
        amount : float
            The amount of money to calculate the tax for.
        gross_annual_salary : float
            The gross annual salary.
        is_plan_de_pensiones : bool, optional
            Whether the contribution is for a pension plan, by default False

        Returns
        -------
        float
            The amount contributed after applying the tax.
        float
            The amount of tax to apply to the given amount.
        """
        if is_plan_de_pensiones:
            return self.plan_de_pensiones_contribution_tax(amount)

        return self.regular_investment_vehicle_contribution_tax(amount, gross_annual_salary)

    def regular_investment_vehicle_contribution_tax(
        self, amount: float, gross_annual_salary: float
    ) -> tuple[float, float]:
        """
        Calculate the tax to apply to a given amount for a regular investment vehicle.

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
        worker_seguridad_social_contribution = (
            gross_annual_salary * self.contingencias_comunes_trabajador
        )
        amount_after_ss = gross_annual_salary - worker_seguridad_social_contribution
        irpf_estatal = self.calculate_irpf(amount_after_ss, self.irpf_estatal)
        irpf_autonomico = self.calculate_irpf(amount_after_ss, self.irpf_autonomico)
        irpf_total = irpf_estatal + irpf_autonomico
        salary_after_tax = amount_after_ss - irpf_total

        amount_after_tax = amount * salary_after_tax / gross_annual_salary

        tax_over_amount = amount - amount_after_tax

        return amount_after_tax, tax_over_amount

    def plan_de_pensiones_contribution_tax(self, amount: float) -> tuple[float, float]:
        """
        Calculate the tax to apply to a given amount for a pension plan.

        Parameters
        ----------
        amount : float
            The amount of money to calculate the tax for.

        Returns
        -------
        float
            The amount contributed after applying the tax.
        float
            The amount of tax to apply to the given amount.
        """
        worker_seguridad_social_contribution = amount * self.contingencias_comunes_trabajador
        amount_after_ss = amount - worker_seguridad_social_contribution

        return amount_after_ss, worker_seguridad_social_contribution

    def calculate_extraction_tax(
        self,
        after_tax_amount: float,
        gross_annual_salary: float,
        contributions: list[Contribution],
        current_price: float,
        *,
        is_plan_de_pensiones: bool = False,
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
        is_plan_de_pensiones : bool, optional
            Whether the extraction is for a pension plan, by default False

        Returns
        -------
        float
            The amount extracted before applying the tax.
        float
            The amount of tax to apply to the given amount.
        """
        if is_plan_de_pensiones:
            gross_extraction, tax = self.plan_de_pensiones_extraction_tax(
                after_tax_amount, gross_annual_salary
            )
            return gross_extraction, tax

        return self.regular_vehicle_investment_extraction_tax(
            after_tax_amount=after_tax_amount,
            contributions=contributions,
            current_price=current_price,
        )

    def regular_vehicle_investment_extraction_tax(
        self,
        after_tax_amount: float,
        contributions: list[Contribution],
        current_price: float,
    ) -> tuple[float, float]:
        """
        Calculate the tax to apply to a given amount for a regular investment vehicle.

        Parameters
        ----------
        after_tax_amount : float
            The amount of money to extract after taxes.
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

        Raises
        ------
        ValueError
            If the after_tax_amount is negative or if the tax calculation results in a non-positive
            net extraction.
        """
        if after_tax_amount <= 0:
            return 0.0, 0.0

        gross_extraction = 0.0
        total_tax = 0.0
        net_left_to_extract = after_tax_amount
        accumulated_gains = 0.0

        for contribution in contributions:
            contribution_amount_left = contribution.amount_left(current_price)
            gain_percentage = self._calculate_gain_percentage(contribution, current_price)

            while contribution_amount_left > 0 and net_left_to_extract > 0:
                tax_rate = self._marginal_capital_gains_tax_rate(accumulated_gains)
                tax_percentage = gain_percentage * tax_rate
                net_percentage = 1 - tax_percentage
                if net_percentage <= 0:
                    err_msg = "Cannot calculate a positive net extraction from this tax rate."
                    raise ValueError(err_msg)

                gross_available_in_bracket = contribution_amount_left
                if gain_percentage > 0:
                    next_bracket = self._next_capital_gains_bracket(accumulated_gains)
                    gross_available_in_bracket = min(
                        gross_available_in_bracket,
                        (next_bracket - accumulated_gains) / gain_percentage,
                    )

                net_available_in_bracket = gross_available_in_bracket * net_percentage
                if net_left_to_extract <= net_available_in_bracket:
                    gross_needed = net_left_to_extract / net_percentage
                    gross_extraction += gross_needed
                    total_tax += gross_needed * tax_percentage
                    return gross_extraction, total_tax

                gross_extraction += gross_available_in_bracket
                total_tax += gross_available_in_bracket * tax_percentage
                net_left_to_extract -= net_available_in_bracket
                contribution_amount_left -= gross_available_in_bracket
                accumulated_gains += gross_available_in_bracket * gain_percentage

        err_msg = f"Cannot extract {after_tax_amount} after tax from the available contributions."
        raise ValueError(err_msg)

    def _calculate_gain_percentage(
        self,
        contribution: Contribution,
        current_price: float,
    ) -> float:
        """
        Calculate taxable gain percentage for a contribution.

        Parameters
        ----------
        contribution : Contribution
            The contribution to calculate the gain percentage for.
        current_price : float
            The current price of the investment vehicle.

        Returns
        -------
        float
            The taxable gain percentage.
        """
        if current_price <= 0:
            return 0.0

        return max((current_price - contribution.buying_price) / current_price, 0.0)

    def _marginal_capital_gains_tax_rate(self, accumulated_gains: float) -> float:
        """
        Find the current marginal capital gains tax rate.

        Parameters
        ----------
        accumulated_gains : float
            The accumulated gains extracted so far in the extraction process.

        Returns
        -------
        float
            The marginal capital gains tax rate to apply to the next unit of gain.
        """
        tax_rate = self.ganancias_patrimoniales[0][1]
        for lower_bound, bracket_tax_rate in self.ganancias_patrimoniales:
            if accumulated_gains >= lower_bound:
                tax_rate = bracket_tax_rate
            else:
                break

        return tax_rate

    def _next_capital_gains_bracket(self, accumulated_gains: float) -> float:
        """
        Find the next capital gains bracket threshold.

        Parameters
        ----------
        accumulated_gains : float
            The accumulated gains extracted so far in the extraction process.

        Returns
        -------
        float
            The next capital gains bracket threshold.
        """
        for lower_bound, _ in self.ganancias_patrimoniales:
            if lower_bound > accumulated_gains:
                return lower_bound

        return float("inf")

    def plan_de_pensiones_extraction_tax(
        self,
        after_tax_amount: float,
        gross_annual_salary: float,
    ) -> tuple[float, float]:
        """
        Calculate the tax to apply to a given amount for a pension plan.

        Parameters
        ----------
        after_tax_amount : float
            The amount of money to extract after taxes.
        gross_annual_salary : float
            The gross annual salary.

        Returns
        -------
        float
            The amount extracted before applying the tax.
        float
            The amount of tax to apply to the given amount.

        Raises
        ------
        ValueError
            If the after_tax_amount is negative or if the tax calculation results in a non-positive
            net extraction.
        """
        if after_tax_amount <= 0:
            return 0.0, 0.0

        gross_extraction = 0.0
        total_tax = 0.0
        net_left_to_extract = after_tax_amount
        taxable_income = gross_annual_salary

        while net_left_to_extract > 0:
            tax_rate = self._marginal_irpf_tax_rate(taxable_income)
            net_percentage = 1 - tax_rate
            if net_percentage <= 0:
                err_msg = "Cannot calculate a positive net extraction from this tax rate."
                raise ValueError(err_msg)

            next_bracket = self._next_irpf_bracket(taxable_income)
            gross_available_in_bracket = next_bracket - taxable_income
            net_available_in_bracket = gross_available_in_bracket * net_percentage

            if net_left_to_extract <= net_available_in_bracket:
                gross_needed = net_left_to_extract / net_percentage
                gross_extraction += gross_needed
                total_tax += gross_needed * tax_rate
                return gross_extraction, total_tax

            gross_extraction += gross_available_in_bracket
            total_tax += gross_available_in_bracket * tax_rate
            taxable_income = next_bracket
            net_left_to_extract -= net_available_in_bracket

        return gross_extraction, total_tax

    def _marginal_irpf_tax_rate(self, taxable_income: float) -> float:
        """
        Find the combined estatal and autonomico marginal IRPF rate.

        Parameters
        ----------
        taxable_income : float
            The taxable income to evaluate.

        Returns
        -------
        float
            The combined marginal IRPF tax rate.
        """
        return self._marginal_tax_rate(taxable_income, self.irpf_estatal) + self._marginal_tax_rate(
            taxable_income, self.irpf_autonomico
        )

    def _marginal_tax_rate(
        self,
        amount: float,
        tax_rates: tuple[tuple[float, float], ...],
    ) -> float:
        """
        Find the marginal tax rate for a bracket table.

        Parameters
        ----------
        amount : float
            The amount to evaluate.
        tax_rates : tuple[tuple[float, float], ...]
            The tax rate brackets.

        Returns
        -------
        float
            The marginal tax rate.
        """
        tax_rate = 0.0
        for lower_bound, bracket_tax_rate in tax_rates:
            if amount >= lower_bound:
                tax_rate = bracket_tax_rate
            else:
                break

        return tax_rate

    def _next_irpf_bracket(self, taxable_income: float) -> float:
        """
        Find the next estatal or autonomico IRPF bracket threshold.

        Parameters
        ----------
        taxable_income : float
            The taxable income to evaluate.

        Returns
        -------
        float
            The next IRPF bracket threshold.
        """
        next_bracket = float("inf")
        for lower_bound, _ in (*self.irpf_estatal, *self.irpf_autonomico):
            if lower_bound > taxable_income:
                next_bracket = min(next_bracket, lower_bound)

        return next_bracket
