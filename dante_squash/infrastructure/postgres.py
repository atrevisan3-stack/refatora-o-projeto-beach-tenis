"""Adaptador PostgreSQL: esquema, repositórios e unidade de trabalho.

Melhorias sobre o legado: datas em ``DATE`` (corrige D02 e a ordenação por
data), dinheiro em ``NUMERIC(10,2)`` (corrige D04), SQL sempre parametrizado
e uma transação por caso de uso.
"""

from __future__ import annotations

import csv
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from dante_squash.domain import (
    Consumption,
    Customer,
    DueTier,
    PriceSchedule,
    Product,
    Reservation,
    SaunaAccount,
)


class PostgresSchema:
    """DDL das oito tabelas e carga padrão (RF17, RN29)."""

    def __init__(self) -> None:
        self._tables = (
            ("clientes", """CREATE TABLE IF NOT EXISTS clientes (
                codigo INTEGER PRIMARY KEY,
                cpf VARCHAR(11) NOT NULL DEFAULT '',
                nome VARCHAR(50) NOT NULL,
                dataaniversario VARCHAR(8) NOT NULL DEFAULT '',
                telefone VARCHAR(15) NOT NULL DEFAULT ''
            )"""),
            ("produtos", """CREATE TABLE IF NOT EXISTS produtos (
                codigo INTEGER PRIMARY KEY,
                descricao VARCHAR(100) NOT NULL,
                preco NUMERIC(10, 2) NOT NULL,
                unidade VARCHAR(100) NOT NULL
            )"""),
            ("valores", """CREATE TABLE IF NOT EXISTS valores (
                codigo INTEGER PRIMARY KEY CHECK (codigo = 1),
                valorsauna NUMERIC(10, 2) NOT NULL,
                valoraulasquash NUMERIC(10, 2) NOT NULL,
                vencimento1 INTEGER NOT NULL,
                valorsquashmensal1 NUMERIC(10, 2) NOT NULL,
                vencimento2 INTEGER,
                valorsquashmensal2 NUMERIC(10, 2),
                vencimento3 INTEGER,
                valorsquashmensal3 NUMERIC(10, 2)
            )"""),
            ("consumos", """CREATE TABLE IF NOT EXISTS consumos (
                codigo_cliente INTEGER NOT NULL REFERENCES clientes(codigo),
                data DATE NOT NULL,
                sequencia INTEGER NOT NULL,
                codigo_produto INTEGER NOT NULL REFERENCES produtos(codigo),
                quantidade INTEGER NOT NULL CHECK (quantidade > 0),
                valor NUMERIC(10, 2) NOT NULL,
                pago BOOLEAN NOT NULL,
                PRIMARY KEY (codigo_cliente, data, sequencia)
            )"""),
            ("consumossauna", """CREATE TABLE IF NOT EXISTS consumossauna (
                codigo_cliente INTEGER NOT NULL REFERENCES clientes(codigo),
                data DATE NOT NULL,
                sequencia INTEGER NOT NULL,
                nome VARCHAR(100) NOT NULL,
                PRIMARY KEY (codigo_cliente, data, sequencia),
                FOREIGN KEY (codigo_cliente, data, sequencia)
                    REFERENCES consumos(codigo_cliente, data, sequencia)
            )"""),
            ("pagamentos", """CREATE TABLE IF NOT EXISTS pagamentos (
                codigo_cliente INTEGER NOT NULL REFERENCES clientes(codigo),
                data DATE NOT NULL,
                sequencia INTEGER NOT NULL,
                valor NUMERIC(10, 2) NOT NULL CHECK (valor > 0),
                pagto_total BOOLEAN NOT NULL,
                PRIMARY KEY (codigo_cliente, data, sequencia)
            )"""),
            ("horariossquash", """CREATE TABLE IF NOT EXISTS horariossquash (
                dia INTEGER NOT NULL CHECK (dia BETWEEN 1 AND 6),
                horario VARCHAR(5) NOT NULL,
                quadra INTEGER NOT NULL CHECK (quadra BETWEEN 1 AND 3),
                codigo_cliente INTEGER NOT NULL REFERENCES clientes(codigo),
                jogo BOOLEAN NOT NULL,
                PRIMARY KEY (dia, horario, quadra, codigo_cliente)
            )"""),
            ("mensalidades", """CREATE TABLE IF NOT EXISTS mensalidades (
                codigo_cliente INTEGER NOT NULL REFERENCES clientes(codigo),
                dia INTEGER NOT NULL,
                horario VARCHAR(5) NOT NULL,
                quadra INTEGER NOT NULL,
                mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
                ano INTEGER NOT NULL,
                PRIMARY KEY (codigo_cliente, dia, horario, quadra, mes, ano)
            )"""),
        )
        self._default_products = (
            (0, "Saldo de pagamento"),
            (1, "Sauna"),
            (-1, "Mensalidade do Squash"),
            (-2, "Primeira Multa por atraso do Squash"),
            (-3, "Segunda Multa por atraso do Squash"),
        )

    def table_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self._tables)

    def create_statements(self) -> tuple[str, ...]:
        return tuple(statement for _, statement in self._tables)

    def default_products(self) -> tuple[tuple[int, str], ...]:
        return self._default_products


