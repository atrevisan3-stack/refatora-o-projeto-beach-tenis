from datetime import date
from decimal import Decimal
import unittest

from dante_squash.domain import DueTier, PriceSchedule, Reservation
from dante_squash.services.squash_billing import SquashBillingService


class SquashBillingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prices = PriceSchedule(
            sauna_price=Decimal("30.00"),
            squash_lesson_price=Decimal("50.00"),
            due_tiers=(
                DueTier(day=10, monthly_price=Decimal("210.00")),
                DueTier(day=15, monthly_price=Decimal("230.00")),
                DueTier(day=20, monthly_price=Decimal("250.00")),
            ),
        )
        self.service = SquashBillingService()

    def test_game_monthly_charge_is_monthly_price_divided_by_players(self) -> None:
        reservation = Reservation(
            weekday=1,
            time="18:00",
            court=1,
            is_game=True,
            customer_ids=(2, 5, 9),
        )

        self.assertEqual(
            self.service.monthly_charge(reservation, self.prices),
            Decimal("70.00"),
        )

    def test_lesson_monthly_charge_is_four_weekly_lessons(self) -> None:
        reservation = Reservation(
            weekday=2,
            time="10:00",
            court=2,
            is_game=False,
            customer_ids=(2,),
        )

        self.assertEqual(
            self.service.monthly_charge(reservation, self.prices),
            Decimal("200.00"),
        )

    def test_first_fine_uses_price_difference_and_is_split_among_players(self) -> None:
        result = self.service.fine_for(
            generation_date=date(2026, 3, 16),
            player_count=2,
            prices=self.prices,
            already_generated_codes=frozenset(),
        )

        self.assertEqual(result.product_code, -2)
        self.assertEqual(result.amount_per_player, Decimal("10.00"))

    def test_second_fine_is_blocked_when_first_fine_exists_as_in_current_behavior(self) -> None:
        result = self.service.fine_for(
            generation_date=date(2026, 3, 21),
            player_count=2,
            prices=self.prices,
            already_generated_codes=frozenset({-2}),
        )

        self.assertIsNone(result)

    def test_fine_is_not_applied_to_lesson_reservations(self) -> None:
        self.assertIsNone(
            self.service.fine_for(
                generation_date=date(2026, 3, 16),
                player_count=1,
                prices=self.prices,
                already_generated_codes=frozenset(),
                is_game=False,
            )
        )


if __name__ == "__main__":
    unittest.main()
