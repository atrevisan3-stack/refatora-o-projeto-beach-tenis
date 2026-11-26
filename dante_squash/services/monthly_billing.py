"""Geração de mensalidades (RF11) e de multas por atraso (RF12)."""

from __future__ import annotations

from datetime import date

from dante_squash.domain import (
    BusinessRuleError,
    Consumption,
    InternalProducts,
    PriceSchedule,
)
from dante_squash.ports import UnitOfWork, UnitOfWorkFactory
from dante_squash.services.squash_billing import SquashBillingCalculator


class MonthlyBillingService:
    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory,
        calculator: SquashBillingCalculator,
        products: InternalProducts,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._calculator = calculator
        self._products = products

    def generate_monthly_charges(self, generation_date: date) -> list[Consumption]:
        """Uma mensalidade por cliente, reserva e mês (RN24)."""
        month, year = generation_date.month, generation_date.year
        generated: list[Consumption] = []
        with self._unit_of_work() as work:
            prices = self._require_prices(work.prices.get())
            for reservation in work.reservations.list_all():
                charge = self._calculator.monthly_charge(
                    reservation, prices, year=year, month=month
                )
                for customer_id in reservation.customer_ids:
                    if work.monthly_billing.has_record(customer_id, reservation, month, year):
                        continue
                    consumption = self._charge(
                        work, customer_id, generation_date, self._products.monthly_fee, charge
                    )
                    work.monthly_billing.record(customer_id, reservation, month, year)
                    generated.append(consumption)
        return generated

    def generate_fines(self, generation_date: date) -> list[Consumption]:
        """1ª ou 2ª multa conforme o dia; cada uma uma vez por mês (RN25 a RN27).

        Corrige o defeito D01: a existência da 1ª multa não impede mais a 2ª.
        """
        month, year = generation_date.month, generation_date.year
        generated: list[Consumption] = []
        with self._unit_of_work() as work:
            prices = self._require_prices(work.prices.get())
            fine_code = self._calculator.fine_code_for_day(generation_date.day, prices)
            if fine_code is None:
                raise BusinessRuleError(
                    "As multas não foram geradas porque está fora do período correto!"
                )
            if work.monthly_billing.has_fine_for_month(fine_code, month, year):
                raise BusinessRuleError("As multas deste mês já foram geradas!")
            for reservation in work.reservations.list_all():
                if not reservation.is_game:
                    continue
                fine = self._calculator.fine_for(
                    fine_code, prices, len(reservation.customer_ids)
                )
                for customer_id in reservation.customer_ids:
                    if work.monthly_billing.monthly_paid(customer_id, month, year):
                        continue
                    generated.append(
                        self._charge(
                            work,
                            customer_id,
                            generation_date,
                            fine.product_code,
                            fine.amount_per_player,
                        )
                    )
        return generated

    def _charge(
        self,
        work: UnitOfWork,
        customer_id: int,
        charge_date: date,
        product_code: int,
        amount,
    ) -> Consumption:
        consumption = Consumption(
            customer_id=customer_id,
            date=charge_date,
            sequence=work.consumptions.next_sequence(customer_id, charge_date),
            product_code=product_code,
            quantity=1,
            unit_price=amount,
            paid=False,
        )
        work.consumptions.insert(consumption)
        return consumption

    def _require_prices(self, prices: PriceSchedule | None) -> PriceSchedule:
        if prices is None:
            raise BusinessRuleError("Configure os valores antes de gerar mensalidades ou multas.")
        prices.validate()
        return prices
