"""Testes de interface gráfica (CT21 a CT25): botões e campos reais do Tkinter.

Os diálogos são substituídos por ``FakeDialogs`` para que as mensagens possam
ser verificadas sem abrir janelas.
"""

from datetime import date
from decimal import Decimal

import pytest

pytestmark = pytest.mark.gui


def test_ct21_cliente_sem_nome_mostra_mensagem_de_erro(gui):
    tab = gui.window.customers
    tab.save_button.invoke()
    assert gui.dialogs.last_error() == "O nome do cliente deve ser informado!"
    assert gui.rows(tab.table) == []


def test_cadastro_de_cliente_pela_tela(gui):
    tab = gui.window.customers
    gui.type(tab.name, "Ana")
    gui.type(tab.phone, "54999990000")
    tab.save_button.invoke()
    assert gui.dialogs.last_info() == "Cliente 1 salvo com sucesso!"
    assert gui.rows(tab.table) == [("1", "Ana", "", "", "54999990000")]
    assert tab.name.get() == ""


def test_cadastro_de_produto_pela_tela(gui):
    """No código anterior, produto novo recebia código 0 e era sempre rejeitado."""
    tab = gui.window.products
    gui.type(tab.description, "Água")
    gui.type(tab.price, "5,50")
    gui.type(tab.unit, "Garrafa")
    tab.save_button.invoke()
    assert gui.dialogs.errors == []
    assert gui.rows(tab.table) == [("2", "Água", "5,50", "Garrafa")]


def test_ct22_sauna_so_aceita_o_dia_de_hoje(gui):
    gui.scenario.default_prices()
    tab = gui.window.sauna
    gui.type(tab.day, "11/03/2026")
    gui.type(tab.name, "Carla")
    tab.add_button.invoke()
    assert gui.dialogs.last_error() == "Só é possível alterar os dados da sauna para o dia de hoje!"


def test_fluxo_da_sauna_pela_tela(gui):
    gui.scenario.default_prices()
    agua = gui.scenario.product("Água", "5.00")
    tab = gui.window.sauna
    gui.type(tab.name, "Carla")
    tab.add_button.invoke()
    assert gui.rows(tab.accounts) == [("Carla", "30,00", "Aberta")]
    gui.select(tab.accounts, "Carla")
    gui.type(tab.product, str(agua))
    gui.type(tab.quantity, "2")
    tab.consume_button.invoke()
    assert gui.rows(tab.accounts) == [("Carla", "40,00", "Aberta")]
    assert len(gui.rows(tab.items)) == 2
    gui.select(tab.accounts, "Carla")
    gui.type(tab.amount, "40")
    tab.close_button.invoke()
    assert gui.dialogs.last_info() == "Conta de Carla encerrada."
    assert gui.rows(tab.accounts) == [("Carla", "40,00", "Encerrada")]


def test_ct23_grade_mostra_aula_marcada(gui):
    ana = gui.scenario.customer("Ana")
    gui.scenario.lesson(2, "10:00", 2, ana)
    tab = gui.window.day_grid
    gui.type(tab.day, "10/03/2026")  # terça-feira
    tab.show_button.invoke()
    assert ("10:00", "", "Ana (AULA)", "") in gui.rows(tab.table)


def test_substituir_reserva_pede_confirmacao(gui):
    ana, bruno = gui.scenario.customer("Ana"), gui.scenario.customer("Bruno")
    gui.scenario.game(1, "18:00", 1, ana)
    tab = gui.window.reservations
    tab.refresh()
    gui.type(tab.weekday, "1")
    gui.type(tab.time, "18:00")
    gui.type(tab.court, "1")
    gui.type(tab.customers, str(bruno))
    gui.dialogs.confirm_answer = False
    tab.save_button.invoke()
    assert gui.rows(tab.table) == [("1", "18:00", "1", "Jogo", str(ana))]
    gui.dialogs.confirm_answer = True
    tab.save_button.invoke()
    assert gui.rows(tab.table) == [("1", "18:00", "1", "Jogo", str(bruno))]
    assert len(gui.dialogs.confirmations) == 2


