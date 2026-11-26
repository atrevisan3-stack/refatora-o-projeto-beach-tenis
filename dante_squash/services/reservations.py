"""Reservas semanais de quadras (RF09) e grade do dia (RF10)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from dante_squash.domain import BusinessRuleError, Reservation, SquashCalendar
from dante_squash.ports import UnitOfWorkFactory


@dataclass(frozen=True)
class DayGridRow:
    time: str
    courts: tuple[str, ...]


class ReservationService:
    def __init__(self, unit_of_work: UnitOfWorkFactory, squash: SquashCalendar) -> None:
        self._unit_of_work = unit_of_work
        self._squash = squash

    def reservations(self) -> Sequence[Reservation]:
        with self._unit_of_work() as work:
            return work.reservations.list_all()

    def has_reservation(self, weekday: int, time: str, court: int) -> bool:
        with self._unit_of_work() as work:
            return any(
                item.weekday == weekday and item.time == time and item.court == court
                for item in work.reservations.list_all()
            )

    def save(self, reservation: Reservation, *, replace_existing: bool) -> None:
        """Mesma quadra, dia e horário substitui a reserva só com confirmação (RN20)."""
        reservation.validate()
        with self._unit_of_work() as work:
            for customer_id in reservation.customer_ids:
                if work.customers.get(customer_id) is None:
                    raise BusinessRuleError(f"Código de cliente {customer_id} não cadastrado!")
            existing = any(item.same_slot(reservation) for item in work.reservations.list_all())
            if existing and not replace_existing:
                raise BusinessRuleError(
                    "Já existe uma reserva para este horário; confirme a substituição."
                )
            work.reservations.replace(reservation)

    def delete(self, weekday: int, time: str, court: int) -> None:
        with self._unit_of_work() as work:
            if not any(
                item.weekday == weekday and item.time == time and item.court == court
                for item in work.reservations.list_all()
            ):
                raise BusinessRuleError("Reserva não encontrada!")
            work.reservations.delete(weekday, time, court)

    def day_grid(self, day: date) -> list[DayGridRow]:
        """Ocupantes de cada horário e quadra na data; aulas marcadas com (AULA)."""
        weekday = self._squash.weekday_of(day)
        with self._unit_of_work() as work:
            names = {item.code: item.name for item in work.customers.list_all()}
            reservations = [
                item for item in work.reservations.list_all() if item.weekday == weekday
            ]
        rows: list[DayGridRow] = []
        for time in self._squash.time_slots:
            cells: list[str] = []
            for court in self._squash.courts:
                found = next(
                    (r for r in reservations if r.time == time and r.court == court), None
                )
                cells.append(self._describe(found, names))
            rows.append(DayGridRow(time, tuple(cells)))
        return rows

    def _describe(self, reservation: Reservation | None, names: dict[int, str]) -> str:
        if reservation is None:
            return ""
        text = ", ".join(names.get(code, str(code)) for code in reservation.customer_ids)
        return text if reservation.is_game else f"{text} (AULA)"
