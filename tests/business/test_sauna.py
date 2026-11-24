"""RF06 a RF08 — sauna (CT10 e fluxo de fechamento)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from dante_squash.domain import BusinessRuleError


@pytest.fixture
def sauna(scenario):
    scenario.default_prices()
    return scenario.services.sauna


def test_entrada_e_lancada_com_o_valor_da_tabela(scenario, sauna):
    sauna.add_attendee("Carla", scenario.clock.today())
    (account,) = sauna.accounts(scenario.clock.today())
    assert account.name == "Carla" and not account.closed
    assert [(c.product_code, c.unit_price) for c in account.consumptions] == [(1, Decimal("30.00"))]


def test_ct10_nome_repetido_no_dia_e_rejeitado(scenario, sauna):
    sauna.add_attendee("Ana", scenario.clock.today())
    with pytest.raises(BusinessRuleError, match="diferente de outro cliente"):
        sauna.add_attendee("ana", scenario.clock.today())
    assert len(sauna.accounts(scenario.clock.today())) == 1


def test_ct10_so_e_possivel_alterar_o_dia_de_hoje(scenario, sauna):
    ontem = scenario.clock.today() - timedelta(days=1)
    with pytest.raises(BusinessRuleError, match="dia de hoje"):
        sauna.add_attendee("Ana", ontem)
    assert sauna.accounts(ontem) == []


def test_fechamento_ajusta_a_entrada_e_encerra_a_conta(scenario, sauna):
    today = scenario.clock.today()
    agua = scenario.product("Água", "5.00")
    sauna.add_attendee("Carla", today)
    sauna.add_product_consumption(name="Carla", account_date=today, product_code=agua, quantity=2)
    sauna.close_account("Carla", today, Decimal("35.00"))  # desconto de R$ 5,00
    (account,) = sauna.accounts(today)
    assert account.closed
    assert account.total == Decimal("35.00")
    assert account.consumptions[0].unit_price == Decimal("25.00")


def test_conta_encerrada_nao_aceita_consumo(scenario, sauna):
    today = scenario.clock.today()
    agua = scenario.product("Água", "5.00")
    sauna.add_attendee("Carla", today)
    sauna.close_account("Carla", today, Decimal("30.00"))
    with pytest.raises(BusinessRuleError, match="já foi encerrada"):
        sauna.add_product_consumption(name="Carla", account_date=today, product_code=agua, quantity=1)


def test_entrada_nao_pode_ser_excluida_mas_consumo_pode(scenario, sauna):
    today = scenario.clock.today()
    agua = scenario.product("Água", "5.00")
    sauna.add_attendee("Carla", today)
    item = sauna.add_product_consumption(
        name="Carla", account_date=today, product_code=agua, quantity=1
    )
    with pytest.raises(BusinessRuleError, match="entrada da sauna"):
        sauna.remove_product_consumption("Carla", today, 1)
    sauna.remove_product_consumption("Carla", today, item.sequence)
    (account,) = sauna.accounts(today)
    assert len(account.consumptions) == 1


def test_excluir_frequentador_com_conta_aberta(scenario, sauna):
    today = scenario.clock.today()
    sauna.add_attendee("Carla", today)
    sauna.remove_attendee("Carla", today)
    assert sauna.accounts(today) == []