class EnvironmentSettings:
    """Lê a string de conexão do ambiente; credenciais nunca ficam no código."""

    def __init__(self, environment: Mapping[str, str]) -> None:
        self._environment = environment

    def dsn(self) -> str:
        dsn = self._environment.get("DANTE_SQUASH_DSN", "").strip()
        if not dsn:
            raise RuntimeError(
                "Defina a variável de ambiente DANTE_SQUASH_DSN "
                "(ex.: postgresql://usuario:senha@localhost:5432/dante_squash)."
            )
        return dsn


class PsycopgConnector:
    """Abre conexões psycopg; a conexão faz commit ao sair sem erro e rollback com erro."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def connect(self) -> Any:
        try:
            import psycopg
        except ImportError as error:
            raise RuntimeError(
                "O driver PostgreSQL não está instalado. Execute: pip install -r requirements.txt"
            ) from error
        return psycopg.connect(self._dsn)


class PostgresDatabase:
    def __init__(self, connector: Any, schema: PostgresSchema) -> None:
        self._connector = connector
        self.schema = schema

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        with self._connector.connect() as connection:
            yield connection

    def initialize(self) -> None:
        """Cria as tabelas ausentes e a carga padrão, sem alterar dados existentes."""
        with self.transaction() as connection:
            with connection.cursor() as cursor:
                for statement in self.schema.create_statements():
                    cursor.execute(statement)
                for code, description in self.schema.default_products():
                    cursor.execute(
                        """INSERT INTO produtos (codigo, descricao, preco, unidade)
                           VALUES (%s, %s, %s, %s) ON CONFLICT (codigo) DO NOTHING""",
                        (code, description, Decimal("0"), "un"),
                    )
                cursor.execute(
                    """INSERT INTO clientes (codigo, cpf, nome, dataaniversario, telefone)
                       VALUES (%s, %s, %s, %s, %s) ON CONFLICT (codigo) DO NOTHING""",
                    (0, "", "Cliente Sauna", "", ""),
                )

    def drop_all(self) -> None:
        """Exclui todas as tabelas (usado pelos testes de banco)."""
        with self.transaction() as connection:
            with connection.cursor() as cursor:
                for name in reversed(self.schema.table_names()):
                    cursor.execute(f"DROP TABLE IF EXISTS {name} CASCADE")


class PostgresUnitOfWork:
    """Compartilha uma conexão entre os repositórios de um caso de uso."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def __enter__(self) -> PostgresUnitOfWork:
        self._transaction = self._database.transaction()
        connection = self._transaction.__enter__()
        self.customers = PostgresCustomerRepository(connection)
        self.products = PostgresProductRepository(connection)
        self.prices = PostgresPriceScheduleRepository(connection)
        self.reservations = PostgresReservationRepository(connection)
        self.consumptions = PostgresConsumptionRepository(connection)
        self.payments = PostgresPaymentRepository(connection)
        self.sauna = PostgresSaunaRepository(connection, self.consumptions)
        self.monthly_billing = PostgresMonthlyBillingRepository(connection)
        return self

    def __exit__(self, exception_type: object, exception: object, traceback: object) -> bool | None:
        return self._transaction.__exit__(exception_type, exception, traceback)


