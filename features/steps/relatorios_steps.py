"""Passos de relatórios (ficha, fluxo de caixa, resumo mensal, grade) e backup."""

from __future__ import annotations

import tempfile
from pathlib import Path

from behave import given, then, when

from support.ajuda import assert_valor, executar
from support.tipos import dinheiro

SITUACOES = {"em aberto": False, "quitado": True}


# --- Ficha do cliente --------------------------------------------------------

@when("eu consulto a ficha do cliente {cliente:d}")
def step_consultar_ficha(context, cliente):
    executar(context, lambda: context.relatorios.customer_sheet(cliente))


def _ficha(context):
    assert context.erro is None, f"A consulta foi recusada: {context.erro}"
    return context.resultado


@then("a ficha deve listar {quantidade:d} reservas")
def step_ficha_reservas(context, quantidade):
    obtido = len(_ficha(context).reservations)
    assert obtido == quantidade, f"Esperadas {quantidade} reservas, obtidas {obtido}"


@then("o total em aberto da ficha deve ser {valor:Dinheiro}")
def step_ficha_total(context, valor):
    assert_valor(_ficha(context).total_due, valor, "Total em aberto da ficha")


@then("o histórico da ficha deve ter os lançamentos:")
def step_ficha_historico(context):
    obtido = [(descricao, item.total, item.paid) for item, descricao in _ficha(context).history]
    esperado = [
        (linha["descricao"], dinheiro(linha["valor"]), SITUACOES[linha["situacao"]])
        for linha in context.table
    ]
    assert obtido == esperado, f"Histórico esperado:\n{esperado}\nHistórico obtido:\n{obtido}"


# --- Fluxo de caixa ----------------------------------------------------------

@when('eu consulto o fluxo de caixa de "{data:Data}"')
def step_consultar_caixa(context, data):
    executar(context, lambda: context.relatorios.cash_flow(data))


@then("o fluxo de caixa deve mostrar:")
def step_caixa(context):
    assert context.erro is None, f"A consulta foi recusada: {context.erro}"
    obtido = [(linha.category, linha.paid, linha.unpaid) for linha in context.resultado]
    esperado = [
        (linha["categoria"], dinheiro(linha["pago"]), dinheiro(linha["em_aberto"]))
        for linha in context.table
    ]
    assert obtido == esperado, f"Caixa esperado:\n{esperado}\nCaixa obtido:\n{obtido}"


# --- Resumo mensal -----------------------------------------------------------

@when("eu gero o resumo mensal de {mes:d}/{ano:d}")
def step_resumo_mensal(context, mes, ano):
    executar(context, lambda: context.relatorios.monthly_summary(ano, mes))


@then("o resumo deve ter {quantidade:d} dias")
def step_resumo_dias(context, quantidade):
    obtido = len(context.resultado)
    assert obtido == quantidade, f"Esperados {quantidade} dias, obtidos {obtido}"


@then(
    "no dia {dia:d} o resumo deve mostrar vendido {vendido:Dinheiro}, pago {pago:Dinheiro} "
    "e a receber {receber:Dinheiro}"
)
def step_resumo_dia(context, dia, vendido, pago, receber):
    linha = next((d for d in context.resultado if d.day.day == dia), None)
    assert linha is not None, f"O dia {dia} não aparece no resumo."
    assert_valor(linha.sold, vendido, f"Vendido no dia {dia}")
    assert_valor(linha.paid, pago, f"Pago no dia {dia}")
    assert_valor(linha.to_receive, receber, f"A receber no dia {dia}")


# --- Grade do dia ------------------------------------------------------------

@when('eu consulto a grade de "{data:Data}"')
def step_consultar_grade(context, data):
    executar(context, lambda: context.reservas.day_grid(data))


def _celula(context, horario, quadra):
    linha = next((r for r in context.resultado if r.time == horario), None)
    assert linha is not None, f'O horário "{horario}" não existe na grade.'
    return linha.courts[quadra - 1]


@then('na grade o horário "{horario}" na quadra {quadra:d} deve mostrar "{texto}"')
def step_grade_celula(context, horario, quadra, texto):
    obtido = _celula(context, horario, quadra)
    assert obtido == texto, f'Esperado "{texto}", obtido "{obtido}"'


@then('na grade o horário "{horario}" na quadra {quadra:d} deve estar livre')
def step_grade_livre(context, horario, quadra):
    obtido = _celula(context, horario, quadra)
    assert obtido == "", f'Esperado horário livre, obtido "{obtido}"'


@then("todos os horários da grade devem estar livres")
def step_grade_vazia(context):
    ocupados = [(r.time, r.courts) for r in context.resultado if any(r.courts)]
    assert not ocupados, f"Horários ocupados: {ocupados}"


# --- Backup ------------------------------------------------------------------

@given("que existe uma pasta para o backup")
def step_pasta_backup(context):
    pasta = tempfile.TemporaryDirectory()
    context.add_cleanup(pasta.cleanup)
    context.pasta_backup = Path(pasta.name)


@when("eu faço o backup nessa pasta")
def step_backup(context):
    executar(context, lambda: context.backup.export(context.pasta_backup))


@when('eu faço o backup na pasta "{pasta}"')
def step_backup_pasta(context, pasta):
    executar(context, lambda: context.backup.export(Path(pasta)))


@then('o backup deve gerar o arquivo "{nome}"')
def step_arquivo_backup(context, nome):
    assert context.erro is None, f"O backup foi recusado: {context.erro}"
    nomes = [arquivo.name for arquivo in context.resultado]
    assert nome in nomes, f'Arquivo "{nome}" não gerado. Arquivos: {nomes}'


@then("nenhuma exportação deve ter sido feita")
def step_sem_exportacao(context):
    assert not context.exportador.calls, f"Exportações feitas: {context.exportador.calls}"
