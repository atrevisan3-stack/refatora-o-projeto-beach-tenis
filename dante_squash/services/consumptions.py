"""Consumo de produtos por clientes cadastrados (RF04)."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from dante_squash.domain import BusinessRuleError, Consumption, InternalProducts
from dante_squash.ports import UnitOfWorkFactory


class ConsumptionService:
    def __init__(self, unit_of_work: UnitOfWorkFactory, products: InternalProducts) -> None:
        self._unit_of_work = unit_of_work
        self._products = products

    def register(
        self,
        *,
        customer_id: int,
        product_code: int,
        quantity: int,
        consumption_date: date,
    ) -> Consumption:
        """Lança o consumo com o preço atual do produto (RN08)."""
        if customer_id <= 0:
            raise BusinessRuleError("O cliente deve ser informado!")
        if quantity <= 0:
            raise BusinessRuleError("A quantidade do Produto deve ser informada!")
        with self._unit_of_work() as work:
            if work.customers.get(customer_id) is None:
                raise BusinessRuleError("Código de cliente não cadastrado!")
            product = work.products.get(product_code)
            if product is None or self._products.is_internal(product.code):
                raise BusinessRuleError("O produto consumido deve estar cadastrado!")
            consumption = Consumption(
                customer_id=customer_id,
                date=consumption_date,
                sequence=work.consumptions.next_sequence(customer_id, consumption_date),
                product_code=product.code,
                quantity=quantity,
                unit_price=product.price,
                paid=False,
            )
            work.consumptions.insert(consumption)
            return consumption

    def for_customer(self, customer_id: int) -> Sequence[Consumption]:
        with self._unit_of_work() as work:
            return work.consumptions.for_customer(customer_id)

    def delete(self, customer_id: int, consumption_date: date, sequence: int) -> None:
        """Consumo já pago não pode ser excluído (RN09)."""
        with self._unit_of_work() as work:
            consumption = work.consumptions.get(customer_id, consumption_date, sequence)
            if consumption is None:
                raise BusinessRuleError("Consumo não encontrado!")
            if consumption.paid:
                raise BusinessRuleError(
                    "Este consumo já foi pago e não pode ser mais excluído!"
                )
            work.consumptions.delete(customer_id, consumption_date, sequence)
