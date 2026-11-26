"""Testes de banco de dados sobre PostgreSQL real (CT13 a CT16 e backup)."""

from datetime import date
from decimal import Decimal

import pytest

from dante_squash.domain import Consumption

pytestmark = pytest.mark.db


def test_ct13_cria_as_oito_tabelas_e_a_carga_padrao(database):
    with database.transaction() as connection, connection.cursor() as cursor:
        cursor.execute(
            """SELECT table_name FROM information_schema.tables
               WHERE table_schema = 'public' ORDER BY table_name"""
        )
        tables = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT codigo FROM produtos ORDER BY codigo")
        products = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT nome FROM clientes WHERE codigo = 0")
        sauna_customer = cursor.fetchall()
    assert tables == sorted(database.schema.table_names())
    assert products == [-3, -2, -1, 0, 1]
    assert sauna_customer == [("Cliente Sauna",)]


def test_inicializacao_repetida_nao_duplica_nem_apaga_dados(database, postgres):
    postgres.customer("Ana")
    database.initialize()
    assert [c.name for c in postgres.services.catalog.customers()] == ["Ana"]


def test_datas_e_valores_tem_tipos_corretos(database):
    with database.transaction() as connection, connection.cursor() as cursor:
        cursor.execute(
            """SELECT column_name, data_type FROM information_schema.columns
               WHERE table_name = 'consumos' AND column_name IN ('data', 'valor')
               ORDER BY column_name"""
        )
        types = cursor.fetchall()
    assert types == [("data", "date"), ("valor", "numeric")]


def test_ct15_chave_estrangeira_impede_produto_inexistente(database, postgres):
    from dante_squash.infrastructure.postgres import PostgresUnitOfWork

    ana = postgres.customer("Ana")
    with pytest.raises(Exception, match="(?i)foreign key|chave estrangeira"):
        with PostgresUnitOfWork(database) as work:
            work.consumptions.insert(
                Consumption(ana, date(2026, 3, 12), 1, 999, 1, Decimal("1"), False)
            )
    assert postgres.services.consumptions.for_customer(ana) == []


def test_ct16_falha_no_meio_do_pagamento_desfaz_tudo(database, postgres, monkeypatch):
    """Transação por caso de uso (P05): sem pagamento órfão nem consumos quitados."""
    from dante_squash.infrastructure.postgres import PostgresConsumptionRepository

    ana = postgres.customer("Ana")
    agua = postgres.product("Água", "50.00")
    postgres.services.consumptions.register(
        customer_id=ana, product_code=agua, quantity=2, consumption_date=date(2026, 3, 12)
    )
    original_insert = PostgresConsumptionRepository.insert

    def failing_insert(self, consumption):
        if consumption.product_code == 0:
            raise RuntimeError("falha simulada ao gravar o saldo")
        original_insert(self, consumption)

    monkeypatch.setattr(PostgresConsumptionRepository, "insert", failing_insert)
    with pytest.raises(RuntimeError, match="falha simulada"):
        postgres.services.payments.settle(
            customer_id=ana, payment_date=date(2026, 3, 12),
            amount_paid=Decimal("60"), discount=Decimal("0"),
        )
    monkeypatch.undo()
    with database.transaction() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM pagamentos")
        assert cursor.fetchall()[0][0] == 0
    assert postgres.services.payments.total_due(ana) == Decimal("100.00")


def test_backup_exporta_as_oito_tabelas_em_csv(postgres, tmp_path):
    postgres.customer("Ana")
    files = postgres.services.backup.export(tmp_path)
    assert sorted(f.name for f in files) == sorted(
        f"{t}_20260312_103000.csv"
        for t in ("clientes", "produtos", "valores", "consumos", "consumossauna",
                  "pagamentos", "horariossquash", "mensalidades")
    )
    content = (tmp_path / "clientes_20260312_103000.csv").read_text(encoding="utf-8")
    assert content.splitlines()[0] == "codigo;cpf;nome;dataaniversario;telefone"
    assert "Ana" in content


def test_dsn_ausente_gera_erro_claro():
    from dante_squash.infrastructure.postgres import EnvironmentSettings

    with pytest.raises(RuntimeError, match="DANTE_SQUASH_DSN"):
        EnvironmentSettings({}).dsn()
