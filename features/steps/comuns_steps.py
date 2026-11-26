"""Passos compartilhados: preparação de dados e verificação de aceite/recusa."""

from __future__ import annotations

from behave import given, then

from dante_squash.domain import Customer, PriceSchedule, Product
from support import tipos  # noqa: F401  (registra os tipos de parâmetro)
from support.ajuda import faixas_da_tabela


# --- Preparação (Dado) -------------------------------------------------------

@given("que existem os clientes:")
def step_clientes(context):
    for linha in context.table:
        context.catalogo.save_customer(Customer(int(linha["codigo"]), linha["nome"], "", "", ""))


@given('que já existe o cliente "{nome}" com código {codigo:d}')
def step_cliente_existente(context, nome, codigo):
    context.catalogo.save_customer(Customer(codigo, nome, "", "", ""))


@given('que existe o produto "{descricao}" de código {codigo:d} com preço {preco:Dinheiro}')
def step_produto_existente(context, descricao, codigo, preco):
    context.catalogo.save_product(Product(codigo, descricao, preco, "un"))


@given(
    "que a tabela de valores tem sauna {sauna:Dinheiro}, aula {aula:Dinheiro} e os vencimentos:"
)
def step_tabela_valores(context, sauna, aula):
    context.catalogo.save_prices(PriceSchedule(sauna, aula, faixas_da_tabela(context.table)))


@given("que a tabela de valores não foi configurada")
def step_sem_tabela(context):
    context.banco.state.prices = None


@given('que hoje é "{hoje:Data}"')
def step_hoje(context, hoje):
    context.relogio.current = hoje


# --- Verificação (Então) -----------------------------------------------------

@then("a operação deve ser aceita")
def step_aceita(context):
    assert context.erro is None, f"A operação foi recusada: {context.erro}"


@then('o sistema deve recusar com a mensagem "{mensagem}"')
def step_recusa(context, mensagem):
    assert context.erro is not None, "Era esperada uma recusa, mas a operação foi aceita."
    assert str(context.erro) == mensagem, (
        f'Mensagem esperada: "{mensagem}"\nMensagem obtida:   "{context.erro}"'
    )
