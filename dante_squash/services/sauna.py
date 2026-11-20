"""Use cases for daily sauna visitors and their accounts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Callable, Sequence

from dante_squash.domain import (
    BusinessRuleError,
    Consumption,
    SaunaAccount,
    validate_sauna_name,
)
from dante_squash.ports import UnitOfWork


class SaunaService:
    def __init__(
        self,
        unit_of_work: Callable[[], UnitOfWork],
        *,
        clock: Callable[[], date] = date.today,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def accounts(self, account_date: date) -> Sequence[SaunaAccount]:
        with self._unit_of_work() as work:
            return work.sauna.accounts_for_date(account_date)

    def add_attendee(self, name: str, account_date: date) -> None:
        self._require_today(account_date)
        with self._unit_of_work() as work:
            schedule = work.prices.get()
            if schedule is None:
                raise BusinessRuleError("Configure os valores antes de registrar frequentadores.")
            existing_names = tuple(
                account.name for account in work.sauna.accounts_for_date(account_date)
            )
            validate_sauna_name(name, existing_names)
            work.sauna.create_account(
                SaunaAccount(name.strip(), account_date, ()),
                schedule.sauna_price,
            )

    def add_product_consumption(
        self,
        *,
        name: str,
        account_date: date,
        product_code: int,
        quantity: int,
    ) -> None:
        self._require_today(account_date)
        if quantity <= 0:
            raise BusinessRuleError("A quantidade do produto deve ser informada!")
        with self._unit_of_work() as work:
            account = self._find_open_account(work.sauna.accounts_for_date(account_date), name)
            product = next(
                (item for item in work.products.list_all() if item.code == product_code),
                None,
            )
            if product is None or product.code <= 1:
                raise BusinessRuleError("Selecione um produto cadastrado para consumo.")
            consumption = Consumption(
                customer_id=0,
                date=account_date,
                sequence=work.consumptions.next_sequence(0, account_date),
                product_code=product.code,
                quantity=quantity,
                unit_price=product.price,
            )
            work.sauna.add_consumption(account.name, account_date, consumption)

    def close_account(self, name: str, account_date: date, amount_paid: Decimal) -> None:
        self._require_today(account_date)
        if amount_paid <= 0:
            raise BusinessRuleError("O valor a ser pago deve ser informado!")
        with self._unit_of_work() as work:
            account = self._find_open_account(work.sauna.accounts_for_date(account_date), name)
            work.sauna.close_account(account.name, account_date, amount_paid)

    def _require_today(self, account_date: date) -> None:
        if account_date != self._clock():
            raise BusinessRuleError("Só é possível alterar os dados da sauna para o dia de hoje.")

    @staticmethod
    def _find_open_account(
        accounts: Sequence[SaunaAccount],
        name: str,
    ) -> SaunaAccount:
        account = next(
            (item for item in accounts if item.name.casefold() == name.casefold()),
            None,
        )
        if account is None:
            raise BusinessRuleError("Frequentador da sauna não encontrado.")
        if account.closed:
            raise BusinessRuleError("A conta do frequentador já foi finalizada.")
        return account
