from decimal import Decimal
import unittest

from dante_squash.domain import BusinessRuleError, DueTier, PriceSchedule


class PriceScheduleTests(unittest.TestCase):
    def test_accepts_required_and_complete_optional_due_tiers(self) -> None:
        schedule = PriceSchedule(
            sauna_price=Decimal("30.00"),
            squash_lesson_price=Decimal("50.00"),
            due_tiers=(
                DueTier(day=10, monthly_price=Decimal("200.00")),
                DueTier(day=15, monthly_price=Decimal("220.00")),
                DueTier(day=20, monthly_price=Decimal("240.00")),
            ),
        )

        schedule.validate()

    def test_rejects_first_due_day_outside_one_to_twenty_eight(self) -> None:
        for day in (0, 29):
            with self.subTest(day=day):
                schedule = PriceSchedule(
                    sauna_price=Decimal("30.00"),
                    squash_lesson_price=Decimal("50.00"),
                    due_tiers=(DueTier(day=day, monthly_price=Decimal("200.00")),),
                )

                with self.assertRaises(BusinessRuleError):
                    schedule.validate()

    def test_rejects_incomplete_or_repeated_optional_tiers(self) -> None:
        incomplete = PriceSchedule(
            sauna_price=Decimal("30.00"),
            squash_lesson_price=Decimal("50.00"),
            due_tiers=(
                DueTier(day=10, monthly_price=Decimal("200.00")),
                DueTier(day=15, monthly_price=None),
            ),
        )
        repeated_day = PriceSchedule(
            sauna_price=Decimal("30.00"),
            squash_lesson_price=Decimal("50.00"),
            due_tiers=(
                DueTier(day=10, monthly_price=Decimal("200.00")),
                DueTier(day=10, monthly_price=Decimal("220.00")),
            ),
        )

        with self.assertRaises(BusinessRuleError):
            incomplete.validate()
        with self.assertRaises(BusinessRuleError):
            repeated_day.validate()


if __name__ == "__main__":
    unittest.main()
