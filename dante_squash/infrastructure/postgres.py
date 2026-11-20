"""PostgreSQL adapter for the legacy Dante Squash schema."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import os
from typing import Any, Callable, Iterator, Sequence

from dante_squash.domain import (
    Consumption,
    Customer,
    DueTier,
    PriceSchedule,
    Product,
    Reservation,
    SaunaAccount,
)


SCHEMA_STATEMENTS: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS produtos (
        codigo INTEGER PRIMARY KEY,
        descricao VARCHAR(100) NOT NULL,
        preco DOUBLE PRECISION NOT NULL,
        unidade VARCHAR(100) NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS clientes (
        codigo INTEGER PRIMARY KEY,
        cpf VARCHAR(11),
        nome VARCHAR(50) NOT NULL,
        dataaniversario VARCHAR(8),
        telefone VARCHAR(15)
    )""",
    """CREATE TABLE IF NOT EXISTS valores (
        codigo INTEGER PRIMARY KEY,
        valorsauna DOUBLE PRECISION NOT NULL,
        valoraulasquash DOUBLE PRECISION NOT NULL,
        vencimento1 INTEGER NOT NULL,
        valorsquashmensal1 DOUBLE PRECISION NOT NULL,
        vencimento2 INTEGER,
        valorsquashmensal2 DOUBLE PRECISION,
        vencimento3 INTEGER,
        valorsquashmensal3 DOUBLE PRECISION
    )""",
    """CREATE TABLE IF NOT EXISTS consumos (
        codigo_cliente INTEGER NOT NULL REFERENCES clientes(codigo),
        data INTEGER NOT NULL,
        sequencia INTEGER NOT NULL,
        codigo_produto INTEGER NOT NULL REFERENCES produtos(codigo),
        quantidade INTEGER NOT NULL,
        valor DOUBLE PRECISION NOT NULL,
        pago BOOLEAN NOT NULL,
        PRIMARY KEY (codigo_cliente, data, sequencia)
    )""",
    """CREATE TABLE IF NOT EXISTS pagamentos (
        codigo_cliente INTEGER NOT NULL REFERENCES clientes(codigo),
        data INTEGER NOT NULL,
        sequencia INTEGER NOT NULL,
        valor DOUBLE PRECISION NOT NULL,
        pagto_total BOOLEAN NOT NULL,
        PRIMARY KEY (codigo_cliente, data, sequencia)
    )""",
    """CREATE TABLE IF NOT EXISTS consumossauna (
        codigo_cliente INTEGER NOT NULL,
        data INTEGER NOT NULL,
        sequencia INTEGER NOT NULL,
        nome VARCHAR(100) NOT NULL,
        PRIMARY KEY (codigo_cliente, data, sequencia),
        FOREIGN KEY (codigo_cliente, data, sequencia)
            REFERENCES consumos(codigo_cliente, data, sequencia),
        FOREIGN KEY (codigo_cliente) REFERENCES clientes(codigo)
    )""",
    """CREATE TABLE IF NOT EXISTS horariossquash (
        dia INTEGER NOT NULL,
        horario VARCHAR(5) NOT NULL,
        quadra INTEGER NOT NULL,
        codigo_cliente INTEGER NOT NULL REFERENCES clientes(codigo),
        jogo BOOLEAN NOT NULL,
        PRIMARY KEY (dia, horario, quadra, codigo_cliente)
    )""",
    """CREATE TABLE IF NOT EXISTS mensalidades (
        codigo_cliente INTEGER NOT NULL,
        dia INTEGER NOT NULL,
        horario VARCHAR(5) NOT NULL,
        quadra INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        ano INTEGER NOT NULL,
        PRIMARY KEY (codigo_cliente, dia, horario, quadra, mes, ano)
    )""",
)


