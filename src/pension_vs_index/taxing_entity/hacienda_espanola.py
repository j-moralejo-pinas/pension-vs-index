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
        if "plan_de_pensiones" in tags:
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
        salary_before_contribution = max(gross_annual_salary - amount, 0.0)
        amount_after_tax = self._salary_after_income_tax(
            gross_annual_salary
        ) - self._salary_after_income_tax(salary_before_contribution)

        tax_over_amount = amount - amount_after_tax

        return amount_after_tax, tax_over_amount

    def _salary_after_income_tax(self, gross_annual_salary: float) -> float:
        """
        Calculate net salary after worker social security and IRPF.

        Parameters
        ----------
        gross_annual_salary : float
            The gross annual salary.

        Returns
        -------
        float
            The salary after worker social-security contributions and IRPF.
        """
        worker_seguridad_social_contribution = (
            gross_annual_salary * self.contingencias_comunes_trabajador
        )
        amount_after_ss = gross_annual_salary - worker_seguridad_social_contribution
        irpf_estatal = self.calculate_irpf(amount_after_ss, self.irpf_estatal)
        irpf_autonomico = self.calculate_irpf(amount_after_ss, self.irpf_autonomico)

        return amount_after_ss - irpf_estatal - irpf_autonomico

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
        if "plan_de_pensiones" in tags:
            gross_extraction, tax, fee = self.plan_de_pensiones_extraction_tax(
                after_tax_amount=after_tax_amount,
                gross_annual_salary=gross_annual_salary,
                contributions=contributions,
                current_price=current_price,
                extraction_fee=extraction_fee,
                min_extraction_fee=min_extraction_fee,
            )
            return gross_extraction, tax, fee

        return self.regular_vehicle_investment_extraction_tax(
            after_tax_amount=after_tax_amount,
            contributions=contributions,
            current_price=current_price,
            extraction_fee=extraction_fee,
            min_extraction_fee=min_extraction_fee,
        )

    def calculate_gross_extraction_tax(
        self,
        gross_amount: float,
        gross_annual_salary: float,
        contributions: list[Contribution],
        current_price: float,
        *,
        tags: list[str],
        fee_amount: float = 0.0,
    ) -> float:
        """
        Calculate the tax for a gross extraction.

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
        fee_amount : float, optional
            The fee amount applied to the gross extraction, by default 0.0.

        Returns
        -------
        float
            The amount of tax to apply to the gross extraction.

        Raises
        ------
        ValueError
            If the requested gross amount is greater than the available contributions.
        """
        if gross_amount <= 0:
            return 0.0

        available_amount = sum(
            contribution.amount_left(current_price) for contribution in contributions
        )
        if gross_amount > available_amount:
            err_msg = f"Cannot extract {gross_amount} from the available contributions."
            raise ValueError(err_msg)

        if "plan_de_pensiones" in tags:
            return self._irpf_tax_for_gross_extraction(
                gross_extraction=gross_amount,
                gross_annual_salary=gross_annual_salary,
            )

        return self._regular_tax_for_gross_extraction(
            gross_extraction=gross_amount,
            contributions=contributions,
            current_price=current_price,
            fee_amount=fee_amount,
        )

    def regular_vehicle_investment_extraction_tax(
        self,
        after_tax_amount: float,
        contributions: list[Contribution],
        current_price: float,
        extraction_fee: float = 0.0,
        min_extraction_fee: float = 0.0,
    ) -> tuple[float, float, float]:
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
        if after_tax_amount <= 0:
            return 0.0, 0.0, 0.0

        return self._regular_gross_extraction_for_net_amount(
            after_tax_amount=after_tax_amount,
            contributions=contributions,
            current_price=current_price,
            extraction_fee=extraction_fee,
            min_extraction_fee=min_extraction_fee,
        )

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
        contributions: list[Contribution],
        current_price: float,
        extraction_fee: float = 0.0,
        min_extraction_fee: float = 0.0,
    ) -> tuple[float, float, float]:
        """
        Calculate the tax to apply to a given amount for a pension plan.

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
        if after_tax_amount <= 0:
            return 0.0, 0.0, 0.0

        return self._irpf_gross_extraction_for_net_amount(
            after_tax_amount=after_tax_amount,
            gross_annual_salary=gross_annual_salary,
            contributions=contributions,
            current_price=current_price,
            extraction_fee=extraction_fee,
            min_extraction_fee=min_extraction_fee,
        )

    def _regular_gross_extraction_for_net_amount(
        self,
        after_tax_amount: float,
        contributions: list[Contribution],
        current_price: float,
        extraction_fee: float,
        min_extraction_fee: float,
    ) -> tuple[float, float, float]:
        """
        Calculate a regular gross extraction exactly from a net amount.

        Parameters
        ----------
        after_tax_amount : float
            The amount of money to extract after taxes and fees.
        contributions : list[Contribution]
            The list of contributions made to the investment vehicle.
        current_price : float
            The current price of the investment vehicle.
        extraction_fee : float
            The fee charged over the gross extraction amount.
        min_extraction_fee : float
            The minimum absolute extraction fee.

        Returns
        -------
        float
            The gross extraction before taxes and fees.
        float
            The amount of tax to apply to the extraction.
        float
            The amount of fees applied to the extraction.

        Raises
        ------
        ValueError
            If the available contributions cannot provide the requested net amount or if tax makes
            positive net extraction impossible.
        """
        gross_extraction = 0.0
        total_tax = 0.0
        net_left_to_extract = after_tax_amount
        accumulated_gains = 0.0

        for contribution in contributions:
            contribution_amount_left = contribution.amount_left(current_price)
            cost_basis_percentage = self._cost_basis_percentage(contribution, current_price)

            while contribution_amount_left > 0 and net_left_to_extract > 0:
                fee_rate = self._marginal_fee_rate(
                    gross_extraction, extraction_fee, min_extraction_fee
                )
                taxable_gain_per_gross = max(1 - fee_rate - cost_basis_percentage, 0.0)
                tax_rate = self._marginal_capital_gains_tax_rate(accumulated_gains)
                tax_per_gross = taxable_gain_per_gross * tax_rate
                net_per_gross = 1 - fee_rate - tax_per_gross

                if taxable_gain_per_gross > 0 and net_per_gross <= 0:
                    err_msg = "Cannot calculate a positive net extraction from this tax rate."
                    raise ValueError(err_msg)

                gross_available = min(
                    contribution_amount_left,
                    self._gross_until_next_fee_boundary(
                        gross_extraction, extraction_fee, min_extraction_fee
                    ),
                    self._gross_until_next_capital_gains_bracket(
                        accumulated_gains, taxable_gain_per_gross
                    ),
                )

                net_available = gross_available * net_per_gross
                if net_per_gross > 0 and net_left_to_extract <= net_available:
                    gross_needed = net_left_to_extract / net_per_gross
                    total_tax += gross_needed * tax_per_gross
                    gross_amount = gross_extraction + gross_needed
                    fee_amount = self._percentage_fee(
                        gross_amount, extraction_fee, min_extraction_fee
                    )
                    return gross_amount, total_tax, fee_amount

                gross_extraction += gross_available
                total_tax += gross_available * tax_per_gross
                net_left_to_extract -= net_available
                accumulated_gains += gross_available * taxable_gain_per_gross
                contribution_amount_left -= gross_available

        err_msg = f"Cannot extract {after_tax_amount} after tax from the available contributions."
        raise ValueError(err_msg)

    def _irpf_gross_extraction_for_net_amount(
        self,
        after_tax_amount: float,
        gross_annual_salary: float,
        contributions: list[Contribution],
        current_price: float,
        extraction_fee: float,
        min_extraction_fee: float,
    ) -> tuple[float, float, float]:
        """
        Calculate a pension-plan gross extraction exactly from a net amount.

        Parameters
        ----------
        after_tax_amount : float
            The amount of money to extract after taxes and fees.
        gross_annual_salary : float
            The gross annual salary.
        contributions : list[Contribution]
            The list of contributions made to the investment vehicle.
        current_price : float
            The current price of the investment vehicle.
        extraction_fee : float
            The fee charged over the gross extraction amount.
        min_extraction_fee : float
            The minimum absolute extraction fee.

        Returns
        -------
        float
            The gross extraction before taxes and fees.
        float
            The amount of tax to apply to the extraction.
        float
            The amount of fees applied to the extraction.

        Raises
        ------
        ValueError
            If the available contributions cannot provide the requested net amount or if tax makes
            positive net extraction impossible.
        """
        available_amount = sum(
            contribution.amount_left(current_price) for contribution in contributions
        )
        gross_extraction = 0.0
        total_tax = 0.0
        net_left_to_extract = after_tax_amount

        while gross_extraction < available_amount and net_left_to_extract > 0:
            taxable_income = gross_annual_salary + gross_extraction
            tax_rate = self._marginal_irpf_tax_rate(taxable_income)
            if tax_rate >= 1:
                err_msg = "Cannot calculate a positive net extraction from this tax rate."
                raise ValueError(err_msg)

            fee_rate = self._marginal_fee_rate(gross_extraction, extraction_fee, min_extraction_fee)
            tax_per_gross = tax_rate
            net_per_gross = 1 - fee_rate - tax_per_gross
            gross_available = min(
                available_amount - gross_extraction,
                self._gross_until_next_fee_boundary(
                    gross_extraction, extraction_fee, min_extraction_fee
                ),
                self._next_irpf_bracket(taxable_income) - taxable_income,
            )

            net_available = gross_available * net_per_gross
            if net_per_gross > 0 and net_left_to_extract <= net_available:
                gross_needed = net_left_to_extract / net_per_gross
                total_tax += gross_needed * tax_per_gross
                gross_amount = gross_extraction + gross_needed
                fee_amount = self._percentage_fee(gross_amount, extraction_fee, min_extraction_fee)
                return gross_amount, total_tax, fee_amount

            gross_extraction += gross_available
            total_tax += gross_available * tax_per_gross
            net_left_to_extract -= net_available

        err_msg = f"Cannot extract {after_tax_amount} after tax from the available contributions."
        raise ValueError(err_msg)

    def _regular_tax_for_gross_extraction(
        self,
        gross_extraction: float,
        contributions: list[Contribution],
        current_price: float,
        fee_amount: float,
    ) -> float:
        """
        Calculate capital-gains tax for a gross extraction.

        Parameters
        ----------
        gross_extraction : float
            The gross extraction before taxes and fees.
        contributions : list[Contribution]
            The list of contributions made to the investment vehicle.
        current_price : float
            The current price of the investment vehicle.
        fee_amount : float
            The fee amount applied to the gross extraction.

        Returns
        -------
        float
            The capital-gains tax for the gross extraction.

        Raises
        ------
        ValueError
            If the gross extraction exceeds the available contributions.
        """
        if gross_extraction <= 0 or current_price <= 0:
            return 0.0

        net_sale_ratio = (gross_extraction - fee_amount) / gross_extraction
        gross_left_to_extract = gross_extraction
        accumulated_gains = 0.0
        total_tax = 0.0

        for contribution in contributions:
            if gross_left_to_extract <= 0:
                break

            contribution_amount_left = contribution.amount_left(current_price)
            gross_sold = min(gross_left_to_extract, contribution_amount_left)
            gain_per_gross_unit = max(
                net_sale_ratio - self._cost_basis_percentage(contribution, current_price),
                0.0,
            )
            gains_left = gross_sold * gain_per_gross_unit

            while gains_left > 0:
                tax_rate = self._marginal_capital_gains_tax_rate(accumulated_gains)
                next_bracket = self._next_capital_gains_bracket(accumulated_gains)
                gains_in_bracket = min(gains_left, next_bracket - accumulated_gains)
                total_tax += gains_in_bracket * tax_rate
                accumulated_gains += gains_in_bracket
                gains_left -= gains_in_bracket

            gross_left_to_extract -= gross_sold

        if gross_left_to_extract > 0:
            err_msg = f"Cannot extract {gross_extraction} from the available contributions."
            raise ValueError(err_msg)

        return total_tax

    def _irpf_tax_for_gross_extraction(
        self,
        gross_extraction: float,
        gross_annual_salary: float,
    ) -> float:
        """
        Calculate IRPF tax for a gross extraction.

        Parameters
        ----------
        gross_extraction : float
            The gross extraction before taxes and fees.
        gross_annual_salary : float
            The gross annual salary.

        Returns
        -------
        float
            The IRPF tax for the gross extraction.

        Raises
        ------
        ValueError
            If the marginal IRPF rate makes positive net extraction impossible.
        """
        gross_left_to_tax = gross_extraction
        taxable_income = gross_annual_salary
        total_tax = 0.0

        while gross_left_to_tax > 0:
            tax_rate = self._marginal_irpf_tax_rate(taxable_income)
            if tax_rate >= 1:
                err_msg = "Cannot calculate a positive net extraction from this tax rate."
                raise ValueError(err_msg)

            next_bracket = self._next_irpf_bracket(taxable_income)
            gross_in_bracket = min(gross_left_to_tax, next_bracket - taxable_income)
            total_tax += gross_in_bracket * tax_rate
            taxable_income += gross_in_bracket
            gross_left_to_tax -= gross_in_bracket

        return total_tax

    def _cost_basis_percentage(self, contribution: Contribution, current_price: float) -> float:
        """
        Calculate contribution cost basis as a percentage of current value.

        Parameters
        ----------
        contribution : Contribution
            The contribution to calculate the cost basis percentage for.
        current_price : float
            The current price of the investment vehicle.

        Returns
        -------
        float
            The cost basis percentage.
        """
        if current_price <= 0:
            return 0.0

        return contribution.buying_price / current_price

    def _marginal_fee_rate(
        self,
        gross_extraction: float,
        extraction_fee: float,
        min_extraction_fee: float,
    ) -> float:
        """
        Find the marginal fee rate at a gross extraction amount.

        Parameters
        ----------
        gross_extraction : float
            The gross extraction before the next marginal unit.
        extraction_fee : float
            The percentage extraction fee.
        min_extraction_fee : float
            The minimum absolute extraction fee.

        Returns
        -------
        float
            The marginal fee rate for the next gross unit.
        """
        if min_extraction_fee > 0 and gross_extraction < min_extraction_fee:
            return 1.0
        if extraction_fee <= 0:
            return 0.0
        if extraction_fee >= 1:
            return 1.0
        if min_extraction_fee > 0 and gross_extraction < min_extraction_fee / extraction_fee:
            return 0.0

        return extraction_fee

    def _gross_until_next_fee_boundary(
        self,
        gross_extraction: float,
        extraction_fee: float,
        min_extraction_fee: float,
    ) -> float:
        """
        Calculate gross amount available before the next fee mode starts.

        Parameters
        ----------
        gross_extraction : float
            The gross extraction before the next marginal unit.
        extraction_fee : float
            The percentage extraction fee.
        min_extraction_fee : float
            The minimum absolute extraction fee.

        Returns
        -------
        float
            The gross amount available before fee behavior changes.
        """
        if min_extraction_fee <= 0:
            return float("inf")
        if gross_extraction < min_extraction_fee:
            return min_extraction_fee - gross_extraction
        if extraction_fee <= 0 or extraction_fee >= 1:
            return float("inf")

        fee_threshold = min_extraction_fee / extraction_fee
        if gross_extraction < fee_threshold:
            return fee_threshold - gross_extraction

        return float("inf")

    def _gross_until_next_capital_gains_bracket(
        self,
        accumulated_gains: float,
        taxable_gain_per_gross: float,
    ) -> float:
        """
        Calculate gross amount available before the next capital-gains bracket.

        Parameters
        ----------
        accumulated_gains : float
            The accumulated gains extracted so far.
        taxable_gain_per_gross : float
            The taxable gain produced by each gross unit.

        Returns
        -------
        float
            The gross amount available before the next capital-gains bracket.
        """
        if taxable_gain_per_gross <= 0:
            return float("inf")

        return (
            self._next_capital_gains_bracket(accumulated_gains) - accumulated_gains
        ) / taxable_gain_per_gross

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