class PostgresUnitOfWorkFactory:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def __call__(self) -> PostgresUnitOfWork:
        return PostgresUnitOfWork(self._database)


class PostgresRepository:
    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def _all(self, statement: str, parameters: Sequence[object] = ()) -> list[tuple[Any, ...]]:
        with self._connection.cursor() as cursor:
            cursor.execute(statement, parameters)
            return list(cursor.fetchall())

    def _one_value(self, statement: str, parameters: Sequence[object] = ()) -> Any:
        return self._all(statement, parameters)[0][0]

    def _execute(self, statement: str, parameters: Sequence[object] = ()) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(statement, parameters)


class PostgresCustomerRepository(PostgresRepository):
    def _customer(self, row: tuple[Any, ...]) -> Customer:
        return Customer(code=row[0], name=row[1], cpf=row[2], birthday=row[3], phone=row[4])

    def list_all(self) -> list[Customer]:
        rows = self._all(
            "SELECT codigo, nome, cpf, dataaniversario, telefone FROM clientes ORDER BY nome"
        )
        return [self._customer(row) for row in rows]

    def get(self, code: int) -> Customer | None:
        rows = self._all(
            "SELECT codigo, nome, cpf, dataaniversario, telefone FROM clientes WHERE codigo = %s",
            (code,),
        )
        return self._customer(rows[0]) if rows else None

    def next_code(self) -> int:
        return int(self._one_value("SELECT COALESCE(MAX(codigo), 0) + 1 AS proximo FROM clientes"))

    def save(self, customer: Customer) -> None:
        self._execute(
            """INSERT INTO clientes (codigo, cpf, nome, dataaniversario, telefone)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET cpf = EXCLUDED.cpf,
               nome = EXCLUDED.nome, dataaniversario = EXCLUDED.dataaniversario,
               telefone = EXCLUDED.telefone""",
            (customer.code, customer.cpf, customer.name, customer.birthday, customer.phone),
        )

    def has_dependencies(self, code: int) -> bool:
        """Consumos, consumos de sauna, pagamentos, reservas ou mensalidades (RN02, D05 antigo)."""
        return bool(
            self._one_value(
                """SELECT EXISTS (SELECT 1 FROM consumos WHERE codigo_cliente = %s)
                       OR EXISTS (SELECT 1 FROM consumossauna WHERE codigo_cliente = %s)
                       OR EXISTS (SELECT 1 FROM pagamentos WHERE codigo_cliente = %s)
                       OR EXISTS (SELECT 1 FROM horariossquash WHERE codigo_cliente = %s)
                       OR EXISTS (SELECT 1 FROM mensalidades WHERE codigo_cliente = %s)
                   AS vinculado""",
                (code, code, code, code, code),
            )
        )

    def delete(self, code: int) -> None:
        self._execute("DELETE FROM clientes WHERE codigo = %s", (code,))