class PostgresDatabase:
    """Creates short-lived PostgreSQL connections and atomic transactions."""

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._connection_factory = connection_factory

    @classmethod
    def from_environment(cls) -> PostgresDatabase:
        dsn = os.environ.get("DANTE_SQUASH_DSN")
        if not dsn:
            raise RuntimeError("Defina a variável de ambiente DANTE_SQUASH_DSN.")
        try:
            import psycopg
        except ImportError as error:
            raise RuntimeError(
                "O driver PostgreSQL não está instalado. Execute: pip install -r requirements.txt"
            ) from error
        return cls(lambda: psycopg.connect(dsn))

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        with self._connection_factory() as connection:
            yield connection

    def initialize(self) -> None:
        with self.transaction() as connection:
            with connection.cursor() as cursor:
                for statement in SCHEMA_STATEMENTS:
                    cursor.execute(statement)
                cursor.execute(
                    """INSERT INTO produtos (codigo, descricao, preco, unidade)
                       VALUES (%s, %s, %s, %s) ON CONFLICT (codigo) DO NOTHING""",
                    (0, "Saldo de pagamento", 0, "un"),
                )
                for product in (
                    (1, "Sauna"),
                    (-1, "Mensalidade do Squash"),
                    (-2, "Primeira Multa por atraso do Squash"),
                    (-3, "Segunda Multa por atraso do Squash"),
                ):
                    cursor.execute(
                        """INSERT INTO produtos (codigo, descricao, preco, unidade)
                           VALUES (%s, %s, %s, %s) ON CONFLICT (codigo) DO NOTHING""",
                        (product[0], product[1], 0, "un"),
                    )
                cursor.execute(
                    """INSERT INTO clientes (codigo, cpf, nome, dataaniversario, telefone)
                       VALUES (%s, %s, %s, %s, %s) ON CONFLICT (codigo) DO NOTHING""",
                    (0, "0000", "Cliente Sauna", "0", "0"),
                )


@dataclass
class PostgresUnitOfWork:
    """Shares one connection among repositories for a single atomic use case."""

    database: PostgresDatabase

    def __enter__(self) -> PostgresUnitOfWork:
        self._transaction = self.database.transaction()
        self.connection = self._transaction.__enter__()
        self.customers = _CustomerRepository(self.connection)
        self.products = _ProductRepository(self.connection)
        self.prices = _PriceScheduleRepository(self.connection)
        self.reservations = _ReservationRepository(self.connection)
        self.consumptions = _ConsumptionRepository(self.connection)
        self.payments = _PaymentRepository(self.connection)
        self.sauna = _SaunaRepository(self.connection)
        self.monthly_billing = _MonthlyBillingRepository(self.connection)
        return self

    def __exit__(self, exception_type: object, exception: object, traceback: object) -> bool | None:
        return self._transaction.__exit__(exception_type, exception, traceback)


class _Repository:
    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def _all(self, statement: str, parameters: Sequence[object] = ()) -> list[tuple[Any, ...]]:
        with self._connection.cursor() as cursor:
            cursor.execute(statement, parameters)
            return list(cursor.fetchall())

    def _execute(self, statement: str, parameters: Sequence[object] = ()) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(statement, parameters)


def _date_to_legacy_integer(value: date) -> int:
    return int(value.strftime("%d%m%Y"))


def _date_from_legacy_integer(value: int) -> date:
    return datetime.strptime(str(value).zfill(8), "%d%m%Y").date()


def _legacy_month_year(value: int) -> tuple[int, int]:
    raw = str(value)
    return int(raw[2:4]) - 1, int(raw[4:8])


class _CustomerRepository(_Repository):
    def list_all(self) -> list[Customer]:
        rows = self._all(
            "SELECT codigo, nome, cpf, dataaniversario, telefone FROM clientes ORDER BY nome"
        )
        return [
            Customer(code=row[0], name=row[1], cpf=row[2] or "", birthday=row[3] or "", phone=row[4] or "")
            for row in rows
        ]

    def next_code(self) -> int:
        return int(self._all("SELECT COALESCE(MAX(codigo), 0) + 1 FROM clientes")[0][0])

    def save(self, customer: Customer) -> None:
        self._execute(
            """INSERT INTO clientes (codigo, cpf, nome, dataaniversario, telefone)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET cpf = EXCLUDED.cpf,
               nome = EXCLUDED.nome, dataaniversario = EXCLUDED.dataaniversario,
               telefone = EXCLUDED.telefone""",
            (customer.code, customer.cpf, customer.name, customer.birthday, customer.phone),
        )


