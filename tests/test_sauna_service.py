from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import unittest

from dante_squash.domain import (
    BusinessRuleError,
    Consumption,
    DueTier,
    PriceSchedule,
    SaunaAccount,
)
from dante_squash.services.sauna import SaunaService


class _MemoryStore:
    def __init__(self) -> None:
        self.accounts: list[SaunaAccount] = []
        self.prices = self
        self.sauna = self
        self.consumptions = self
        self.created: list[tuple[str, date, Decimal]] = []
        self.schedule = PriceSchedule(
            Decimal("30.00"),
            Decimal("50.00"),
            (DueTier(10, Decimal("200.00")),),
        )

    @contextmanager
    def unit_of_work(self):
        yield self

    def get(self):
        return self.schedule

    def accounts_for_date(self, account_date: date):
        return [account for account in self.accounts if account.date == account_date]

    def create_account(self, account: SaunaAccount, entrance_price: Decimal) -> None:
        self.created.append((account.name, account.date, entrance_price))
        self.accounts.append(
            SaunaAccount(
                account.name,
                account.date,
                (Consumption(0, account.date, 1, 1, 1, entrance_price),),
            )
        )


class SaunaServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.today = date(2026, 3, 12)
        self.store = _MemoryStore()
        self.service = SaunaService(self.store.unit_of_work, clock=lambda: self.today)

    def test_attendee_creation_records_the_configured_entrance_price(self) -> None:
        self.service.add_attendee("Carla", self.today)

        self.assertEqual(self.store.created, [("Carla", self.today, Decimal("30.00"))])

    def test_duplicate_name_is_rejected_without_case_sensitivity(self) -> None:
        self.service.add_attendee("Carla", self.today)

        with self.assertRaises(BusinessRuleError):
            self.service.add_attendee("carla", self.today)

    def test_attendee_cannot_be_added_for_another_date(self) -> None:
        with self.assertRaises(BusinessRuleError):
            self.service.add_attendee("Carla", date(2026, 3, 11))


if __name__ == "__main__":
    unittest.main()