class PostgresProductRepository(PostgresRepository):
    def _product(self, row: tuple[Any, ...]) -> Product:
        return Product(code=row[0], description=row[1], price=Decimal(row[2]), unit=row[3])

    def list_all(self) -> list[Product]:
        rows = self._all("SELECT codigo, descricao, preco, unidade FROM produtos ORDER BY codigo")
        return [self._product(row) for row in rows]

    def get(self, code: int) -> Product | None:
        rows = self._all(
            "SELECT codigo, descricao, preco, unidade FROM produtos WHERE codigo = %s", (code,)
        )
        return self._product(rows[0]) if rows else None

    def next_code(self) -> int:
        return int(
            self._one_value("SELECT GREATEST(COALESCE(MAX(codigo), 1) + 1, 2) AS proximo FROM produtos")
        )

    def save(self, product: Product) -> None:
        self._execute(
            """INSERT INTO produtos (codigo, descricao, preco, unidade)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (codigo) DO UPDATE SET descricao = EXCLUDED.descricao,
               preco = EXCLUDED.preco, unidade = EXCLUDED.unidade""",
            (product.code, product.description, product.price, product.unit),
        )

    def is_used(self, code: int) -> bool:
        return bool(
            self._one_value(
                "SELECT EXISTS (SELECT 1 FROM consumos WHERE codigo_produto = %s) AS usado",
                (code,),
            )
        )

    def delete(self, code: int) -> None:
        self._execute("DELETE FROM produtos WHERE codigo = %s", (code,))


class PostgresPriceScheduleRepository(PostgresRepository):
    def get(self) -> PriceSchedule | None:
        rows = self._all(
            """SELECT valorsauna, valoraulasquash, vencimento1, valorsquashmensal1,
                      vencimento2, valorsquashmensal2, vencimento3, valorsquashmensal3
               FROM valores WHERE codigo = 1"""
        )
        if not rows:
            return None
        row = rows[0]
        tiers = [DueTier(row[2], Decimal(row[3]))]
        for day, price in ((row[4], row[5]), (row[6], row[7])):
            if day is not None:
                tiers.append(DueTier(day, Decimal(price)))
        return PriceSchedule(Decimal(row[0]), Decimal(row[1]), tuple(tiers))

    def save(self, schedule: PriceSchedule) -> None:
        tiers: list[DueTier | None] = list(schedule.due_tiers) + [None, None]
        second, third = tiers[1], tiers[2]
        self._execute(
            """INSERT INTO valores (
                   codigo, valorsauna, valoraulasquash, vencimento1, valorsquashmensal1,
                   vencimento2, valorsquashmensal2, vencimento3, valorsquashmensal3
               ) VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s)
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
                schedule.sauna_price,
                schedule.squash_lesson_price,
                schedule.due_tiers[0].day,
                schedule.due_tiers[0].monthly_price,
                second.day if second else None,
                second.monthly_price if second else None,
                third.day if third else None,
                third.monthly_price if third else None,
            ),
        )


class PostgresReservationRepository(PostgresRepository):
    def list_all(self) -> list[Reservation]:
        rows = self._all(
            """SELECT dia, horario, quadra, jogo, codigo_cliente FROM horariossquash
               ORDER BY dia, horario, quadra, codigo_cliente"""
        )
        grouped: dict[tuple[int, str, int, bool], list[int]] = {}
        for weekday, time, court, is_game, customer_id in rows:
            grouped.setdefault((weekday, time, court, is_game), []).append(customer_id)
        return [
            Reservation(weekday, time, court, is_game, tuple(customers))
            for (weekday, time, court, is_game), customers in grouped.items()
        ]

    def replace(self, reservation: Reservation) -> None:
        self.delete(reservation.weekday, reservation.time, reservation.court)
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

    def delete(self, weekday: int, time: str, court: int) -> None:
        self._execute(
            "DELETE FROM horariossquash WHERE dia = %s AND horario = %s AND quadra = %s",
            (weekday, time, court),
        )


class PostgresConsumptionRepository(PostgresRepository):
    def __init__(self, connection: Any) -> None:
        super().__init__(connection)
        self._columns = (
            "codigo_cliente, data, sequencia, codigo_produto, quantidade, valor, pago"
        )

    def _consumption(self, row: tuple[Any, ...]) -> Consumption:
        return Consumption(
            customer_id=row[0],
            date=row[1],
            sequence=row[2],
            product_code=row[3],
            quantity=row[4],
            unit_price=Decimal(row[5]),
            paid=row[6],
        )

    def for_customer(self, customer_id: int) -> list[Consumption]:
        rows = self._all(
            f"""SELECT {self._columns} FROM consumos WHERE codigo_cliente = %s
                ORDER BY data, sequencia""",
            (customer_id,),
        )
        return [self._consumption(row) for row in rows]

    def unpaid_for_customer(self, customer_id: int) -> list[Consumption]:
        rows = self._all(
            f"""SELECT {self._columns} FROM consumos
                WHERE codigo_cliente = %s AND pago = FALSE ORDER BY data, sequencia""",
            (customer_id,),
        )
        return [self._consumption(row) for row in rows]

    def between(self, start: date, end: date) -> list[Consumption]:
        rows = self._all(
            f"""SELECT {self._columns} FROM consumos WHERE data BETWEEN %s AND %s
                ORDER BY data, codigo_cliente, sequencia""",
            (start, end),
        )
        return [self._consumption(row) for row in rows]

    def get(self, customer_id: int, consumption_date: date, sequence: int) -> Consumption | None:
        rows = self._all(
            f"""SELECT {self._columns} FROM consumos
                WHERE codigo_cliente = %s AND data = %s AND sequencia = %s""",
            (customer_id, consumption_date, sequence),
        )
        return self._consumption(rows[0]) if rows else None

    def next_sequence(self, customer_id: int, consumption_date: date) -> int:
        return int(
            self._one_value(
                """SELECT COALESCE(MAX(sequencia), 0) + 1 AS proxima FROM consumos
                   WHERE codigo_cliente = %s AND data = %s""",
                (customer_id, consumption_date),
            )
        )

    def insert(self, consumption: Consumption) -> None:
        self._execute(
            f"""INSERT INTO consumos ({self._columns})
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                consumption.customer_id,
                consumption.date,
                consumption.sequence,
                consumption.product_code,
                consumption.quantity,
                consumption.unit_price,
                consumption.paid,
            ),
        )

    def delete(self, customer_id: int, consumption_date: date, sequence: int) -> None:
        self._execute(
            "DELETE FROM consumos WHERE codigo_cliente = %s AND data = %s AND sequencia = %s",
            (customer_id, consumption_date, sequence),
        )

    def mark_unpaid_as_paid(self, customer_id: int) -> None:
        self._execute(
            "UPDATE consumos SET pago = TRUE WHERE codigo_cliente = %s AND pago = FALSE",
            (customer_id,),
        )