class _ProductRepository(_Repository):
    def list_all(self) -> list[Product]:
        rows = self._all(
            "SELECT codigo, descricao, preco, unidade FROM produtos ORDER BY codigo"
        )
        return [
            Product(code=row[0], description=row[1], price=Decimal(str(row[2])), unit=row[3])
            for row in rows
        ]

    def next_code(self) -> int:
        return max(2, int(self._all("SELECT COALESCE(MAX(codigo), 1) + 1 FROM produtos")[0][0]))

    def save(self, product: Product) -> None:
        self._execute(
            """INSERT INTO produtos (codigo, descricao, preco, unidade)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET descricao = EXCLUDED.descricao,
               preco = EXCLUDED.preco, unidade = EXCLUDED.unidade""",
            (product.code, product.description, float(product.price), product.unit),
        )


class _PriceScheduleRepository(_Repository):
    def get(self) -> PriceSchedule | None:
        rows = self._all(
            """SELECT valorsauna, valoraulasquash, vencimento1, valorsquashmensal1,
                      vencimento2, valorsquashmensal2, vencimento3, valorsquashmensal3
               FROM valores WHERE codigo = 1"""
        )
        if not rows:
            return None
        row = rows[0]
        tiers = [DueTier(row[2], Decimal(str(row[3])))]
        if row[4] is not None or row[5] is not None:
            tiers.append(DueTier(row[4], Decimal(str(row[5])) if row[5] is not None else None))
        if row[6] is not None or row[7] is not None:
            tiers.append(DueTier(row[6], Decimal(str(row[7])) if row[7] is not None else None))
        return PriceSchedule(
            sauna_price=Decimal(str(row[0])),
            squash_lesson_price=Decimal(str(row[1])),
            due_tiers=tuple(tiers),
        )

    def save(self, schedule: PriceSchedule) -> None:
        schedule.validate()
        tiers = list(schedule.due_tiers) + [None, None]
        second, third = tiers[1], tiers[2]
        self._execute(
            """INSERT INTO valores (
                   codigo, valorsauna, valoraulasquash, vencimento1, valorsquashmensal1,
                   vencimento2, valorsquashmensal2, vencimento3, valorsquashmensal3
               ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET
                   valorsauna = EXCLUDED.valorsauna,
                   valoraulasquash = EXCLUDED.valoraulasquash,
                   vencimento1 = EXCLUDED.vencimento1,
                   valorsquashmensal1 = EXCLUDED.valorsquashmensal1,
                   vencimento2 = EXCLUDED.vencimento2,
                   valorsquashmensal2 = EXCLUDED.valorsquashmensal2,
                   vencimento3 = EXCLUDED.vencimento3,
                   valorsquashmensal3 = EXCLUDED.valorsquashmensal3""",
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


class _ReservationRepository(_Repository):
    def list_all(self) -> list[Reservation]:
        rows = self._all(
            """SELECT dia, horario, quadra, jogo, codigo_cliente FROM horariossquash
               ORDER BY dia, horario, quadra, codigo_cliente"""
        )
        grouped: dict[tuple[int, str, int, bool], list[int]] = {}
        for weekday, time, court, is_game, customer_id in rows:
            grouped.setdefault((weekday, time, court, is_game), []).append(customer_id)
        return [
            Reservation(day, time, court, is_game, tuple(customers))
            for (day, time, court, is_game), customers in grouped.items()
        ]

    def replace(self, reservation: Reservation) -> None:
        reservation.validate()
        self._execute(
            "DELETE FROM horariossquash WHERE dia = %s AND horario = %s AND quadra = %s",
            (reservation.weekday, reservation.time, reservation.court),
        )
        for customer_id in reservation.customer_ids:
            self._execute(
                """INSERT INTO horariossquash (dia, horario, quadra, codigo_cliente, jogo)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    reservation.weekday,
                    reservation.time,
                    reservation.court,
                    customer_id,
                    reservation.is_game,
                ),
            )


class _ConsumptionRepository(_Repository):
    def unpaid_for_customer(self, customer_id: int) -> list[Consumption]:
        rows = self._all(
            """SELECT codigo_cliente, data, sequencia, codigo_produto,
                      quantidade, valor, pago
               FROM consumos WHERE codigo_cliente = %s AND pago = FALSE
               ORDER BY data, sequencia""",
            (customer_id,),
        )
        return [
            Consumption(
                customer_id=row[0],
                date=_date_from_legacy_integer(row[1]),
                sequence=row[2],
                product_code=row[3],
                quantity=row[4],
                unit_price=Decimal(str(row[5])),
                paid=row[6],
            )
            for row in rows
        ]

    def next_sequence(self, customer_id: int, consumption_date: date) -> int:
        rows = self._all(
            """SELECT COALESCE(MAX(sequencia), 0) + 1 FROM consumos
               WHERE codigo_cliente = %s AND data = %s""",
            (customer_id, _date_to_legacy_integer(consumption_date)),
        )
        return int(rows[0][0])

    def insert(self, consumption: Consumption) -> None:
        self._execute(
            """INSERT INTO consumos
               (codigo_cliente, data, sequencia, codigo_produto, quantidade, valor, pago)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                consumption.customer_id,
                _date_to_legacy_integer(consumption.date),
                consumption.sequence,
                consumption.product_code,
                consumption.quantity,
                float(consumption.unit_price),
                consumption.paid,
            ),
        )

    def mark_unpaid_as_paid(self, customer_id: int) -> None:
        self._execute(
            "UPDATE consumos SET pago = TRUE WHERE codigo_cliente = %s AND pago = FALSE",
            (customer_id,),
        )


