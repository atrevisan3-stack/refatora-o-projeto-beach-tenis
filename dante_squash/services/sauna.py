"""Frequentadores avulsos da sauna: entrada, consumo e fechamento (RF06 a RF08)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Sequence

from dante_squash.domain import (
    BusinessRuleError,
    Consumption,
    InternalProducts,
    Money,
    SaunaAccount,
    SaunaRules,
)
from dante_squash.ports import Clock, UnitOfWork, UnitOfWorkFactory


class SaunaService:
    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory,
        clock: Clock,
        rules: SaunaRules,
        products: InternalProducts,
        money: Money,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._rules = rules
        self._products = products
        self._money = money

    def accounts(self, account_date: date) -> Sequence[SaunaAccount]:
        with self._unit_of_work() as work:
            return work.sauna.accounts_for_date(account_date)

    def add_attendee(self, name: str, account_date: date) -> SaunaAccount:
        """Inclui o frequentador e lança a entrada da sauna (RN14 a RN16)."""
        self._require_today(account_date)
        with self._unit_of_work() as work:
            prices = work.prices.get()
            if prices is None:
                raise BusinessRuleError("Configure os valores antes de registrar frequentadores.")
            existing = tuple(item.name for item in work.sauna.accounts_for_date(account_date))
            self._rules.validate_name(name, existing)
            entrance = self._new_consumption(
                work, account_date, self._products.sauna, 1, prices.sauna_price
            )
            work.sauna.add_consumption(name.strip(), entrance)
            return SaunaAccount(name.strip(), account_date, (entrance,), False)

    def remove_attendee(self, name: str, account_date: date) -> None:
        """Exclui o frequentador do dia, se a conta ainda estiver aberta."""
        self._require_today(account_date)
        with self._unit_of_work() as work:
            account = self._open_account(work, name, account_date)
            for item in account.consumptions:
                work.sauna.remove_consumption(account_date, item.sequence)

    def add_product_consumption(
        self,
        *,
        name: str,
        account_date: date,
        product_code: int,
        quantity: int,
    ) -> Consumption:
        self._require_today(account_date)
        if quantity <= 0:
            raise BusinessRuleError("A quantidade do produto deve ser informada!")
        with self._unit_of_work() as work:
            account = self._open_account(work, name, account_date)
            product = work.products.get(product_code)
            if product is None or self._products.is_internal(product.code):
                raise BusinessRuleError("Selecione um produto cadastrado para consumo.")
            consumption = self._new_consumption(
                work, account_date, product.code, quantity, product.price
            )
            work.sauna.add_consumption(account.name, consumption)
            return consumption

    def remove_product_consumption(self, name: str, account_date: date, sequence: int) -> None:
        """Exclui um consumo; a entrada da sauna não pode ser excluída (RN17)."""
        self._require_today(account_date)
        with self._unit_of_work() as work:
            account = self._open_account(work, name, account_date)
            item = next((c for c in account.consumptions if c.sequence == sequence), None)
            if item is None:
                raise BusinessRuleError("Consumo não encontrado para este frequentador.")
            if item.product_code == self._products.sauna:
                raise BusinessRuleError("A entrada da sauna não pode ser excluída!")
            work.sauna.remove_consumption(account_date, sequence)

    def close_account(self, name: str, account_date: date, amount_paid: Decimal) -> SaunaAccount:
        """Encerra a conta; a diferença (pago − total) ajusta a entrada (RN18)."""
        self._require_today(account_date)
        self._money.require_positive(amount_paid, "O valor a ser pago deve ser informado!")
        with self._unit_of_work() as work:
            account = self._open_account(work, name, account_date)
            adjustment = self._money.round(amount_paid - account.total)
            work.sauna.close_account(account, adjustment)
            work.payments.record(self._products.sauna_customer, account_date, amount_paid, True)
            return account

    def _new_consumption(
        self,
        work: UnitOfWork,
        account_date: date,
        product_code: int,
        quantity: int,
        unit_price: Decimal,
    ) -> Consumption:
        customer = self._products.sauna_customer
        return Consumption(
            customer_id=customer,
            date=account_date,
            sequence=work.consumptions.next_sequence(customer, account_date),
            product_code=product_code,
            quantity=quantity,
            unit_price=unit_price,
            paid=False,
        )

    def _open_account(self, work: UnitOfWork, name: str, account_date: date) -> SaunaAccount:
        account = next(
            (
                item
                for item in work.sauna.accounts_for_date(account_date)
                if item.name.casefold() == name.strip().casefold()
            ),
            None,
        )
        if account is None:
            raise BusinessRuleError("Frequentador da sauna não encontrado.")
        if account.closed:
            raise BusinessRuleError("A conta deste frequentador já foi encerrada!")
        return account

    def _require_today(self, account_date: date) -> None:
        if account_date != self._clock.today():
            raise BusinessRuleError(
                "Só é possível alterar os dados da sauna para o dia de hoje!"
            )
