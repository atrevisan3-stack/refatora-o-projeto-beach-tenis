"""Squash monthly-charge and late-fine use cases."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Callable

from dante_squash.domain import BusinessRuleError, Consumption, PriceSchedule
from dante_squash.ports import UnitOfWork
from dante_squash.services.squash_billing import SquashBillingService


class MonthlyBillingService:
    def __init__(
        self,
        unit_of_work: Callable[[], UnitOfWork],
        calculator: SquashBillingService | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._calculator = calculator or SquashBillingService()

    def generate_monthly_charges(self, generation_date: date) -> int:
        with self._unit_of_work() as work:
            prices = self._require_prices(work.prices.get())
            month = generation_date.month - 1
            generated = 0
            for reservation in work.reservations.list_all():
                charge = self._calculator.monthly_charge(reservation, prices)
                for customer_id in reservation.customer_ids:
                    if work.monthly_billing.has_record(
                        customer_id, reservation, month, generation_date.year
                    ):
                        continue
                    work.consumptions.insert(
                        Consumption(
                            customer_id=customer_id,
                            date=generation_date,
                            sequence=work.consumptions.next_sequence(customer_id, generation_date),
                            product_code=-1,
                            quantity=1,
                            unit_price=charge,
                        )
                    )
                    work.monthly_billing.record(
                        customer_id, reservation, month, generation_date.year
                    )
                    generated += 1
            return generated

    def generate_fines(self, generation_date: date) -> int:
        with self._unit_of_work() as work:
            prices = self._require_prices(work.prices.get())
            month = generation_date.month - 1
            year = generation_date.year
            if work.monthly_billing.has_fine_for_month(-2, month, year):
                raise BusinessRuleError("As multas deste mês já foram geradas!")
            existing_codes = frozenset(
                code
                for code in (-2, -3)
                if work.monthly_billing.has_fine_for_month(code, month, year)
            )
            first_due_day = prices.due_tiers[0].day
            second_due_day = prices.due_tiers[1].day if len(prices.due_tiers) > 1 else None
            third_due_day = prices.due_tiers[2].day if len(prices.due_tiers) > 2 else None
            first_fine_period = (
                second_due_day is not None
                and third_due_day is not None
                and generation_date.day > first_due_day
                and generation_date.day >= second_due_day
                and generation_date.day < third_due_day
            )
            if not first_fine_period and -3 in existing_codes:
                raise BusinessRuleError("As multas deste mês já foram geradas!")
            if (
                self._calculator.fine_for(
                    generation_date=generation_date,
                    player_count=1,
                    prices=prices,
                    already_generated_codes=existing_codes,
                )
                is None
            ):
                raise BusinessRuleError(
                    "As multas não foram geradas porque está fora do período correto!"
                )
            generated = 0
            for reservation in work.reservations.list_all():
                if not reservation.is_game:
                    continue
                fine = self._calculator.fine_for(
                    generation_date=generation_date,
                    player_count=len(reservation.customer_ids),
                    prices=prices,
                    already_generated_codes=existing_codes,
                )
                if fine is None:
                    continue
                for customer_id in reservation.customer_ids:
                    if work.monthly_billing.monthly_paid(customer_id, month, year):
                        continue
                    work.consumptions.insert(
                        Consumption(
                            customer_id=customer_id,
                            date=generation_date,
                            sequence=work.consumptions.next_sequence(customer_id, generation_date),
                            product_code=fine.product_code,
                            quantity=1,
                            unit_price=fine.amount_per_player,
                        )
                    )
                    generated += 1
            return generated

    @staticmethod
    def _require_prices(prices: PriceSchedule | None) -> PriceSchedule:
        if prices is None:
            raise BusinessRuleError("Configure os valores antes de gerar mensalidades ou multas.")
        prices.validate()
        return prices
