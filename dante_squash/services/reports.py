"""Ficha do cliente (RF13), fluxo de caixa diário (RF14) e resumo mensal (RF15)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

from dante_squash.domain import (
    BusinessRuleError,
    Consumption,
    Customer,
    InternalProducts,
    Money,
    Reservation,
)
from dante_squash.ports import UnitOfWorkFactory


@dataclass(frozen=True)
class CustomerSheet:
    customer: Customer
    reservations: tuple[Reservation, ...]
    total_due: Decimal
    history: tuple[tuple[Consumption, str], ...]


@dataclass(frozen=True)
class CashFlowLine:
    category: str
    paid: Decimal
    unpaid: Decimal

    @property
    def sold(self) -> Decimal:
        return self.paid + self.unpaid


@dataclass(frozen=True)
class DailySummary:
    day: date
    lines: tuple[CashFlowLine, ...]

    @property
    def sold(self) -> Decimal:
        return sum((line.sold for line in self.lines), Decimal("0"))

    @property
    def paid(self) -> Decimal:
        return sum((line.paid for line in self.lines), Decimal("0"))

    @property
    def to_receive(self) -> Decimal:
        return self.sold - self.paid


class CashFlowClassifier:
    """Categoria de caixa de cada produto (RN28). Saldo e desconto ficam fora."""

    def __init__(self, products: InternalProducts) -> None:
        self._products = products
        self.categories = ("Sauna", "Squash", "Produtos")

    def category_of(self, product_code: int) -> str | None:
        if product_code == self._products.sauna:
            return "Sauna"
        if product_code in self._products.squash_codes():
            return "Squash"
        if product_code > self._products.sauna:
            return "Produtos"
        return None


class ReportService:
    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory,
        classifier: CashFlowClassifier,
        money: Money,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._classifier = classifier
        self._money = money

    def customer_sheet(self, customer_id: int) -> CustomerSheet:
        with self._unit_of_work() as work:
            customer = work.customers.get(customer_id)
            if customer is None or customer_id <= 0:
                raise BusinessRuleError("Código de cliente não cadastrado!")
            reservations = tuple(
                item
                for item in work.reservations.list_all()
                if customer_id in item.customer_ids
            )
            descriptions = {item.code: item.description for item in work.products.list_all()}
            history = tuple(
                (item, descriptions.get(item.product_code, str(item.product_code)))
                for item in work.consumptions.for_customer(customer_id)
            )
        total_due = self._money.round(
            sum((item.total for item, _ in history if not item.paid), self._money.zero())
        )
        return CustomerSheet(customer, reservations, total_due, history)

    def cash_flow(self, day: date) -> tuple[CashFlowLine, ...]:
        with self._unit_of_work() as work:
            items = work.consumptions.between(day, day)
        return self._lines(items)

    def monthly_summary(self, year: int, month: int) -> tuple[DailySummary, ...]:
        """Uma linha por dia do mês, inclusive o dia 31 (corrige D03)."""
        last_day = calendar.monthrange(year, month)[1]
        with self._unit_of_work() as work:
            items = work.consumptions.between(date(year, month, 1), date(year, month, last_day))
        return tuple(
            DailySummary(
                date(year, month, day),
                self._lines([item for item in items if item.date.day == day]),
            )
            for day in range(1, last_day + 1)
        )

    def _lines(self, items: Sequence[Consumption]) -> tuple[CashFlowLine, ...]:
        totals = {
            category: [self._money.zero(), self._money.zero()]
            for category in self._classifier.categories
        }
        for item in items:
            category = self._classifier.category_of(item.product_code)
            if category is None:
                continue
            totals[category][0 if item.paid else 1] += item.total
        return tuple(
            CashFlowLine(category, self._money.round(paid), self._money.round(unpaid))
            for category, (paid, unpaid) in totals.items()
        )
