"""Cálculo de mensalidades e multas do squash (RN22, RN23, RN25, RN26)."""

from __future__ import annotations

from decimal import Decimal

from dante_squash.domain import (
    Fine,
    InternalProducts,
    Money,
    PriceSchedule,
    Reservation,
    SquashCalendar,
)


class SquashBillingCalculator:
    def __init__(
        self,
        products: InternalProducts,
        squash: SquashCalendar,
        money: Money,
    ) -> None:
        self._products = products
        self._squash = squash
        self._money = money

    def monthly_charge(
        self,
        reservation: Reservation,
        prices: PriceSchedule,
        *,
        year: int,
        month: int,
    ) -> Decimal:
        """Jogo: mensal 1 ÷ jogadores (RN22). Aula: valor da aula × aulas do mês (RN23)."""
        reservation.validate()
        prices.validate()
        if reservation.is_game:
            first_tier = prices.due_tiers[0]
            return self._money.round(first_tier.monthly_price / len(reservation.customer_ids))
        lessons = self._squash.lessons_in_month(reservation.weekday, year, month)
        return self._money.round(prices.squash_lesson_price * lessons)

    def fine_code_for_day(self, day: int, prices: PriceSchedule) -> int | None:
        """Qual multa vale no dia: 1ª (RN25), 2ª (RN26) ou nenhuma."""
        first, second, third = prices.tier(1), prices.tier(2), prices.tier(3)
        if first is None or second is None or third is None:
            return None
        if day > first.day and day >= second.day and day < third.day:
            return self._products.first_fine
        if (day > first.day and day >= third.day) or day < first.day:
            return self._products.second_fine
        return None

    def fine_for(self, fine_code: int, prices: PriceSchedule, player_count: int) -> Fine:
        """Valor da multa por jogador: diferença entre faixas ÷ jogadores."""
        first, second, third = prices.tier(1), prices.tier(2), prices.tier(3)
        if fine_code == self._products.first_fine:
            difference = second.monthly_price - first.monthly_price
        else:
            difference = third.monthly_price - second.monthly_price
        return Fine(
            product_code=fine_code,
            amount_per_player=self._money.round(difference / player_count),
        )
