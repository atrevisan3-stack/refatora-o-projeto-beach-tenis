from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import unittest

from dante_squash.domain import BusinessRuleError, Customer, Product
from dante_squash.services.consumptions import ConsumptionService


class _MemoryStore:
    def __init__(self) -> None:
        self.customers = self
        self.products = self
        self.consumptions = self
        self.items = []

    @contextmanager
    def unit_of_work(self):
        yield self

    def list_all(self):
        return [
            Customer(2, "Ana"),
            Product(5, "Água", Decimal("5.00"), "un"),
        ]

    def next_sequence(self, customer_id, consumption_date):
        return 1

    def insert(self, consumption):
        self.items.append(consumption)


class ConsumptionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _MemoryStore()
        self.service = ConsumptionService(self.store.unit_of_work)

    def test_registers_product_consumption_for_existing_customer(self) -> None:
        item = self.service.register(
            customer_id=2,
            product_code=5,
            quantity=2,
            consumption_date=date(2026, 3, 12),
        )

        self.assertEqual(item.total, Decimal("10.00"))
        self.assertEqual(self.store.items, [item])

    def test_rejects_internal_product_codes(self) -> None:
        with self.assertRaises(BusinessRuleError):
            self.service.register(
                customer_id=2,
                product_code=1,
                quantity=1,
                consumption_date=date(2026, 3, 12),
            )
        self.assertEqual(self.store.items, [])


if __name__ == "__main__":
    unittest.main()
