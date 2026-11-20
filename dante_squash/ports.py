"""Interfaces between application services and infrastructure adapters."""

from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import date
from decimal import Decimal
from typing import Protocol, Sequence

from dante_squash.domain import Consumption, Customer, PriceSchedule, Product, Reservation, SaunaAccount


class CustomerRepository(Protocol):
    def list_all(self) -> Sequence[Customer]: ...

    def next_code(self) -> int: ...

    def save(self, customer: Customer) -> None: ...


class ProductRepository(Protocol):
    def list_all(self) -> Sequence[Product]: ...

    def next_code(self) -> int: ...

    def save(self, product: Product) -> None: ...


class PriceScheduleRepository(Protocol):
    def get(self) -> PriceSchedule | None: ...

    def save(self, schedule: PriceSchedule) -> None: ...


class ReservationRepository(Protocol):
    def list_all(self) -> Sequence[Reservation]: ...

    def replace(self, reservation: Reservation) -> None: ...


class ConsumptionRepository(Protocol):
    def unpaid_for_customer(self, customer_id: int) -> Sequence[Consumption]: ...

    def insert(self, consumption: Consumption) -> None: ...

    def next_sequence(self, customer_id: int, consumption_date: date) -> int: ...

    def mark_unpaid_as_paid(self, customer_id: int) -> None: ...


class PaymentRepository(Protocol):
    def record(self, customer_id: int, payment_date: date, amount: Decimal, paid_in_full: bool) -> None: ...


class SaunaRepository(Protocol):
    def accounts_for_date(self, account_date: date) -> Sequence[SaunaAccount]: ...

    def create_account(self, account: SaunaAccount, entrance_price: Decimal) -> None: ...

    def add_consumption(self, account_name: str, account_date: date, consumption: Consumption) -> None: ...

    def close_account(self, account_name: str, account_date: date, amount_paid: Decimal) -> None: ...


class MonthlyBillingRepository(Protocol):
    def has_record(self, customer_id: int, reservation: Reservation, month: int, year: int) -> bool: ...

    def record(self, customer_id: int, reservation: Reservation, month: int, year: int) -> None: ...

    def has_fine_for_month(self, product_code: int, month: int, year: int) -> bool: ...

    def monthly_paid(self, customer_id: int, month: int, year: int) -> bool: ...


class UnitOfWork(Protocol):
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
    def __call__(self) -> AbstractContextManager[UnitOfWork]: ...