def test_ct24_pagamento_parcial_pede_confirmacao(gui):
    ana = gui.scenario.customer("Ana")
    agua = gui.scenario.product("Água", "50.00")
    gui.scenario.services.consumptions.register(
        customer_id=ana, product_code=agua, quantity=2, consumption_date=date(2026, 3, 12)
    )
    tab = gui.window.payments
    gui.type(tab.customer, str(ana))
    gui.type(tab.amount, "60")
    gui.dialogs.confirm_answer = False
    tab.pay_button.invoke()
    assert gui.scenario.services.payments.total_due(ana) == Decimal("100.00")
    gui.dialogs.confirm_answer = True
    tab.pay_button.invoke()
    assert gui.dialogs.last_info() == "Pagamento parcial registrado. Saldo: R$ 40,00"
    assert tab.total_label.cget("text") == "Total em aberto: R$ 40,00"


def test_valor_invalido_mostra_erro_sem_travar(gui):
    tab = gui.window.payments
    gui.type(tab.customer, "1")
    gui.type(tab.amount, "abc")
    tab.pay_button.invoke()
    assert "valor numérico válido" in gui.dialogs.last_error()


def test_ct25_resumo_mensal_mostra_o_dia_31(gui):
    ana = gui.scenario.customer("Ana")
    agua = gui.scenario.product("Água", "50.00")
    gui.scenario.services.consumptions.register(
        customer_id=ana, product_code=agua, quantity=1, consumption_date=date(2026, 3, 31)
    )
    tab = gui.window.monthly_summary
    gui.type(tab.month, "3")
    gui.type(tab.year, "2026")
    tab.show_button.invoke()
    rows = gui.rows(tab.table)
    assert len(rows) == 32  # 31 dias + total
    assert rows[30] == ("31", "0,00", "0,00", "50,00", "50,00", "0,00", "50,00")
    assert rows[31][0] == "Total" and rows[31][4] == "50,00"


def test_geracao_de_mensalidades_pela_tela(gui):
    gui.scenario.default_prices()
    ana, bruno = gui.scenario.customer("Ana"), gui.scenario.customer("Bruno")
    gui.scenario.game(1, "18:00", 1, ana, bruno)
    tab = gui.window.monthly_billing
    gui.type(tab.day, "12/03/2026")
    tab.charges_button.invoke()
    assert gui.dialogs.last_info() == "2 mensalidade(s) gerada(s)."
    assert len(gui.rows(tab.table)) == 2


def test_fluxo_de_caixa_pela_tela(gui):
    ana = gui.scenario.customer("Ana")
    agua = gui.scenario.product("Água", "5.00")
    gui.scenario.services.consumptions.register(
        customer_id=ana, product_code=agua, quantity=2, consumption_date=date(2026, 3, 12)
    )
    tab = gui.window.cash_flow
    tab.show_button.invoke()
    assert ("Produtos", "0,00", "10,00", "10,00") in gui.rows(tab.table)


def test_ficha_do_cliente_pela_tela(gui):
    ana = gui.scenario.customer("Ana")
    gui.scenario.game(1, "18:00", 1, ana)
    tab = gui.window.customer_sheet
    gui.type(tab.customer, str(ana))
    tab.show_button.invoke()
    assert tab.summary.cget("text") == "Ana — total devido: R$ 0,00"
    assert gui.rows(tab.reservations) == [("Segunda-feira", "18:00", "1", "Jogo")]


def test_backup_pela_tela(gui, tmp_path):
    gui.dialogs.directory = str(tmp_path)
    gui.window.backup.backup_button.invoke()
    assert gui.dialogs.last_info().startswith("1 tabela(s) exportada(s)")
