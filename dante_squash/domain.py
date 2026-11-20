"""Domain entities and rules, independent of persistence and user interface."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final


class BusinessRuleError(ValueError):
    """Raised when an operation violates a documented business rule."""


@dataclass(frozen=True)
class Customer:
    code: int
    name: str
    cpf: str = ""
    birthday: str = ""
    phone: str = ""

    def validate(self) -> None:
        if not self.name.strip():
            raise BusinessRuleError("O nome do cliente deve ser informado!")
        if len(self.name) > 50:
            raise BusinessRuleError("O nome do cliente deve ter no máximo 50 caracteres!")
        if len(self.cpf) > 11 or len(self.birthday) > 8 or len(self.phone) > 15:
            raise BusinessRuleError("Os dados do cliente excedem o tamanho permitido.")


@dataclass(frozen=True)
class Product:
    code: int
    description: str
    price: Decimal
    unit: str

    def validate(self) -> None:
        if not self.description.strip():
            raise BusinessRuleError("A descrição do produto deve ser informada!")
        if len(self.description) > 100:
            raise BusinessRuleError("A descrição do produto deve ter no máximo 100 caracteres!")
        if self.price <= 0:
            raise BusinessRuleError("O preço do produto deve ser maior que zero!")
        if not self.unit.strip():
            raise BusinessRuleError("A unidade do produto deve ser informada!")
        if self.code in (0, 1):
            raise BusinessRuleError("Os códigos 0 e 1 são de uso interno da aplicação!")


@dataclass(frozen=True)
class DueTier:
    day: int
    monthly_price: Decimal | None


@dataclass(frozen=True)
class PriceSchedule:
    sauna_price: Decimal
    squash_lesson_price: Decimal
    due_tiers: tuple[DueTier, ...]

    def validate(self) -> None:
        if self.sauna_price <= 0:
            raise BusinessRuleError("O valor da sauna deve ser maior que zero!")
        if self.squash_lesson_price <= 0:
            raise BusinessRuleError("O valor da aula deve ser maior que zero!")
        if not 1 <= len(self.due_tiers) <= 3:
            raise BusinessRuleError("Deve existir ao menos a primeira faixa de vencimento.")

        seen_days: set[int] = set()
        for tier in self.due_tiers:
            if not 1 <= tier.day <= 28:
                raise BusinessRuleError("Os vencimentos devem estar entre os dias 1 e 28.")
            if tier.day in seen_days:
                raise BusinessRuleError("Os vencimentos devem ser diferentes.")
            seen_days.add(tier.day)
            if tier.monthly_price is None:
                raise BusinessRuleError("Dia e valor do vencimento devem ser informados juntos.")
            if tier.monthly_price <= 0:
                raise BusinessRuleError("O valor da mensalidade deve ser maior que zero.")


@dataclass(frozen=True)
class Reservation:
    weekday: int
    time: str
    court: int
    is_game: bool
    customer_ids: tuple[int, ...]

    def validate(self) -> None:
        if not 1 <= self.weekday <= 6:
            raise BusinessRuleError("O dia da reserva deve ser de segunda-feira a sábado.")
        if not 1 <= self.court <= 3:
            raise BusinessRuleError("A quadra deve ser 1, 2 ou 3.")
        if self.time not in SQUASH_TIME_SLOTS:
            raise BusinessRuleError("O horário da reserva é inválido.")
        if not self.customer_ids:
            raise BusinessRuleError("A reserva deve ter ao menos um cliente.")
        if any(customer_id <= 0 for customer_id in self.customer_ids):
            raise BusinessRuleError("O cliente da reserva deve estar cadastrado.")
        if len(set(self.customer_ids)) != len(self.customer_ids):
            raise BusinessRuleError("O cliente já foi incluído nesta reserva.")
        if not self.is_game and len(self.customer_ids) != 1:
            raise BusinessRuleError("A reserva de aula deve ser feita para apenas um cliente!")


@dataclass(frozen=True)
class Consumption:
    customer_id: int
    date: date
    sequence: int
    product_code: int
    quantity: int
    unit_price: Decimal
    paid: bool = False

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass(frozen=True)
class PaymentResult:
    paid_in_full: bool
    balance: Decimal
    discount_entry: Decimal


@dataclass(frozen=True)
class SaunaAccount:
    name: str
    date: date
    consumptions: tuple[Consumption, ...]
    closed: bool = False


@dataclass(frozen=True)
class Fine:
    product_code: int
    amount_per_player: Decimal


def calculate_payment(
    *,
    total_due: Decimal,
    amount_paid: Decimal,
    discount: Decimal,
) -> PaymentResult:
    # Keep IEEE-754 comparisons at this boundary to characterize the legacy
    # double behavior until the payment rules are explicitly approved for change.
    amount_paid_value = float(amount_paid)
    discount_value = float(discount)
    difference = float(total_due) - amount_paid_value - discount_value
    if amount_paid_value <= 0:
        raise BusinessRuleError("O valor a ser pago deve ser informado!")
    return PaymentResult(
        paid_in_full=difference == 0.0,
        balance=Decimal(str(difference)),
        discount_entry=Decimal(str(-discount_value)) if discount_value > 0 else Decimal("0"),
    )


def validate_sauna_name(name: str, existing_names: tuple[str, ...]) -> None:
    if not name.strip():
        raise BusinessRuleError("O nome do cliente deve ser informado!")
    if any(name.casefold() == existing.casefold() for existing in existing_names):
        raise BusinessRuleError("O nome do cliente deve ser diferente de outro cliente da sauna!")


WEEKLY_LESSONS_PER_MONTH: Final = 4
SQUASH_TIME_SLOTS: Final = (
    "10:00",
    "11:00",
    "12:00",
    "13:00",
    "14:00",
    "15:00",
    "15:45",
    "16:30",
    "17:15",
    "18:00",
    "18:45",
    "19:30",
    "20:15",
)
