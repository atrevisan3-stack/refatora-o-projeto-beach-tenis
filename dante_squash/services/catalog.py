"""Cadastros de clientes (RF01), produtos (RF02) e tabela de valores (RF03)."""

from __future__ import annotations

from typing import Sequence

from dante_squash.domain import (
    BusinessRuleError,
    Customer,
    InternalProducts,
    PriceSchedule,
    Product,
)
from dante_squash.ports import UnitOfWorkFactory


class CatalogService:
    def __init__(self, unit_of_work: UnitOfWorkFactory, products: InternalProducts) -> None:
        self._unit_of_work = unit_of_work
        self._products = products

    # Clientes -----------------------------------------------------------------

    def customers(self) -> Sequence[Customer]:
        """Clientes cadastrados, sem o cliente interno da sauna."""
        with self._unit_of_work() as work:
            return [
                item
                for item in work.customers.list_all()
                if item.code != self._products.sauna_customer
            ]

    def customer(self, code: int) -> Customer:
        with self._unit_of_work() as work:
            customer = work.customers.get(code)
        if customer is None or code == self._products.sauna_customer:
            raise BusinessRuleError("Código de cliente não cadastrado!")
        return customer

    def save_customer(self, customer: Customer) -> Customer:
        """Inclui (código = maior + 1) ou altera um cliente (RN01)."""
        customer.validate()
        if customer.code == self._products.sauna_customer:
            raise BusinessRuleError("O cliente 0 é de uso interno da sauna!")
        with self._unit_of_work() as work:
            code = customer.code if customer.code is not None else work.customers.next_code()
            saved = Customer(
                code=code,
                name=customer.name.strip(),
                cpf=customer.cpf.strip(),
                birthday=customer.birthday.strip(),
                phone=customer.phone.strip(),
            )
            work.customers.save(saved)
        return saved

    def delete_customer(self, code: int) -> None:
        """Cliente com consumos, pagamentos ou reservas não pode ser excluído (RN02)."""
        if code == self._products.sauna_customer:
            raise BusinessRuleError("O cliente 0 é de uso interno da sauna!")
        with self._unit_of_work() as work:
            if work.customers.get(code) is None:
                raise BusinessRuleError("Código de cliente não cadastrado!")
            if work.customers.has_dependencies(code):
                raise BusinessRuleError(
                    "Este cliente foi utilizado em consumos, pagamentos ou reservas "
                    "e não pode ser excluído!"
                )
            work.customers.delete(code)

    # Produtos -----------------------------------------------------------------

    def products(self) -> Sequence[Product]:
        """Produtos vendáveis, sem os códigos internos."""
        with self._unit_of_work() as work:
            return [
                item
                for item in work.products.list_all()
                if not self._products.is_internal(item.code)
            ]

    def save_product(self, product: Product) -> Product:
        """Inclui ou altera um produto; códigos internos são protegidos (RN03)."""
        product.validate()
        with self._unit_of_work() as work:
            code = product.code if product.code is not None else work.products.next_code()
            saved = Product(
                code=code,
                description=product.description.strip(),
                price=product.price,
                unit=product.unit.strip(),
            )
            work.products.save(saved)
        return saved

    def delete_product(self, code: int) -> None:
        """Produto usado em algum consumo não pode ser excluído (RN04)."""
        if self._products.is_internal(code):
            raise BusinessRuleError("Os códigos 0 e 1 são de uso interno da aplicação!")
        with self._unit_of_work() as work:
            if work.products.get(code) is None:
                raise BusinessRuleError("Código de produto não cadastrado!")
            if work.products.is_used(code):
                raise BusinessRuleError(
                    "Este produto foi utilizado em consumos e não pode ser excluído!"
                )
            work.products.delete(code)

    # Valores ------------------------------------------------------------------

    def prices(self) -> PriceSchedule | None:
        with self._unit_of_work() as work:
            return work.prices.get()

    def save_prices(self, schedule: PriceSchedule) -> None:
        """Configuração única de valores, sobrescrita a cada gravação (RN05 a RN07)."""
        schedule.validate()
        with self._unit_of_work() as work:
            work.prices.save(schedule)
