"""Interfaces (portas) entre os serviços de aplicação e a infraestrutura."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol, Sequence

from dante_squash.domain import (
    Consumption,
    Customer,
    PriceSchedule,
    Product,
    Reservation,
    SaunaAccount,
)


class Clock(Protocol):
    def today(self) -> date: ...

    def now(self) -> datetime: ...


class CustomerRepository(Protocol):
    def list_all(self) -> Sequence[Customer]: ...

    def get(self, code: int) -> Customer | None: ...

    def next_code(self) -> int: ...

    def save(self, customer: Customer) -> None: ...

    def has_dependencies(self, code: int) -> bool: ...

    def delete(self, code: int) -> None: ...


class ProductRepository(Protocol):
    def list_all(self) -> Sequence[Product]: ...

    def get(self, code: int) -> Product | None: ...

    def next_code(self) -> int: ...

    def save(self, product: Product) -> None: ...

    def is_used(self, code: int) -> bool: ...

    def delete(self, code: int) -> None: ...


class PriceScheduleRepository(Protocol):
    def get(self) -> PriceSchedule | None: ...

    def save(self, schedule: PriceSchedule) -> None: ...


class ReservationRepository(Protocol):
    def list_all(self) -> Sequence[Reservation]: ...

    def replace(self, reservation: Reservation) -> None: ...

    def delete(self, weekday: int, time: str, court: int) -> None: ...


class ConsumptionRepository(Protocol):
    def for_customer(self, customer_id: int) -> Sequence[Consumption]: ...

    def unpaid_for_customer(self, customer_id: int) -> Sequence[Consumption]: ...

    def between(self, start: date, end: date) -> Sequence[Consumption]: ...

    def get(self, customer_id: int, consumption_date: date, sequence: int) -> Consumption | None: ...

    def insert(self, consumption: Consumption) -> None: ...

    def delete(self, customer_id: int, consumption_date: date, sequence: int) -> None: ...

    def next_sequence(self, customer_id: int, consumption_date: date) -> int: ...

    def mark_unpaid_as_paid(self, customer_id: int) -> None: ...


class PaymentRepository(Protocol):
    def record(
        self, customer_id: int, payment_date: date, amount: Decimal, paid_in_full: bool
    ) -> None: ...


class SaunaRepository(Protocol):
    def accounts_for_date(self, account_date: date) -> Sequence[SaunaAccount]: ...

    def add_consumption(self, account_name: str, consumption: Consumption) -> None: ...

    def remove_consumption(self, account_date: date, sequence: int) -> None: ...

    def close_account(
        self, account: SaunaAccount, entrance_adjustment: Decimal
    ) -> None: ...


class MonthlyBillingRepository(Protocol):
    def has_record(self, customer_id: int, reservation: Reservation, month: int, year: int) -> bool: ...

    def record(self, customer_id: int, reservation: Reservation, month: int, year: int) -> None: ...

    def has_fine_for_month(self, product_code: int, month: int, year: int) -> bool: ...

    def monthly_paid(self, customer_id: int, month: int, year: int) -> bool: ...


class UnitOfWork(Protocol):
    """Agrupa os repositórios de um caso de uso numa única transação."""

    customers: CustomerRepository
    products: ProductRepository
    prices: PriceScheduleRepository
    reservations: ReservationRepository
    consumptions: ConsumptionRepository
    payments: PaymentRepository
    sauna: SaunaRepository
    monthly_billing: MonthlyBillingRepository

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(self, exception_type: object, exception: object, traceback: object) -> bool | None: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...


class TableExporter(Protocol):
    """Exporta as tabelas do banco para arquivos (RF16)."""

    def export_all(self, directory: Path, stamp: str) -> Sequence[Path]: ...