class _PaymentRepository(_Repository):
    def record(
        self,
        customer_id: int,
        payment_date: date,
        amount: Decimal,
        paid_in_full: bool,
    ) -> None:
        legacy_date = _date_to_legacy_integer(payment_date)
        rows = self._all(
            """SELECT COALESCE(MAX(sequencia), 0) + 1 FROM pagamentos
               WHERE codigo_cliente = %s AND data = %s""",
            (customer_id, legacy_date),
        )
        self._execute(
            """INSERT INTO pagamentos
               (codigo_cliente, data, sequencia, valor, pagto_total)
               VALUES (%s, %s, %s, %s, %s)""",
            (customer_id, legacy_date, int(rows[0][0]), float(amount), paid_in_full),
        )


class _SaunaRepository(_Repository):
    def accounts_for_date(self, account_date: date) -> list[SaunaAccount]:
        rows = self._all(
            """SELECT cs.nome, c.codigo_cliente, c.data, c.sequencia,
                      c.codigo_produto, c.quantidade, c.valor, c.pago
               FROM consumossauna cs
               JOIN consumos c ON c.codigo_cliente = cs.codigo_cliente
                   AND c.data = cs.data AND c.sequencia = cs.sequencia
               WHERE cs.data = %s
               ORDER BY cs.nome, c.sequencia""",
            (_date_to_legacy_integer(account_date),),
        )
        grouped: dict[str, list[Consumption]] = {}
        closed: dict[str, bool] = {}
        for name, customer_id, legacy_date, sequence, product_code, quantity, price, paid in rows:
            grouped.setdefault(name, []).append(
                Consumption(
                    customer_id=customer_id,
                    date=_date_from_legacy_integer(legacy_date),
                    sequence=sequence,
                    product_code=product_code,
                    quantity=quantity,
                    unit_price=Decimal(str(price)),
                    paid=paid,
                )
            )
            closed[name] = closed.get(name, True) and paid
        return [
            SaunaAccount(name, account_date, tuple(items), closed[name])
            for name, items in grouped.items()
        ]

    def create_account(self, account: SaunaAccount, entrance_price: Decimal) -> None:
        consumption = Consumption(
            customer_id=0,
            date=account.date,
            sequence=self._next_sequence(account.date),
            product_code=1,
            quantity=1,
            unit_price=entrance_price,
        )
        self._insert_sauna_consumption(account.name, consumption)

    def add_consumption(
        self,
        account_name: str,
        account_date: date,
        consumption: Consumption,
    ) -> None:
        self._insert_sauna_consumption(account_name, consumption)

    def close_account(self, account_name: str, account_date: date, amount_paid: Decimal) -> None:
        legacy_date = _date_to_legacy_integer(account_date)
        keys = self._all(
            """SELECT codigo_cliente, data, sequencia FROM consumossauna
               WHERE LOWER(nome) = LOWER(%s) AND data = %s ORDER BY sequencia""",
            (account_name, legacy_date),
        )
        if not keys:
            raise LookupError("Frequentador da sauna não encontrado.")
        initial = keys[0]
        rows = self._all(
            """SELECT COALESCE(SUM(c.valor * c.quantidade), 0)
               FROM consumos c JOIN consumossauna cs
                 ON cs.codigo_cliente = c.codigo_cliente
                AND cs.data = c.data AND cs.sequencia = c.sequencia
               WHERE LOWER(cs.nome) = LOWER(%s) AND cs.data = %s""",
            (account_name, legacy_date),
        )
        difference = amount_paid - Decimal(str(rows[0][0]))
        self._execute(
            """UPDATE consumos SET pago = TRUE
               WHERE (codigo_cliente, data, sequencia) IN (
                   SELECT codigo_cliente, data, sequencia FROM consumossauna
                   WHERE LOWER(nome) = LOWER(%s) AND data = %s
               )""",
            (account_name, legacy_date),
        )
        if difference:
            self._execute(
                """UPDATE consumos SET valor = valor + %s
                   WHERE codigo_cliente = %s AND data = %s AND sequencia = %s""",
                (float(difference), initial[0], initial[1], initial[2]),
            )

    def _next_sequence(self, account_date: date) -> int:
        rows = self._all(
            """SELECT COALESCE(MAX(sequencia), 0) + 1 FROM consumos
               WHERE codigo_cliente = 0 AND data = %s""",
            (_date_to_legacy_integer(account_date),),
        )
        return int(rows[0][0])

    def _insert_sauna_consumption(self, name: str, consumption: Consumption) -> None:
        _ConsumptionRepository(self._connection).insert(consumption)
        self._execute(
            """INSERT INTO consumossauna (codigo_cliente, data, sequencia, nome)
               VALUES (%s, %s, %s, %s)""",
            (
                consumption.customer_id,
                _date_to_legacy_integer(consumption.date),
                consumption.sequence,
                name,
            ),
        )


