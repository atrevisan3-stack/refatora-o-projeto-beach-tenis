"""Passos de exclusão de clientes, produtos, consumos, reservas e sauna."""

from __future__ import annotations

from decimal import Decimal

from behave import given, then, when

from support.ajuda import executar


@given('que o cliente {cliente:d} pagou {valor:Dinheiro} em "{data:Data}"')
def step_cliente_pagou(context, cliente, valor, data):
    context.pagamentos.settle(
        customer_id=cliente, payment_date=data, amount_paid=valor, discount=Decimal("0")
    )


@when("eu excluo o cliente {codigo:d}")
def step_excluir_cliente(context, codigo):
    executar(context, lambda: context.catalogo.delete_customer(codigo))


@when("eu excluo o produto {codigo:d}")
def step_excluir_produto(context, codigo):
    executar(context, lambda: context.catalogo.delete_product(codigo))


@then('o produto "{descricao}" não deve estar cadastrado')
def step_produto_ausente(context, descricao):
    descricoes = [p.description for p in context.catalogo.products()]
    assert descricao not in descricoes, f'"{descricao}" continua cadastrado: {descricoes}'


@when('eu excluo o consumo de sequência {sequencia:d} do cliente {cliente:d} em "{data:Data}"')
def step_excluir_consumo(context, sequencia, cliente, data):
    executar(context, lambda: context.consumos.delete(cliente, data, sequencia))


@when('eu excluo a reserva {dia:DiaSemana} às "{horario}" na quadra {quadra:d}')
def step_excluir_reserva(context, dia, horario, quadra):
    executar(context, lambda: context.reservas.delete(dia, horario, quadra))


@when('eu removo "{nome}" da sauna')
def step_remover_frequentador(context, nome):
    executar(context, lambda: context.sauna.remove_attendee(nome, context.relogio.current))


@when('eu excluo o consumo de sequência {sequencia:d} da conta de "{nome}" na sauna')
def step_excluir_consumo_sauna(context, sequencia, nome):
    executar(
        context,
        lambda: context.sauna.remove_product_consumption(nome, context.relogio.current, sequencia),
    )


@then('não deve existir conta de "{nome}" na sauna')
def step_sem_conta(context, nome):
    nomes = [c.name for c in context.sauna.accounts(context.relogio.current)]
    assert nome not in nomes, f'A conta de "{nome}" continua na sauna: {nomes}'
