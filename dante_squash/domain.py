"""Entidades e regras de negócio, independentes de banco de dados e interface.

Nenhuma classe deste módulo usa métodos ou atributos estáticos: constantes de
negócio ficam em objetos (``InternalProducts``, ``SquashCalendar``, ``Money``)
criados e injetados por quem os usa.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


class BusinessRuleError(ValueError):
    """Violação de uma regra de negócio documentada na Entrega 1."""


class InternalProducts:
    """Códigos de produto reservados pelo sistema (RN29)."""

    def __init__(self) -> None:
        self.balance = 0
        self.sauna = 1
        self.monthly_fee = -1
        self.first_fine = -2
        self.second_fine = -3
        self.sauna_customer = 0

    def is_internal(self, product_code: int) -> bool:
        return product_code <= self.sauna

    def squash_codes(self) -> tuple[int, int, int]:
        return (self.monthly_fee, self.first_fine, self.second_fine)


class Money:
    """Arredondamento e validação de valores monetários (corrige D04 e D05)."""

    def __init__(self) -> None:
        self._cent = Decimal("0.01")
        self._zero = Decimal("0")

    def zero(self) -> Decimal:
        return self._zero

    def round(self, value: Decimal) -> Decimal:
        return value.quantize(self._cent, rounding=ROUND_HALF_UP)

    def require_positive(self, value: Decimal, message: str) -> None:
        if not value.is_finite() or value <= 0:
            raise BusinessRuleError(message)

    def require_not_negative(self, value: Decimal, message: str) -> None:
        if not value.is_finite() or value < 0:
            raise BusinessRuleError(message)


class SquashCalendar:
    """Dias, horários e quadras de squash e contagem de aulas no mês."""

    def __init__(self) -> None:
        self.time_slots = (
            "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "15:45",
            "16:30", "17:15", "18:00", "18:45", "19:30", "20:15",
        )
        self.courts = (1, 2, 3)
        self.weekday_names = {
            1: "Segunda-feira",
            2: "Terça-feira",
            3: "Quarta-feira",
            4: "Quinta-feira",
            5: "Sexta-feira",
            6: "Sábado",
        }

    def is_valid_weekday(self, weekday: int) -> bool:
        return weekday in self.weekday_names

    def weekday_of(self, day: date) -> int:
        """1 = segunda-feira ... 7 = domingo (domingo não tem reservas)."""
        return day.isoweekday()

    def lessons_in_month(self, weekday: int, year: int, month: int) -> int:
        """Quantas vezes o dia da semana da aula ocorre no mês (corrige D08)."""
        days_in_month = calendar.monthrange(year, month)[1]
        return sum(
            1
            for day in range(1, days_in_month + 1)
            if date(year, month, day).isoweekday() == weekday
        )


@dataclass(frozen=True)
class Customer:
    code: int | None
    name: str
    cpf: str
    birthday: str
    phone: str

    def validate(self) -> None:
        if not self.name.strip():
            raise BusinessRuleError("O nome do cliente deve ser informado!")
        if len(self.name.strip()) > 50:
            raise BusinessRuleError("O nome do cliente deve ter no máximo 50 caracteres!")
        if len(self.cpf) > 11:
            raise BusinessRuleError("O CPF deve ter no máximo 11 caracteres!")
        if len(self.birthday) > 8:
            raise BusinessRuleError("A data de aniversário deve ter no máximo 8 caracteres!")
        if len(self.phone) > 15:
            raise BusinessRuleError("O telefone deve ter no máximo 15 caracteres!")


@dataclass(frozen=True)
class Product:
    code: int | None
    description: str
    price: Decimal
    unit: str

    def validate(self) -> None:
        if self.code is not None and InternalProducts().is_internal(self.code):
            raise BusinessRuleError("Os códigos 0 e 1 são de uso interno da aplicação!")
        if not self.description.strip():
            raise BusinessRuleError("A descrição do produto deve ser informada!")
        if len(self.description.strip()) > 100:
            raise BusinessRuleError("A descrição do produto deve ter no máximo 100 caracteres!")
        Money().require_positive(self.price, "O preço do produto deve ser maior que zero!")
        if not self.unit.strip():
            raise BusinessRuleError("A unidade do produto deve ser informada!")


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
        money = Money()
        money.require_positive(self.sauna_price, "O valor da sauna deve ser maior que zero!")
        money.require_positive(
            self.squash_lesson_price, "O valor da aula deve ser maior que zero!"
        )
        if not 1 <= len(self.due_tiers) <= 3:
            raise BusinessRuleError("O vencimento 1 e o valor mensal 1 devem ser informados!")
        seen_days: set[int] = set()
        for number, tier in enumerate(self.due_tiers, start=1):
            if tier.monthly_price is None or tier.day == 0:
                raise BusinessRuleError(
                    f"O vencimento {number} e o valor mensal {number} devem ser informados juntos!"
                )
            if not 1 <= tier.day <= 28:
                raise BusinessRuleError(
                    f"O vencimento {number} deve estar entre os dias 1 e 28!"
                )
            if tier.day in seen_days:
                raise BusinessRuleError("Os dias de vencimento devem ser diferentes!")
            seen_days.add(tier.day)
            money.require_positive(
                tier.monthly_price, f"O valor mensal {number} deve ser maior que zero!"
            )

    def tier(self, number: int) -> DueTier | None:
        """Faixa de vencimento 1, 2 ou 3; ``None`` se não configurada."""
        if number > len(self.due_tiers):
            return None
        return self.due_tiers[number - 1]


@dataclass(frozen=True)
class Reservation:
    weekday: int
    time: str
    court: int
    is_game: bool
    customer_ids: tuple[int, ...]

    def validate(self) -> None:
        squash = SquashCalendar()
        if not squash.is_valid_weekday(self.weekday):
            raise BusinessRuleError("O dia da reserva deve ser de segunda-feira a sábado!")
        if self.court not in squash.courts:
            raise BusinessRuleError("A quadra deve ser 1, 2 ou 3!")
        if self.time not in squash.time_slots:
            raise BusinessRuleError("O horário da reserva é inválido!")
        if not self.customer_ids:
            raise BusinessRuleError("A reserva deve ter ao menos um cliente!")
        if any(customer_id <= 0 for customer_id in self.customer_ids):
            raise BusinessRuleError("O cliente da reserva deve estar cadastrado!")
        if len(set(self.customer_ids)) != len(self.customer_ids):
            raise BusinessRuleError("Este cliente já foi incluído nesta reserva!")
        if not self.is_game and len(self.customer_ids) != 1:
            raise BusinessRuleError(
                "A reserva de uma quadra para aula deve ser feita para somente um cliente!"
            )

    def same_slot(self, other: Reservation) -> bool:
        return (
            self.weekday == other.weekday
            and self.time == other.time
            and self.court == other.court
        )


@dataclass(frozen=True)
class Consumption:
    customer_id: int
    date: date
    sequence: int
    product_code: int
    quantity: int
    unit_price: Decimal
    paid: bool

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
    closed: bool

    @property
    def total(self) -> Decimal:
        return sum((item.total for item in self.consumptions), Decimal("0"))


@dataclass(frozen=True)
class Fine:
    product_code: int
    amount_per_player: Decimal


class PaymentCalculator:
    """Cálculo do pagamento de cliente cadastrado (RN10 a RN12)."""

    def __init__(self, money: Money) -> None:
        self._money = money

    def calculate(
        self,
        *,
        total_due: Decimal,
        amount_paid: Decimal,
        discount: Decimal,
    ) -> PaymentResult:
        self._money.require_positive(amount_paid, "O valor a ser pago deve ser informado!")
        self._money.require_not_negative(discount, "O desconto não pode ser negativo!")
        difference = self._money.round(total_due - amount_paid - discount)
        return PaymentResult(
            paid_in_full=difference == 0,
            balance=difference,
            discount_entry=self._money.round(-discount) if discount > 0 else self._money.zero(),
        )


class SaunaRules:
    """Regras do frequentador avulso da sauna (RN14)."""

    def validate_name(self, name: str, existing_names: tuple[str, ...]) -> None:
        if not name.strip():
            raise BusinessRuleError("O nome do cliente deve ser informado!")
        if len(name.strip()) > 100:
            raise BusinessRuleError("O nome do cliente deve ter no máximo 100 caracteres!")
        if any(name.strip().casefold() == item.casefold() for item in existing_names):
            raise BusinessRuleError(
                "O nome do cliente deve ser diferente de outro cliente da sauna!"
            )
