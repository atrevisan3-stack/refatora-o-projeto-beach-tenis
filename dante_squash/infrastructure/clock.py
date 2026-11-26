"""Relógio do sistema, injetado para que os testes controlem a data de hoje."""

from __future__ import annotations

from datetime import date, datetime


class SystemClock:
    def today(self) -> date:
        return date.today()

    def now(self) -> datetime:
        return datetime.now()
