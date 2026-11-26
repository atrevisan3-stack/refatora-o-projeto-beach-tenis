"""Dublês de teste: banco em memória com transação, relógio fixo e diálogos falsos.

O banco em memória segue o mesmo contrato das portas (``ports.py``) e desfaz
todas as alterações quando o caso de uso termina com erro, como o PostgreSQL.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from dante_squash.domain import (
    Consumption,
    Customer,
    PriceSchedule,
    Product,
    Reservation,
    SaunaAccount,
)


class InMemoryState:
    def __init__(self) -> None:
        self.customers: dict[int, Customer] = {0: Customer(0, "Cliente Sauna", "", "", "")}
        self.products: dict[int, Product] = {
            code: Product(code, description, Decimal("0"), "un")
            for code, description in (
                (0, "Saldo de pagamento"),
                (1, "Sauna"),
                (-1, "Mensalidade do Squash"),
                (-2, "Primeira Multa por atraso do Squash"),
                (-3, "Segunda Multa por atraso do Squash"),
            )
        }
        self.prices: PriceSchedule | None = None
        self.reservations: list[Reservation] = []
        self.consumptions: dict[tuple[int, date, int], Consumption] = {}
        self.sauna_names: dict[tuple[date, int], str] = {}
        self.payments: list[tuple[int, date, int, Decimal, bool]] = []
        self.monthly: set[tuple[int, int, str, int, int, int]] = set()


class InMemoryDatabase:
    def __init__(self) -> None:
        self.state = InMemoryState()


class InMemoryCustomers:
    def __init__(self, state: InMemoryState) -> None:
        self._s = state

    def list_all(self):
        return sorted(self._s.customers.values(), key=lambda c: c.name)

    def get(self, code):
        return self._s.customers.get(code)

    def next_code(self):
        return max(self._s.customers) + 1

    def save(self, customer):
        self._s.customers[customer.code] = customer

    def has_dependencies(self, code):
        s = self._s
        return (
            any(key[0] == code for key in s.consumptions)
            or any(p[0] == code for p in s.payments)
            or any(code in r.customer_ids for r in s.reservations)
            or any(m[0] == code for m in s.monthly)
        )

    def delete(self, code):
        del self._s.customers[code]


class InMemoryProducts:
    def __init__(self, state: InMemoryState) -> None:
        self._s = state

    def list_all(self):
        return sorted(self._s.products.values(), key=lambda p: p.code)

    def get(self, code):
        return self._s.products.get(code)

    def next_code(self):
        return max(max(self._s.products) + 1, 2)

    def save(self, product):
        self._s.products[product.code] = product

    def is_used(self, code):
        return any(c.product_code == code for c in self._s.consumptions.values())

    def delete(self, code):
        del self._s.products[code]


class InMemoryPrices:
    def __init__(self, state: InMemoryState) -> None:
        self._s = state

    def get(self):
        return self._s.prices

    def save(self, schedule):
        self._s.prices = schedule


class InMemoryReservations:
    def __init__(self, state: InMemoryState) -> None:
        self._s = state

    def list_all(self):
        return sorted(self._s.reservations, key=lambda r: (r.weekday, r.time, r.court))

    def replace(self, reservation):
        self.delete(reservation.weekday, reservation.time, reservation.court)
        self._s.reservations.append(reservation)

    def delete(self, weekday, time, court):
        self._s.reservations = [
            r
            for r in self._s.reservations
            if not (r.weekday == weekday and r.time == time and r.court == court)
        ]


class InMemoryConsumptions:
    def __init__(self, state: InMemoryState) -> None:
        self._s = state

    def _sorted(self, items):
        return sorted(items, key=lambda c: (c.date, c.customer_id, c.sequence))

    def for_customer(self, customer_id):
        return self._sorted(c for c in self._s.consumptions.values() if c.customer_id == customer_id)

    def unpaid_for_customer(self, customer_id):
        return [c for c in self.for_customer(customer_id) if not c.paid]

    def between(self, start, end):
        return self._sorted(c for c in self._s.consumptions.values() if start <= c.date <= end)

    def get(self, customer_id, consumption_date, sequence):
        return self._s.consumptions.get((customer_id, consumption_date, sequence))

    def insert(self, consumption):
        key = (consumption.customer_id, consumption.date, consumption.sequence)
        if key in self._s.consumptions:
            raise ValueError("chave primária duplicada em consumos")
        if consumption.customer_id not in self._s.customers:
            raise ValueError("cliente inexistente (chave estrangeira)")
        if consumption.product_code not in self._s.products:
            raise ValueError("produto inexistente (chave estrangeira)")
        self._s.consumptions[key] = consumption

    def delete(self, customer_id, consumption_date, sequence):
        self._s.consumptions.pop((customer_id, consumption_date, sequence), None)

    def next_sequence(self, customer_id, consumption_date):
        sequences = [
            key[2]
            for key in self._s.consumptions
            if key[0] == customer_id and key[1] == consumption_date
        ]
        return max(sequences, default=0) + 1

    def mark_unpaid_as_paid(self, customer_id):
        for key, item in list(self._s.consumptions.items()):
            if item.customer_id == customer_id and not item.paid:
                self._s.consumptions[key] = replace(item, paid=True)


class InMemoryPayments:
    def __init__(self, state: InMemoryState) -> None:
        self._s = state

    def record(self, customer_id, payment_date, amount, paid_in_full):
        sequence = 1 + max(
            (p[2] for p in self._s.payments if p[0] == customer_id and p[1] == payment_date),
            default=0,
        )
        self._s.payments.append((customer_id, payment_date, sequence, amount, paid_in_full))


class InMemorySauna:
    def __init__(self, state: InMemoryState, consumptions: InMemoryConsumptions) -> None:
        self._s = state
        self._consumptions = consumptions

    def accounts_for_date(self, account_date):
        grouped: dict[str, list[Consumption]] = {}
        for (day, sequence), name in sorted(self._s.sauna_names.items()):
            if day == account_date:
                grouped.setdefault(name, []).append(self._s.consumptions[(0, day, sequence)])
        return [
            SaunaAccount(name, account_date, tuple(items), all(i.paid for i in items))
            for name, items in sorted(grouped.items())
        ]

    def add_consumption(self, account_name, consumption):
        self._consumptions.insert(consumption)
        self._s.sauna_names[(consumption.date, consumption.sequence)] = account_name

    def remove_consumption(self, account_date, sequence):
        del self._s.sauna_names[(account_date, sequence)]
        self._consumptions.delete(0, account_date, sequence)

    def close_account(self, account, entrance_adjustment):
        for item in account.consumptions:
            key = (item.customer_id, item.date, item.sequence)
            self._s.consumptions[key] = replace(self._s.consumptions[key], paid=True)
        if entrance_adjustment:
            first = account.consumptions[0]
            key = (first.customer_id, first.date, first.sequence)
            current = self._s.consumptions[key]
            self._s.consumptions[key] = replace(
                current, unit_price=current.unit_price + entrance_adjustment
            )


class InMemoryMonthlyBilling:
    def __init__(self, state: InMemoryState) -> None:
        self._s = state

    def _key(self, customer_id, reservation, month, year):
        return (customer_id, reservation.weekday, reservation.time, reservation.court, month, year)

    def has_record(self, customer_id, reservation, month, year):
        return self._key(customer_id, reservation, month, year) in self._s.monthly

    def record(self, customer_id, reservation, month, year):
        self._s.monthly.add(self._key(customer_id, reservation, month, year))

    def has_fine_for_month(self, product_code, month, year):
        return any(
            c.product_code == product_code and c.date.month == month and c.date.year == year
            for c in self._s.consumptions.values()
        )

    def monthly_paid(self, customer_id, month, year):
        return any(
            c.customer_id == customer_id
            and c.product_code == -1
            and c.paid
            and c.date.month == month
            and c.date.year == year
            for c in self._s.consumptions.values()
        )


class InMemoryUnitOfWork:
    def __init__(self, database: InMemoryDatabase) -> None:
        self._database = database

    def __enter__(self):
        self._backup = copy.deepcopy(self._database.state)
        state = self._database.state
        self.customers = InMemoryCustomers(state)
        self.products = InMemoryProducts(state)
        self.prices = InMemoryPrices(state)
        self.reservations = InMemoryReservations(state)
        self.consumptions = InMemoryConsumptions(state)
        self.payments = InMemoryPayments(state)
        self.sauna = InMemorySauna(state, self.consumptions)
        self.monthly_billing = InMemoryMonthlyBilling(state)
        return self

    def __exit__(self, exception_type, exception, traceback):
        if exception_type is not None:
            self._database.state = self._backup
        return False


class InMemoryUnitOfWorkFactory:
    def __init__(self, database: InMemoryDatabase) -> None:
        self.database = database

    def __call__(self) -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(self.database)


class FixedClock:
    def __init__(self, today: date) -> None:
        self.current = today

    def today(self) -> date:
        return self.current

    def now(self) -> datetime:
        return datetime(self.current.year, self.current.month, self.current.day, 10, 30, 0)


class RecordingExporter:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []

    def export_all(self, directory, stamp):
        self.calls.append((directory, stamp))
        return [directory / f"clientes_{stamp}.csv"]


class FakeDialogs:
    """Registra as mensagens em vez de abrir janelas; respostas configuráveis."""

    def __init__(self) -> None:
        self.infos: list[tuple[str, str]] = []
        self.errors: list[tuple[str, str]] = []
        self.confirmations: list[str] = []
        self.confirm_answer = True
        self.directory = ""

    def info(self, title, message):
        self.infos.append((title, message))

    def error(self, title, message):
        self.errors.append((title, message))

    def confirm(self, title, message):
        self.confirmations.append(message)
        return self.confirm_answer

    def choose_directory(self, title):
        return self.directory

    def last_error(self) -> str:
        return self.errors[-1][1] if self.errors else ""

    def last_info(self) -> str:
        return self.infos[-1][1] if self.infos else ""
