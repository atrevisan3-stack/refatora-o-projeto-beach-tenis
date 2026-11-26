"""Montagem de cenários de teste com os valores usados na Entrega 1 (seção 6.2)."""

from __future__ import annotations

from decimal import Decimal

from dante_squash.domain import Customer, DueTier, PriceSchedule, Product, Reservation
from dante_squash.services.application_services import ApplicationServices


class Scenario:
    """Sauna R$ 30,00; aula R$ 50,00; faixas (10, 200), (15, 220) e (20, 240)."""

    def __init__(self, services: ApplicationServices, clock) -> None:
        self.services = services
        self.clock = clock

    def default_prices(self) -> PriceSchedule:
        schedule = PriceSchedule(
            Decimal("30.00"),
            Decimal("50.00"),
            (
                DueTier(10, Decimal("200.00")),
                DueTier(15, Decimal("220.00")),
                DueTier(20, Decimal("240.00")),
            ),
        )
        self.services.catalog.save_prices(schedule)
        return schedule

    def customer(self, name: str) -> int:
        return self.services.catalog.save_customer(Customer(None, name, "", "", "")).code

    def product(self, description: str, price: str) -> int:
        return self.services.catalog.save_product(
            Product(None, description, Decimal(price), "un")
        ).code

    def game(self, weekday: int, time: str, court: int, *customer_ids: int) -> Reservation:
        reservation = Reservation(weekday, time, court, True, tuple(customer_ids))
        self.services.reservations.save(reservation, replace_existing=False)
        return reservation

    def lesson(self, weekday: int, time: str, court: int, customer_id: int) -> Reservation:
        reservation = Reservation(weekday, time, court, False, (customer_id,))
        self.services.reservations.save(reservation, replace_existing=False)
        return reservation
