"""Passos de cadastro de clientes, produtos e tabela de valores."""

from __future__ import annotations

from behave import then, when

from dante_squash.domain import Customer, PriceSchedule, Product
from support.ajuda import assert_valor, executar, faixas_da_tabela


# --- Clientes ----------------------------------------------------------------

@when('eu cadastro o cliente "{nome:Texto}" com CPF "{cpf:Texto}" e telefone "{telefone:Texto}"')
def step_cadastrar_cliente(context, nome, cpf, telefone):
    # Código 0 = cliente novo, exatamente como a tela de cadastro envia.
    executar(context, lambda: context.catalogo.save_customer(Customer(0, nome, cpf, "", telefone)))


@when('eu cadastro um cliente com nome de {tamanho:d} caracteres e CPF "{cpf:Texto}"')
def step_cadastrar_cliente_tamanho(context, tamanho, cpf):
    executar(context, lambda: context.catalogo.save_customer(Customer(0, "A" * tamanho, cpf)))


@when('eu altero o nome do cliente de código {codigo:d} para "{nome}"')
def step_alterar_cliente(context, codigo, nome):
    atual = next(c for c in context.catalogo.customers() if c.code == codigo)
    executar(
        context,
        lambda: context.catalogo.save_customer(
            Customer(codigo, nome, atual.cpf, atual.birthday, atual.phone)
        ),
    )


@then('o cliente "{nome}" deve estar cadastrado com código {codigo:d}')
def step_cliente_cadastrado(context, nome, codigo):
    clientes = {c.name: c.code for c in context.catalogo.customers()}
    assert nome in clientes, f'Cliente "{nome}" não encontrado. Cadastrados: {clientes}'
    assert clientes[nome] == codigo, f"Código esperado {codigo}, obtido {clientes[nome]}"


@then("devem existir {quantidade:d} clientes cadastrados")
def step_quantidade_clientes(context, quantidade):
    obtido = len(context.catalogo.customers())
    assert obtido == quantidade, f"Esperados {quantidade} clientes, obtidos {obtido}"


# --- Produtos ----------------------------------------------------------------

@when(
    'eu cadastro o produto "{descricao:Texto}" com preço {preco:Dinheiro} e unidade "{unidade:Texto}"'
)
def step_cadastrar_produto(context, descricao, preco, unidade):
    # Código 0 = produto novo, exatamente como a tela de cadastro envia.
    executar(context, lambda: context.catalogo.save_product(Product(0, descricao, preco, unidade)))


@when(
    'eu cadastro o produto de código {codigo:d} "{descricao}" com preço {preco:Dinheiro} '
    'e unidade "{unidade}"'
)
def step_cadastrar_produto_codigo(context, codigo, descricao, preco, unidade):
    executar(
        context, lambda: context.catalogo.save_product(Product(codigo, descricao, preco, unidade))
    )


@then(
    'o produto "{descricao}" deve estar cadastrado com código {codigo:d} e preço {preco:Dinheiro}'
)
def step_produto_cadastrado(context, descricao, codigo, preco):
    assert context.erro is None, f"O cadastro foi recusado: {context.erro}"
    produto = next((p for p in context.catalogo.products() if p.description == descricao), None)
    assert produto is not None, f'Produto "{descricao}" não encontrado.'
    assert produto.code == codigo, f"Código esperado {codigo}, obtido {produto.code}"
    assert_valor(produto.price, preco, "Preço do produto")


# --- Tabela de valores -------------------------------------------------------

@when(
    "eu salvo a tabela de valores com sauna {sauna:Dinheiro}, aula {aula:Dinheiro} "
    "e os vencimentos:"
)
def step_salvar_tabela(context, sauna, aula):
    tabela = PriceSchedule(sauna, aula, faixas_da_tabela(context.table))
    executar(context, lambda: context.catalogo.save_prices(tabela))


@then("a tabela de valores deve ter {quantidade:d} faixas de vencimento")
def step_quantidade_faixas(context, quantidade):
    tabela = context.catalogo.prices()
    assert tabela is not None, "Nenhuma tabela de valores foi gravada."
    assert len(tabela.due_tiers) == quantidade, (
        f"Esperadas {quantidade} faixas, obtidas {len(tabela.due_tiers)}"
    )


@then("nenhuma tabela de valores deve estar gravada")
def step_sem_tabela_gravada(context):
    assert context.catalogo.prices() is None, "Uma tabela inválida foi gravada."
