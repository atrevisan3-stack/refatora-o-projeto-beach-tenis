"""Atomic payment use case for registered customers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Callable

from dante_squash.domain import (
    BusinessRuleError,
    Consumption,
    PaymentResult,
    calculate_payment,
)
from dante_squash.ports import UnitOfWork


class PaymentService:
    def __init__(self, unit_of_work: Callable[[], UnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    def total_due(self, customer_id: int) -> Decimal:
        if customer_id <= 0:
            raise BusinessRuleError("O cliente deve ser informado!")
        with self._unit_of_work() as work:
            items = work.consumptions.unpaid_for_customer(customer_id)
        return sum((item.total for item in items), Decimal("0"))

    def settle(
        self,
        *,
        customer_id: int,
        payment_date: date,
        amount_paid: Decimal,
        discount: Decimal,
    ) -> PaymentResult:
        if customer_id <= 0:
            raise BusinessRuleError("O cliente deve ser informado!")
        if amount_paid <= 0:
            raise BusinessRuleError("O valor a ser pago deve ser informado!")

        with self._unit_of_work() as work:
            unpaid = work.consumptions.unpaid_for_customer(customer_id)
            total_due = sum((item.total for item in unpaid), Decimal("0"))
            result = calculate_payment(
                total_due=total_due,
                amount_paid=amount_paid,
                discount=discount,
            )
            work.payments.record(
                customer_id,
                payment_date,
                amount_paid,
                result.paid_in_full,
            )
            work.consumptions.mark_unpaid_as_paid(customer_id)

            if result.discount_entry:
                work.consumptions.insert(
                    Consumption(
                        customer_id=customer_id,
                        date=payment_date,
                        sequence=work.consumptions.next_sequence(customer_id, payment_date),
                        product_code=0,
                        quantity=1,
                        unit_price=result.discount_entry,
                        paid=True,
                    )
                )
            if result.balance:
                work.consumptions.insert(
                    Consumption(
                        customer_id=customer_id,
                        date=payment_date,
                        sequence=work.consumptions.next_sequence(customer_id, payment_date),
                        product_code=0,
                        quantity=1,
                        unit_price=result.balance,
                        paid=False,
                    )
                )
        return result