class _MonthlyBillingRepository(_Repository):
    def has_record(
        self,
        customer_id: int,
        reservation: Reservation,
        month: int,
        year: int,
    ) -> bool:
        rows = self._all(
            """SELECT 1 FROM mensalidades
               WHERE codigo_cliente = %s AND dia = %s AND horario = %s
                 AND quadra = %s AND mes = %s AND ano = %s""",
            (
                customer_id,
                reservation.weekday,
                reservation.time,
                reservation.court,
                month,
                year,
            ),
        )
        return bool(rows)

    def record(
        self,
        customer_id: int,
        reservation: Reservation,
        month: int,
        year: int,
    ) -> None:
        self._execute(
            """INSERT INTO mensalidades
               (codigo_cliente, dia, horario, quadra, mes, ano)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT DO NOTHING""",
            (
                customer_id,
                reservation.weekday,
                reservation.time,
                reservation.court,
                month,
                year,
            ),
        )

    def has_fine_for_month(self, product_code: int, month: int, year: int) -> bool:
        rows = self._all(
            "SELECT data FROM consumos WHERE codigo_produto = %s ORDER BY data DESC",
            (product_code,),
        )
        return any(_legacy_month_year(row[0]) == (month, year) for row in rows)

    def monthly_paid(self, customer_id: int, month: int, year: int) -> bool:
        rows = self._all(
            """SELECT data FROM consumos
               WHERE codigo_cliente = %s AND codigo_produto = -1 AND pago = TRUE
               ORDER BY data DESC""",
            (customer_id,),
        )
        return any(_legacy_month_year(row[0]) == (month, year) for row in rows)