class PostgresPaymentRepository(PostgresRepository):
    def record(
        self, customer_id: int, payment_date: date, amount: Decimal, paid_in_full: bool
    ) -> None:
        sequence = self._one_value(
            """SELECT COALESCE(MAX(sequencia), 0) + 1 AS proxima FROM pagamentos
               WHERE codigo_cliente = %s AND data = %s""",
            (customer_id, payment_date),
        )
        self._execute(
            """INSERT INTO pagamentos (codigo_cliente, data, sequencia, valor, pagto_total)
               VALUES (%s, %s, %s, %s, %s)""",
            (customer_id, payment_date, int(sequence), amount, paid_in_full),
        )


class PostgresSaunaRepository(PostgresRepository):
    def __init__(self, connection: Any, consumptions: PostgresConsumptionRepository) -> None:
        super().__init__(connection)
        self._consumptions = consumptions

    def accounts_for_date(self, account_date: date) -> list[SaunaAccount]:
        rows = self._all(
            """SELECT cs.nome, c.codigo_cliente, c.data, c.sequencia,
                      c.codigo_produto, c.quantidade, c.valor, c.pago
               FROM consumossauna cs
               JOIN consumos c ON c.codigo_cliente = cs.codigo_cliente
                AND c.data = cs.data AND c.sequencia = cs.sequencia
               WHERE cs.data = %s
               ORDER BY cs.nome, c.sequencia""",
            (account_date,),
        )
        grouped: dict[str, list[Consumption]] = {}
        for row in rows:
            grouped.setdefault(row[0], []).append(
                Consumption(
                    customer_id=row[1],
                    date=row[2],
                    sequence=row[3],
                    product_code=row[4],
                    quantity=row[5],
                    unit_price=Decimal(row[6]),
                    paid=row[7],
                )
            )
        return [
            SaunaAccount(name, account_date, tuple(items), all(item.paid for item in items))
            for name, items in grouped.items()
        ]

    def add_consumption(self, account_name: str, consumption: Consumption) -> None:
        self._consumptions.insert(consumption)
        self._execute(
            """INSERT INTO consumossauna (codigo_cliente, data, sequencia, nome)
               VALUES (%s, %s, %s, %s)""",
            (consumption.customer_id, consumption.date, consumption.sequence, account_name),
        )

    def remove_consumption(self, account_date: date, sequence: int) -> None:
        self._execute(
            """DELETE FROM consumossauna
               WHERE codigo_cliente = 0 AND data = %s AND sequencia = %s""",
            (account_date, sequence),
        )
        self._consumptions.delete(0, account_date, sequence)

    def close_account(self, account: SaunaAccount, entrance_adjustment: Decimal) -> None:
        for item in account.consumptions:
            self._execute(
                """UPDATE consumos SET pago = TRUE
                   WHERE codigo_cliente = %s AND data = %s AND sequencia = %s""",
                (item.customer_id, item.date, item.sequence),
            )
        if entrance_adjustment:
            entrance = account.consumptions[0]
            self._execute(
                """UPDATE consumos SET valor = valor + %s
                   WHERE codigo_cliente = %s AND data = %s AND sequencia = %s""",
                (entrance_adjustment, entrance.customer_id, entrance.date, entrance.sequence),
            )


