"""MariaDB adapter for the legacy Dante Squash schema."""

from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Any, Callable, Iterator
from urllib.parse import unquote, urlparse

from dante_squash.domain import Customer, PriceSchedule, Product, Reservation
from dante_squash.infrastructure.postgres import (
    SCHEMA_STATEMENTS,
    _ConsumptionRepository,
    _CustomerRepository,
    _MonthlyBillingRepository,
    _PaymentRepository,
    _PriceScheduleRepository,
    _ProductRepository,
    _ReservationRepository,
    _SaunaRepository,
)


_MYSQL_SCHEMA_STATEMENTS = tuple(
    statement.replace("DOUBLE PRECISION", "DOUBLE") + " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    for statement in SCHEMA_STATEMENTS
)


class MariaDBDatabase:
    """Creates transactional MariaDB connections from a private environment DSN."""

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._connection_factory = connection_factory

    @classmethod
    def from_environment(cls) -> MariaDBDatabase:
        dsn = os.environ.get("DANTE_SQUASH_MARIADB_DSN")
        if not dsn:
            raise RuntimeError("Defina DANTE_SQUASH_MARIADB_DSN para o banco MariaDB.")
        parsed = urlparse(dsn)
        if parsed.scheme not in {"mysql", "mariadb"} or not parsed.hostname or not parsed.path:
            raise RuntimeError(
                "DANTE_SQUASH_MARIADB_DSN deve ter o formato "
                "mysql://usuario:senha@host:3306/banco."
            )
        try:
            import pymysql
        except ImportError as error:
            raise RuntimeError(
                "O driver MariaDB não está instalado. Execute: pip install -r requirements.txt"
            ) from error
        return cls(
            lambda: pymysql.connect(
                host=parsed.hostname,
                port=parsed.port or 3306,
                user=unquote(parsed.username or ""),
                password=unquote(parsed.password or ""),
                database=unquote(parsed.path.lstrip("/")),
                charset="utf8mb4",
                autocommit=False,
            )
        )

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        connection = self._connection_factory()
        try:
            yield connection
        except BaseException:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.transaction() as connection:
            with connection.cursor() as cursor:
                for statement in _MYSQL_SCHEMA_STATEMENTS:
                    cursor.execute(statement)
                cursor.execute(
                    """INSERT IGNORE INTO produtos
                       (codigo, descricao, preco, unidade) VALUES (%s, %s, %s, %s)""",
                    (0, "Saldo de pagamento", 0, "un"),
                )
                for code, description in (
                    (1, "Sauna"),
                    (-1, "Mensalidade do Squash"),
                    (-2, "Primeira Multa por atraso do Squash"),
                    (-3, "Segunda Multa por atraso do Squash"),
                ):
                    cursor.execute(
                        """INSERT IGNORE INTO produtos
                           (codigo, descricao, preco, unidade) VALUES (%s, %s, %s, %s)""",
                        (code, description, 0, "un"),
                    )
                cursor.execute(
                    """INSERT IGNORE INTO clientes
                       (codigo, cpf, nome, dataaniversario, telefone)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (0, "0000", "Cliente Sauna", "0", "0"),
                )


class MariaDBUnitOfWork:
    """Shares one MariaDB transaction across all repositories in a use case."""

    def __init__(self, database: MariaDBDatabase) -> None:
        self._database = database

    def __enter__(self) -> MariaDBUnitOfWork:
        self._transaction = self._database.transaction()
        self.connection = self._transaction.__enter__()
        self.customers = _MariaDBCustomerRepository(self.connection)
        self.products = _MariaDBProductRepository(self.connection)
        self.prices = _MariaDBPriceScheduleRepository(self.connection)
        self.reservations = _ReservationRepository(self.connection)
        self.consumptions = _ConsumptionRepository(self.connection)
        self.payments = _PaymentRepository(self.connection)
        self.sauna = _SaunaRepository(self.connection)
        self.monthly_billing = _MariaDBMonthlyBillingRepository(self.connection)
        return self

    def __exit__(self, exception_type: object, exception: object, traceback: object) -> bool | None:
        return self._transaction.__exit__(exception_type, exception, traceback)


class _MariaDBCustomerRepository(_CustomerRepository):
    def save(self, customer: Customer) -> None:
        self._execute(
            """INSERT INTO clientes (codigo, cpf, nome, dataaniversario, telefone)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE cpf = VALUES(cpf), nome = VALUES(nome),
               dataaniversario = VALUES(dataaniversario), telefone = VALUES(telefone)""",
            (customer.code, customer.cpf, customer.name, customer.birthday, customer.phone),
        )


class _MariaDBProductRepository(_ProductRepository):
    def save(self, product: Product) -> None:
        self._execute(
            """INSERT INTO produtos (codigo, descricao, preco, unidade)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE descricao = VALUES(descricao),
               preco = VALUES(preco), unidade = VALUES(unidade)""",
            (product.code, product.description, float(product.price), product.unit),
        )


class _MariaDBPriceScheduleRepository(_PriceScheduleRepository):
    def save(self, schedule: PriceSchedule) -> None:
        schedule.validate()
        tiers = list(schedule.due_tiers) + [None, None]
        second, third = tiers[1], tiers[2]
        self._execute(
            """INSERT INTO valores (
                   codigo, valorsauna, valoraulasquash, vencimento1, valorsquashmensal1,
                   vencimento2, valorsquashmensal2, vencimento3, valorsquashmensal3
               ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE valorsauna = VALUES(valorsauna),
               valoraulasquash = VALUES(valoraulasquash),
               vencimento1 = VALUES(vencimento1),
               valorsquashmensal1 = VALUES(valorsquashmensal1),
               vencimento2 = VALUES(vencimento2),
               valorsquashmensal2 = VALUES(valorsquashmensal2),
               vencimento3 = VALUES(vencimento3),
               valorsquashmensal3 = VALUES(valorsquashmensal3)""",
            (
                1,
                float(schedule.sauna_price),
                float(schedule.squash_lesson_price),
                schedule.due_tiers[0].day,
                float(schedule.due_tiers[0].monthly_price),
                second.day if second else None,
                float(second.monthly_price) if second and second.monthly_price is not None else None,
                third.day if third else None,
                float(third.monthly_price) if third and third.monthly_price is not None else None,
            ),
        )


class _MariaDBMonthlyBillingRepository(_MonthlyBillingRepository):
    def record(
        self,
        customer_id: int,
        reservation: Reservation,
        month: int,
        year: int,
    ) -> None:
        self._execute(
            """INSERT IGNORE INTO mensalidades
               (codigo_cliente, dia, horario, quadra, mes, ano)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                customer_id,
                reservation.weekday,
                reservation.time,
                reservation.court,
                month,
                year,
            ),
        )
