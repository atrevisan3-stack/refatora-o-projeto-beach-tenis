"""Squash monthly charge and late-fine calculations."""

from datetime import date
from decimal import Decimal

from dante_squash.domain import (
    Fine,
    PriceSchedule,
    Reservation,
    WEEKLY_LESSONS_PER_MONTH,
)


class SquashBillingService:
    def monthly_charge(self, reservation: Reservation, prices: PriceSchedule) -> Decimal:
        reservation.validate()
        prices.validate()
        if reservation.is_game:
            return prices.due_tiers[0].monthly_price / len(reservation.customer_ids)
        return prices.squash_lesson_price * WEEKLY_LESSONS_PER_MONTH

    def fine_for(
        self,
        *,
        generation_date: date,
        player_count: int,
        prices: PriceSchedule,
        already_generated_codes: frozenset[int],
        is_game: bool = True,
    ) -> Fine | None:
        if not is_game or player_count <= 0:
            return None
        prices.validate()

        first_due = prices.due_tiers[0]
        second_due = prices.due_tiers[1] if len(prices.due_tiers) > 1 else None
        third_due = prices.due_tiers[2] if len(prices.due_tiers) > 2 else None
        day = generation_date.day

        # Keep the existing behavior: an already generated first fine blocks the
        # second fine for the same month. This is documented as defect D01.
        if -2 in already_generated_codes:
            return None

        if (
            second_due is not None
            and third_due is not None
            and second_due.monthly_price is not None
            and third_due.monthly_price is not None
            and day > first_due.day
            and day >= second_due.day
            and day < third_due.day
        ):
            return Fine(
                product_code=-2,
                amount_per_player=(second_due.monthly_price - first_due.monthly_price)
                / player_count,
            )

        if -3 in already_generated_codes:
            return None
        if (
            second_due is None
            or third_due is None
            or second_due.monthly_price is None
            or third_due.monthly_price is None
        ):
            return None
        if (day > first_due.day and day >= third_due.day) or day < first_due.day:
            return Fine(
                product_code=-3,
                amount_per_player=(third_due.monthly_price - second_due.monthly_price)
                / player_count,
            )
        return None

