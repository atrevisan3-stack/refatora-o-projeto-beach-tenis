"""RF13 a RF16 — ficha, fluxo de caixa, resumo mensal e backup."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from dante_squash.domain import BusinessRuleError


def by_category(lines):
    return {line.category: (line.paid, line.unpaid) for line in lines}


def test_ficha_do_cliente(scenario):
    ana = scenario.customer("Ana")
    agua = scenario.product("Água", "5.00")
    scenario.game(1, "18:00", 1, ana)
    scenario.services.consumptions.register(
        customer_id=ana, product_code=agua, quantity=2, consumption_date=date(2026, 3, 12)
    )
    sheet = scenario.services.reports.customer_sheet(ana)
    assert sheet.customer.name == "Ana"
    assert [(r.weekday, r.time) for r in sheet.reservations] == [(1, "18:00")]
    assert sheet.total_due == Decimal("10.00")
    assert [description for _, description in sheet.history] == ["Água"]


def test_fluxo_de_caixa_separa_sauna_squash_e_produtos(scenario):
    scenario.default_prices()
    today = scenario.clock.today()
    ana = scenario.customer("Ana")
    agua = scenario.product("Água", "5.00")
    scenario.game(1, "18:00", 1, ana)
    scenario.services.monthly_billing.generate_monthly_charges(today)
    scenario.services.sauna.add_attendee("Carla", today)
    scenario.services.sauna.add_product_consumption(
        name="Carla", account_date=today, product_code=agua, quantity=2
    )
    scenario.services.sauna.close_account("Carla", today, Decimal("40.00"))
    lines = by_category(scenario.services.reports.cash_flow(today))
    assert lines == {
        "Sauna": (Decimal("30.00"), Decimal("0.00")),
        "Squash": (Decimal("0.00"), Decimal("200.00")),
        "Produtos": (Decimal("10.00"), Decimal("0.00")),
    }


def test_saldo_e_desconto_ficam_fora_do_caixa(scenario):
    ana = scenario.customer("Ana")
    agua = scenario.product("Água", "5.00")
    today = scenario.clock.today()
    scenario.services.consumptions.register(
        customer_id=ana, product_code=agua, quantity=2, consumption_date=today
    )
    scenario.services.payments.settle(
        customer_id=ana, payment_date=today, amount_paid=Decimal("6"), discount=Decimal("1")
    )
    lines = by_category(scenario.services.reports.cash_flow(today))
    assert lines["Produtos"] == (Decimal("10.00"), Decimal("0.00"))


def test_resumo_mensal_inclui_o_dia_31_d03(scenario):
    ana = scenario.customer("Ana")
    agua = scenario.product("Água", "50.00")
    scenario.services.consumptions.register(
        customer_id=ana, product_code=agua, quantity=1, consumption_date=date(2026, 3, 31)
    )
    days = scenario.services.reports.monthly_summary(2026, 3)
    assert len(days) == 31
    assert days[-1].day == date(2026, 3, 31)
    assert days[-1].sold == Decimal("50.00") and days[-1].to_receive == Decimal("50.00")
    assert sum(d.sold for d in days) == Decimal("50.00")


def test_resumo_de_fevereiro_tem_28_dias(scenario):
    assert len(scenario.services.reports.monthly_summary(2026, 2)) == 28


def test_ficha_de_cliente_inexistente(scenario):
    with pytest.raises(BusinessRuleError, match="não cadastrado"):
        scenario.services.reports.customer_sheet(999)


def test_backup_exige_pasta_existente(memory, tmp_path):
    with pytest.raises(BusinessRuleError, match="pasta existente"):
        memory.services.backup.export(tmp_path / "nao_existe")


def test_backup_nomeia_arquivos_com_o_instante(memory, tmp_path):
    files = memory.services.backup.export(tmp_path)
    assert [Path(f).name for f in files] == ["clientes_20260312_103000.csv"]
