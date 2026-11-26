"""Unidade de trabalho em memória usada pelos cenários BDD.

Implementa as mesmas portas (``dante_squash.ports``) que os adaptadores
PostgreSQL/MariaDB e reproduz a semântica das consultas legadas: mês base zero
lido da data DDMMAAAA, conta da sauna fechada quando todos os consumos estão
pagos e diferença do fechamento lançada na entrada. Assim os cenários exercitam
os serviços reais da aplicação sem depender de um servidor de banco de dados.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Iterator

from dante_squash.domain import Consumption, Customer, PriceSchedule, Product, Reservation, SaunaAccount


def _legacy_month_year(value: date) -> tuple[int, int]:
    """Replica o adaptador: a data é gravada como inteiro DDMMAAAA."""
    raw = str(int(value.strftime("%d%m%Y")))
    return int(raw[2:4]) - 1, int(raw[4:8])


class _Customers:
    def __init__(self) -> None:
        self.rows: dict[int, Customer] = {}

    def list_all(self) -> list[Customer]:
        return sorted(self.rows.values(), key=lambda item: item.name)

    def next_code(self) -> int:
        return max(self.rows, default=0) + 1

    def save(self, customer: Customer) -> None:
        self.rows[customer.code] = customer


class _Products:
    def __init__(self) -> None:
        # Carga padrão do sistema: códigos internos 0 (ajuste) e 1 (entrada da sauna).
        self.rows: dict[int, Product] = {
            0: Product(0, "Ajuste de saldo", Decimal("0.01"), "un"),
            1: Product(1, "Entrada sauna", Decimal("0.01"), "un"),
        }

    def list_all(self) -> list[Product]:
        return sorted(self.rows.values(), key=lambda item: item.code)

    def next_code(self) -> int:
        return max(self.rows, default=0) + 1

    def save(self, product: Product) -> None:
        self.rows[product.code] = product


class _Prices:
    def __init__(self) -> None:
        self.schedule: PriceSchedule | None = None

    def get(self) -> PriceSchedule | None:
        return self.schedule

    def save(self, schedule: PriceSchedule) -> None:
        self.schedule = schedule


class _Reservations:
    def __init__(self) -> None:
        self.rows: list[Reservation] = []

    def list_all(self) -> list[Reservation]:
        return list(self.rows)

    def replace(self, reservation: Reservation) -> None:
        slot = (reservation.weekday, reservation.time, reservation.court)
        self.rows = [item for item in self.rows if (item.weekday, item.time, item.court) != slot]
        self.rows.append(reservation)


class _Consumptions:
    def __init__(self) -> None:
        self.rows: list[Consumption] = []

    def unpaid_for_customer(self, customer_id: int) -> list[Consumption]:
        return [item for item in self.rows if item.customer_id == customer_id and not item.paid]

    def insert(self, consumption: Consumption) -> None:
        self.rows.append(consumption)

    def next_sequence(self, customer_id: int, consumption_date: date) -> int:
        return 1 + max(
            (
                item.sequence
                for item in self.rows
                if item.customer_id == customer_id and item.date == consumption_date
            ),
            default=0,
        )

    def mark_unpaid_as_paid(self, customer_id: int) -> None:
        self.rows = [
            replace(item, paid=True) if item.customer_id == customer_id and not item.paid else item
            for item in self.rows
        ]

    def of_customer(self, customer_id: int) -> list[Consumption]:
        return [item for item in self.rows if item.customer_id == customer_id]


class _Payments:
    def __init__(self) -> None:
        self.rows: list[tuple[int, date, Decimal, bool]] = []

    def record(self, customer_id: int, payment_date: date, amount: Decimal, paid_in_full: bool) -> None:
        self.rows.append((customer_id, payment_date, amount, paid_in_full))


class _Sauna:
    def __init__(self, consumptions: _Consumptions) -> None:
        self._consumptions = consumptions
        # (nome, data, sequência do consumo do cliente interno 0)
        self.links: list[tuple[str, date, int]] = []
        self.closings: list[tuple[str, date, Decimal]] = []

    def _items(self, name: str, account_date: date) -> list[Consumption]:
        sequences = {
            seq
            for nome, data, seq in self.links
            if nome.casefold() == name.casefold() and data == account_date
        }
        return sorted(
            (
                item
                for item in self._consumptions.rows
                if item.customer_id == 0 and item.date == account_date and item.sequence in sequences
            ),
            key=lambda item: item.sequence,
        )

    def accounts_for_date(self, account_date: date) -> list[SaunaAccount]:
        names = sorted({nome for nome, data, _ in self.links if data == account_date})
        accounts = []
        for name in names:
            items = tuple(self._items(name, account_date))
            accounts.append(SaunaAccount(name, account_date, items, all(item.paid for item in items)))
        return accounts

    def create_account(self, account: SaunaAccount, entrance_price: Decimal) -> None:
        consumption = Consumption(
            customer_id=0,
            date=account.date,
            sequence=self._consumptions.next_sequence(0, account.date),
            product_code=1,
            quantity=1,
            unit_price=entrance_price,
        )
        self.add_consumption(account.name, account.date, consumption)

    def add_consumption(self, account_name: str, account_date: date, consumption: Consumption) -> None:
        self._consumptions.insert(consumption)
        self.links.append((account_name, account_date, consumption.sequence))

    def close_account(self, account_name: str, account_date: date, amount_paid: Decimal) -> None:
        items = self._items(account_name, account_date)
        if not items:
            raise LookupError("Frequentador da sauna não encontrado.")
        total = sum((item.total for item in items), Decimal("0"))
        difference = amount_paid - total
        initial = items[0]
        keys = {item.sequence for item in items}
        updated = []
        for item in self._consumptions.rows:
            if item.customer_id == 0 and item.date == account_date and item.sequence in keys:
                item = replace(item, paid=True)
                if item.sequence == initial.sequence and difference:
                    item = replace(item, unit_price=item.unit_price + difference)
            updated.append(item)
        self._consumptions.rows = updated
        self.closings.append((account_name, account_date, amount_paid))


class _MonthlyBilling:
    def __init__(self, consumptions: _Consumptions) -> None:
        self._consumptions = consumptions
        self.keys: set[tuple[int, int, str, int, int, int]] = set()

    def has_record(self, customer_id: int, reservation: Reservation, month: int, year: int) -> bool:
        key = (customer_id, reservation.weekday, reservation.time, reservation.court, month, year)
        return key in self.keys

    def record(self, customer_id: int, reservation: Reservation, month: int, year: int) -> None:
        self.keys.add((customer_id, reservation.weekday, reservation.time, reservation.court, month, year))

    def has_fine_for_month(self, product_code: int, month: int, year: int) -> bool:
        return any(
            item.product_code == product_code and _legacy_month_year(item.date) == (month, year)
            for item in self._consumptions.rows
        )

    def monthly_paid(self, customer_id: int, month: int, year: int) -> bool:
        return any(
            item.customer_id == customer_id
            and item.product_code == -1
            and item.paid
            and _legacy_month_year(item.date) == (month, year)
            for item in self._consumptions.rows
        )


class InMemoryUnitOfWork:
    """Implementa ``dante_squash.ports.UnitOfWork`` com rollback por cópia do estado."""

    def __init__(self) -> None:
        self.customers = _Customers()
        self.products = _Products()
        self.prices = _Prices()
        self.reservations = _Reservations()
        self.consumptions = _Consumptions()
        self.payments = _Payments()
        self.sauna = _Sauna(self.consumptions)
        self.monthly_billing = _MonthlyBilling(self.consumptions)
        self.commits = 0
        self.rollbacks = 0

    def _snapshot(self) -> dict:
        return {
            "customers": dict(self.customers.rows),
            "products": dict(self.products.rows),
            "prices": self.prices.schedule,
            "reservations": list(self.reservations.rows),
            "consumptions": list(self.consumptions.rows),
            "payments": list(self.payments.rows),
            "links": list(self.sauna.links),
            "closings": list(self.sauna.closings),
            "monthly": set(self.monthly_billing.keys),
        }

    def _restore(self, state: dict) -> None:
        self.customers.rows = state["customers"]
        self.products.rows = state["products"]
        self.prices.schedule = state["prices"]
        self.reservations.rows = state["reservations"]
        self.consumptions.rows = state["consumptions"]
        self.payments.rows = state["payments"]
        self.sauna.links = state["links"]
        self.sauna.closings = state["closings"]
        self.monthly_billing.keys = state["monthly"]

    @contextmanager
    def __call__(self) -> Iterator["InMemoryUnitOfWork"]:
        state = self._snapshot()
        try:
            yield self
        except BaseException:
            self._restore(state)
            self.rollbacks += 1
            raise
        self.commits += 1
