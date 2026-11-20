"""Use cases for products consumed by registered customers."""

from __future__ import annotations

from datetime import date
from typing import Callable

from dante_squash.domain import BusinessRuleError, Consumption
from dante_squash.ports import UnitOfWork


class ConsumptionService:
    def __init__(self, unit_of_work: Callable[[], UnitOfWork]) -> None:
        self._unit_of_work = unit_of_work

    def register(
        self,
        *,
        customer_id: int,
        product_code: int,
        quantity: int,
        consumption_date: date,
    ) -> Consumption:
        if customer_id <= 0:
            raise BusinessRuleError("O cliente deve ser informado!")
        if quantity <= 0:
            raise BusinessRuleError("A quantidade do Produto deve ser informada!")
        with self._unit_of_work() as work:
            if not any(customer.code == customer_id for customer in work.customers.list_all()):
                raise BusinessRuleError("Código de cliente não cadastrado!")
            product = next(
                (item for item in work.products.list_all() if item.code == product_code),
                None,
            )
            if product is None or product.code <= 1:
                raise BusinessRuleError("O produto consumido deve estar cadastrado.")
            if product.price <= 0:
                raise BusinessRuleError("O Preço do Produto deve ser informado!")
            consumption = Consumption(
                customer_id=customer_id,
                date=consumption_date,
                sequence=work.consumptions.next_sequence(customer_id, consumption_date),
                product_code=product.code,
                quantity=quantity,
                unit_price=product.price,
            )
            work.consumptions.insert(consumption)
            return consumption
