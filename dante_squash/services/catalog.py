"""Use cases for customer, product, price, and reservation setup."""

from __future__ import annotations

from typing import Callable, Sequence

from dante_squash.domain import (
    BusinessRuleError,
    Customer,
    PriceSchedule,
    Product,
    Reservation,
)
from dante_squash.ports import UnitOfWork


class CatalogService:
    def __init__(self, unit_of_work: Callable[[], UnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    def customers(self) -> Sequence[Customer]:
        with self._unit_of_work() as work:
            return work.customers.list_all()

    def save_customer(self, customer: Customer) -> Customer:
        customer.validate()
        with self._unit_of_work() as work:
            saved = customer
            if saved.code <= 0:
                saved = Customer(
                    code=work.customers.next_code(),
                    name=customer.name.strip(),
                    cpf=customer.cpf,
                    birthday=customer.birthday,
                    phone=customer.phone,
                )
            work.customers.save(saved)
        return saved

    def products(self) -> Sequence[Product]:
        with self._unit_of_work() as work:
            return work.products.list_all()

    def save_product(self, product: Product) -> Product:
        product.validate()
        with self._unit_of_work() as work:
            saved = product
            if saved.code <= 0:
                saved = Product(
                    code=work.products.next_code(),
                    description=product.description.strip(),
                    price=product.price,
                    unit=product.unit.strip(),
                )
            work.products.save(saved)
        return saved

    def prices(self) -> PriceSchedule | None:
        with self._unit_of_work() as work:
            return work.prices.get()

    def save_prices(self, schedule: PriceSchedule) -> None:
        schedule.validate()
        with self._unit_of_work() as work:
            work.prices.save(schedule)

    def reservations(self) -> Sequence[Reservation]:
        with self._unit_of_work() as work:
            return work.reservations.list_all()

    def save_reservation(self, reservation: Reservation, *, replace_existing: bool) -> None:
        reservation.validate()
        with self._unit_of_work() as work:
            existing = any(
                item.weekday == reservation.weekday
                and item.time == reservation.time
                and item.court == reservation.court
                for item in work.reservations.list_all()
            )
            if existing and not replace_existing:
                raise BusinessRuleError(
                    "Já existe uma reserva para este horário; confirme a substituição."
                )
            work.reservations.replace(reservation)
