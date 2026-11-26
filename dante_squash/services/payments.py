"""Pagamento de cliente cadastrado, em uma única transação (RF05)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from dante_squash.domain import (
    BusinessRuleError,
    Consumption,
    InternalProducts,
    Money,
    PaymentCalculator,
    PaymentResult,
)
from dante_squash.ports import UnitOfWork, UnitOfWorkFactory


class PaymentService:
    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory,
        calculator: PaymentCalculator,
        products: InternalProducts,
        money: Money,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._calculator = calculator
        self._products = products
        self._money = money

    def total_due(self, customer_id: int) -> Decimal:
        """Soma dos consumos não pagos do cliente, de todas as datas (RN10)."""
        self._require_customer(customer_id)
        with self._unit_of_work() as work:
            return self._total(work.consumptions.unpaid_for_customer(customer_id))

    def settle(
        self,
        *,
        customer_id: int,
        payment_date: date,
        amount_paid: Decimal,
        discount: Decimal,
    ) -> PaymentResult:
        """Grava o pagamento, quita os consumos e lança desconto e saldo (RN11, RN12)."""
        self._require_customer(customer_id)
        with self._unit_of_work() as work:
            if work.customers.get(customer_id) is None:
                raise BusinessRuleError("Código de cliente não cadastrado!")
            total_due = self._total(work.consumptions.unpaid_for_customer(customer_id))
            if total_due == 0:
                raise BusinessRuleError("Este cliente não possui valores em aberto!")
            result = self._calculator.calculate(
                total_due=total_due, amount_paid=amount_paid, discount=discount
            )
            work.payments.record(customer_id, payment_date, amount_paid, result.paid_in_full)
            work.consumptions.mark_unpaid_as_paid(customer_id)
            if result.discount_entry:
                self._balance_entry(work, customer_id, payment_date, result.discount_entry, True)
            if result.balance:
                self._balance_entry(work, customer_id, payment_date, result.balance, False)
        return result

    def _balance_entry(
        self,
        work: UnitOfWork,
        customer_id: int,
        payment_date: date,
        amount: Decimal,
        paid: bool,
    ) -> None:
        work.consumptions.insert(
            Consumption(
                customer_id=customer_id,
                date=payment_date,
                sequence=work.consumptions.next_sequence(customer_id, payment_date),
                product_code=self._products.balance,
                quantity=1,
                unit_price=amount,
                paid=paid,
            )
        )

    def _total(self, items) -> Decimal:
        return self._money.round(sum((item.total for item in items), self._money.zero()))

    def _require_customer(self, customer_id: int) -> None:
        if customer_id <= 0:
            raise BusinessRuleError("O cliente deve ser informado!")
