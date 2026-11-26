"""Passos de consumo de produtos, pagamentos e sauna."""

from __future__ import annotations

from behave import given, then, when

from support.ajuda import assert_valor, executar
from support.tipos import lista_codigos

AJUSTE = 0


# --- Consumo -----------------------------------------------------------------

def _lancar(context, quantidade, produto, cliente, data):
    return context.consumos.register(
        customer_id=cliente, product_code=produto, quantity=quantidade, consumption_date=data
    )


@given(
    'que o cliente {cliente:d} consumiu {quantidade:d} unidades do produto {produto:d} '
    'em "{data:Data}"'
)
def step_consumo_existente(context, cliente, quantidade, produto, data):
    _lancar(context, quantidade, produto, cliente, data)


@when(
    'eu lanço {quantidade:d} unidades do produto {produto:d} para o cliente {cliente:d} '
    'em "{data:Data}"'
)
def step_lancar_consumo(context, quantidade, produto, cliente, data):
    executar(context, lambda: _lancar(context, quantidade, produto, cliente, data))


@then("o cliente {cliente:d} deve ter um débito em aberto de {valor:Dinheiro}")
def step_debito_aberto(context, cliente, valor):
    assert_valor(context.pagamentos.total_due(cliente), valor, "Débito em aberto")


@then('os consumos do cliente {cliente:d} devem ter as sequências "{sequencias}"')
def step_sequencias(context, cliente, sequencias):
    obtido = tuple(c.sequence for c in context.consumos.for_customer(cliente))
    esperado = lista_codigos(sequencias)
    assert obtido == esperado, f"Sequências esperadas {esperado}, obtidas {obtido}"


# --- Pagamentos --------------------------------------------------------------

@when(
    'o cliente {cliente:d} paga {valor:Dinheiro} com desconto de {desconto:Dinheiro} '
    'em "{data:Data}"'
)
def step_pagar(context, cliente, valor, desconto, data):
    executar(
        context,
        lambda: context.pagamentos.settle(
            customer_id=cliente, payment_date=data, amount_paid=valor, discount=desconto
        ),
    )


@then("o total devido pelo cliente {cliente:d} deve ser {valor:Dinheiro}")
def step_total_devido(context, cliente, valor):
    assert_valor(context.pagamentos.total_due(cliente), valor, "Total devido")


@then("o pagamento deve ser registrado como {tipo}")
def step_tipo_pagamento(context, tipo):
    assert context.erro is None, f"O pagamento foi recusado: {context.erro}"
    esperado_total = {"total": True, "parcial": False}[tipo]
    assert context.resultado.paid_in_full is esperado_total, (
        f"Esperado pagamento {tipo}, obtido paid_in_full={context.resultado.paid_in_full}"
    )
    assert context.banco.state.payments[-1][4] is esperado_total


@then("o saldo do pagamento deve ser {valor:Dinheiro}")
def step_saldo(context, valor):
    assert_valor(context.resultado.balance, valor, "Saldo do pagamento")


@then(
    "deve existir {quantidade:d} pagamento registrado de {valor:Dinheiro} "
    "para o cliente {cliente:d}"
)
def step_pagamentos_registrados(context, quantidade, valor, cliente):
    registros = [r for r in context.banco.state.payments if r[0] == cliente]
    assert len(registros) == quantidade, f"Esperados {quantidade} pagamentos, obtidos {registros}"
    assert_valor(registros[0][3], valor, "Valor pago")


@then(
    "deve existir um lançamento de ajuste de {valor:Dinheiro} {situacao} "
    "para o cliente {cliente:d}"
)
def step_lancamento_ajuste(context, valor, situacao, cliente):
    pago = {"em aberto": False, "quitado": True}[situacao]
    ajustes = [
        c for c in context.consumos.for_customer(cliente)
        if c.product_code == AJUSTE and c.paid is pago and c.total == valor
    ]
    assert len(ajustes) == 1, (
        f"Ajuste de {valor} {situacao} não encontrado. "
        f"Lançamentos: {context.consumos.for_customer(cliente)}"
    )


@then("não deve existir pagamento registrado")
def step_sem_pagamento(context):
    assert not context.banco.state.payments, f"Pagamentos gravados: {context.banco.state.payments}"


# --- Sauna -------------------------------------------------------------------

def _conta(context, nome):
    contas = context.sauna.accounts(context.relogio.current)
    conta = next((c for c in contas if c.name.casefold() == nome.casefold()), None)
    assert conta is not None, f'Conta de "{nome}" não encontrada na sauna.'
    return conta


@given('que "{nome}" já entrou na sauna hoje')
def step_entrou_sauna(context, nome):
    context.sauna.add_attendee(nome, context.relogio.current)


@given('que "{nome}" consumiu {quantidade:d} unidades do produto {produto:d} na sauna')
def step_consumiu_sauna(context, nome, quantidade, produto):
    context.sauna.add_product_consumption(
        name=nome, account_date=context.relogio.current, product_code=produto, quantity=quantidade
    )


@given('que a conta de "{nome}" foi fechada com pagamento de {valor:Dinheiro}')
def step_conta_fechada(context, nome, valor):
    context.sauna.close_account(nome, context.relogio.current, valor)


@when('eu registro a entrada de "{nome:Texto}" na sauna em "{data:Data}"')
def step_registrar_entrada(context, nome, data):
    executar(context, lambda: context.sauna.add_attendee(nome, data))


@when('"{nome}" consome {quantidade:d} unidades do produto {produto:d} na sauna')
def step_consome_sauna(context, nome, quantidade, produto):
    executar(
        context,
        lambda: context.sauna.add_product_consumption(
            name=nome, account_date=context.relogio.current, product_code=produto, quantity=quantidade
        ),
    )


@when('eu fecho a conta de "{nome}" com pagamento de {valor:Dinheiro}')
def step_fechar_conta(context, nome, valor):
    executar(context, lambda: context.sauna.close_account(nome, context.relogio.current, valor))


@then('a conta de "{nome}" na sauna deve totalizar {valor:Dinheiro}')
def step_total_conta(context, nome, valor):
    conta = _conta(context, nome)
    assert_valor(sum(c.total for c in conta.consumptions), valor, f'Total da conta de "{nome}"')


@then('a conta de "{nome}" na sauna deve estar {situacao}')
def step_situacao_conta(context, nome, situacao):
    fechada = {"aberta": False, "fechada": True}[situacao]
    conta = _conta(context, nome)
    assert conta.closed is fechada, f'Esperado conta {situacao}, obtido closed={conta.closed}'


