from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import unittest

from dante_squash.domain import Consumption
from dante_squash.services.payments import PaymentService


class _MemoryStore:
    def __init__(self) -> None:
        self.items = [
            Consumption(7, date(2026, 3, 1), 1, 2, 2, Decimal("50.00")),
        ]
        self.records: list[tuple[int, date, Decimal, bool]] = []
        self.marked_customer_ids: list[int] = []
        self.consumptions = self
        self.payments = self

    @contextmanager
    def unit_of_work(self):
        yield self

    def unpaid_for_customer(self, customer_id: int):
        return [
            item for item in self.items
            if item.customer_id == customer_id and not item.paid
        ]

    def next_sequence(self, customer_id: int, consumption_date: date) -> int:
        matching = [
            item.sequence for item in self.items
            if item.customer_id == customer_id and item.date == consumption_date
        ]
        return max(matching, default=0) + 1

    def insert(self, consumption: Consumption) -> None:
        self.items.append(consumption)

    def mark_unpaid_as_paid(self, customer_id: int) -> None:
        self.marked_customer_ids.append(customer_id)
        self.items = [
            Consumption(
                item.customer_id,
                item.date,
                item.sequence,
                item.product_code,
                item.quantity,
                item.unit_price,
                True,
            )
            if item.customer_id == customer_id and not item.paid
            else item
            for item in self.items
        ]

    def record(self, customer_id: int, payment_date: date, amount: Decimal, paid_in_full: bool) -> None:
        self.records.append((customer_id, payment_date, amount, paid_in_full))


class PaymentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _MemoryStore()
        self.service = PaymentService(self.store.unit_of_work)

    def test_partial_payment_records_open_balance_and_quits_old_consumptions(self) -> None:
        result = self.service.settle(
            customer_id=7,
            payment_date=date(2026, 3, 20),
            amount_paid=Decimal("60.00"),
            discount=Decimal("0.00"),
        )

        self.assertFalse(result.paid_in_full)
        self.assertEqual(result.balance, Decimal("40.00"))
        self.assertEqual(self.store.records[0][2:], (Decimal("60.00"), False))
        self.assertEqual(self.store.items[-1].product_code, 0)
        self.assertEqual(self.store.items[-1].unit_price, Decimal("40.00"))
        self.assertFalse(self.store.items[-1].paid)
        self.assertTrue(self.store.items[0].paid)

    def test_discount_is_recorded_as_paid_negative_consumption(self) -> None:
        self.service.settle(
            customer_id=7,
            payment_date=date(2026, 3, 20),
            amount_paid=Decimal("90.00"),
            discount=Decimal("10.00"),
        )

        discount = next(item for item in self.store.items if item.product_code == 0)
        self.assertEqual(discount.unit_price, Decimal("-10.00"))
        self.assertTrue(discount.paid)
        self.assertEqual(self.store.records[0][3], True)


if __name__ == "__main__":
    unittest.main()
