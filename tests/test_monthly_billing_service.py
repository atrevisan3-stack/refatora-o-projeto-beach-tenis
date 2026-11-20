from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import unittest

from dante_squash.domain import Consumption, DueTier, PriceSchedule, Reservation
from dante_squash.services.monthly_billing import MonthlyBillingService


class _MemoryStore:
    def __init__(self) -> None:
        self.reservations = self
        self.prices = self
        self.monthly_billing = self
        self.consumptions = self
        self.schedule = PriceSchedule(
            Decimal("30.00"),
            Decimal("50.00"),
            (DueTier(10, Decimal("200.00")),),
        )
        self.bookings = [
            Reservation(1, "18:00", 1, True, (2, 5)),
        ]
        self.monthly_keys: set[tuple[int, int, str, int, int, int]] = set()
        self.items: list[Consumption] = []

    @contextmanager
    def unit_of_work(self):
        yield self

    def get(self):
        return self.schedule

    def list_all(self):
        return self.bookings

    def has_record(self, customer_id, reservation, month, year):
        return (
            customer_id,
            reservation.weekday,
            reservation.time,
            reservation.court,
            month,
            year,
        ) in self.monthly_keys

    def record(self, customer_id, reservation, month, year):
        self.monthly_keys.add(
            (
                customer_id,
                reservation.weekday,
                reservation.time,
                reservation.court,
                month,
                year,
            )
        )

    def has_fine_for_month(self, product_code, month, year):
        return any(
            item.product_code == product_code and item.date.month == month and item.date.year == year
            for item in self.items
        )

    def monthly_paid(self, customer_id, month, year):
        return False

    def unpaid_for_customer(self, customer_id):
        return []

    def next_sequence(self, customer_id, consumption_date):
        return 1 + max(
            (
                item.sequence
                for item in self.items
                if item.customer_id == customer_id and item.date == consumption_date
            ),
            default=0,
        )

    def insert(self, consumption):
        self.items.append(consumption)


class MonthlyBillingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _MemoryStore()
        self.service = MonthlyBillingService(self.store.unit_of_work)

    def test_monthly_generation_is_once_per_customer_reservation_and_month(self) -> None:
        generation_date = date(2026, 3, 12)

        generated = self.service.generate_monthly_charges(generation_date)
        generated_again = self.service.generate_monthly_charges(generation_date)

        self.assertEqual(generated, 2)
        self.assertEqual(generated_again, 0)
        self.assertEqual([item.unit_price for item in self.store.items], [
            Decimal("100.00"),
            Decimal("100.00"),
        ])
        self.assertTrue(all(item.product_code == -1 for item in self.store.items))


if __name__ == "__main__":
    unittest.main()