class PostgresMonthlyBillingRepository(PostgresRepository):
    def has_record(self, customer_id: int, reservation: Reservation, month: int, year: int) -> bool:
        return bool(
            self._one_value(
                """SELECT EXISTS (SELECT 1 FROM mensalidades
                   WHERE codigo_cliente = %s AND dia = %s AND horario = %s
                     AND quadra = %s AND mes = %s AND ano = %s) AS gerada""",
                (customer_id, reservation.weekday, reservation.time, reservation.court, month, year),
            )
        )

    def record(self, customer_id: int, reservation: Reservation, month: int, year: int) -> None:
        self._execute(
            """INSERT INTO mensalidades (codigo_cliente, dia, horario, quadra, mes, ano)
               VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
            (customer_id, reservation.weekday, reservation.time, reservation.court, month, year),
        )

    def has_fine_for_month(self, product_code: int, month: int, year: int) -> bool:
        return bool(
            self._one_value(
                """SELECT EXISTS (SELECT 1 FROM consumos WHERE codigo_produto = %s
                   AND EXTRACT(MONTH FROM data) = %s AND EXTRACT(YEAR FROM data) = %s)
                   AS gerada""",
                (product_code, month, year),
            )
        )

    def monthly_paid(self, customer_id: int, month: int, year: int) -> bool:
        return bool(
            self._one_value(
                """SELECT EXISTS (SELECT 1 FROM consumos
                   WHERE codigo_cliente = %s AND codigo_produto = -1 AND pago = TRUE
                     AND EXTRACT(MONTH FROM data) = %s AND EXTRACT(YEAR FROM data) = %s)
                   AS paga""",
                (customer_id, month, year),
            )
        )


class CsvTableExporter:
    """Grava cada tabela em ``<tabela>_<AAAAMMDD_HHMMSS>.csv`` (RF16)."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def export_all(self, directory: Path, stamp: str) -> list[Path]:
        written: list[Path] = []
        with self._database.transaction() as connection:
            for table in self._database.schema.table_names():
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM {table}")
                    header = [column[0] for column in cursor.description]
                    rows = cursor.fetchall()
                path = directory / f"{table}_{stamp}.csv"
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle, delimiter=";")
                    writer.writerow(header)
                    writer.writerows(rows)
                written.append(path)
        return written
