"""Passos de reservas de squash, mensalidades e multas."""

from __future__ import annotations

from behave import given, then, when

from dante_squash.domain import Consumption, Reservation
from support.ajuda import assert_valor, executar
from support.tipos import lista_codigos

MENSALIDADE = -1
CODIGOS_MULTA = (-2, -3)


def _reserva(is_game, dia, horario, quadra, clientes) -> Reservation:
    return Reservation(dia, horario, quadra, is_game, lista_codigos(clientes))


def _lancamentos(context, cliente, codigo):
    return [c for c in context.consumos.for_customer(cliente) if c.product_code == codigo]


# --- Reservas ----------------------------------------------------------------

@given(
    'que existe {jogo:TipoReserva} {dia:DiaSemana} às "{horario}" na quadra {quadra:d} '
    'para os clientes "{clientes:Texto}"'
)
def step_reserva_existente(context, jogo, dia, horario, quadra, clientes):
    context.reservas.save(
        _reserva(jogo, dia, horario, quadra, clientes), replace_existing=True
    )


@when(
    'eu reservo {jogo:TipoReserva} {dia:DiaSemana} às "{horario}" na quadra {quadra:d} '
    'para os clientes "{clientes:Texto}"'
)
def step_reservar(context, jogo, dia, horario, quadra, clientes):
    reserva = _reserva(jogo, dia, horario, quadra, clientes)
    executar(context, lambda: context.reservas.save(reserva, replace_existing=False))


@when(
    'eu confirmo a substituição por {jogo:TipoReserva} {dia:DiaSemana} às "{horario}" '
    'na quadra {quadra:d} para os clientes "{clientes:Texto}"'
)
def step_substituir(context, jogo, dia, horario, quadra, clientes):
    reserva = _reserva(jogo, dia, horario, quadra, clientes)
    executar(context, lambda: context.reservas.save(reserva, replace_existing=True))


@then("deve existir {quantidade:d} reserva na grade")
def step_quantidade_reservas(context, quantidade):
    obtido = len(context.reservas.reservations())
    assert obtido == quantidade, f"Esperadas {quantidade} reservas, obtidas {obtido}"


@then(
    'a reserva {dia:DiaSemana} às "{horario}" na quadra {quadra:d} '
    'deve ser dos clientes "{clientes:Texto}"'
)
def step_reserva_clientes(context, dia, horario, quadra, clientes):
    reserva = next(
        r
        for r in context.reservas.reservations()
        if (r.weekday, r.time, r.court) == (dia, horario, quadra)
    )
    esperado = lista_codigos(clientes)
    assert reserva.customer_ids == esperado, (
        f"Clientes esperados {esperado}, obtidos {reserva.customer_ids}"
    )


# --- Mensalidades ------------------------------------------------------------

@given('que as mensalidades já foram geradas em "{data:Data}"')
def step_mensalidades_geradas(context, data):
    context.cobranca.generate_monthly_charges(data)


@when('eu gero as mensalidades em "{data:Data}"')
def step_gerar_mensalidades(context, data):
    executar(context, lambda: context.cobranca.generate_monthly_charges(data))


@then("devem ser geradas {quantidade:d} cobranças")
def step_quantidade_cobrancas(context, quantidade):
    assert context.erro is None, f"A geração foi recusada: {context.erro}"
    assert len(context.resultado) == quantidade, (
        f"Esperadas {quantidade} cobranças, geradas {len(context.resultado)}"
    )


@then("o cliente {cliente:d} deve ter uma mensalidade de {valor:Dinheiro}")
def step_valor_mensalidade(context, cliente, valor):
    lancamentos = _lancamentos(context, cliente, MENSALIDADE)
    assert len(lancamentos) == 1, f"Esperada 1 mensalidade, encontradas {len(lancamentos)}"
    assert_valor(lancamentos[0].total, valor, "Valor da mensalidade")


@then("o cliente {cliente:d} deve ter {quantidade:d} lançamentos de mensalidade")
def step_quantidade_mensalidades(context, cliente, quantidade):
    obtido = len(_lancamentos(context, cliente, MENSALIDADE))
    assert obtido == quantidade, f"Esperados {quantidade} lançamentos, obtidos {obtido}"


# --- Multas ------------------------------------------------------------------

@given('que as multas já foram geradas em "{data:Data}"')
def step_multas_geradas(context, data):
    context.cobranca.generate_fines(data)


@given('que o cliente {cliente:d} pagou a mensalidade de "{data:Data}"')
def step_mensalidade_paga(context, cliente, data):
    consumos = context.banco.state.consumptions
    sequencia = 1 + max((k[2] for k in consumos if k[:2] == (cliente, data)), default=0)
    consumos[(cliente, data, sequencia)] = Consumption(
        cliente, data, sequencia, MENSALIDADE, 1,
        context.catalogo.prices().due_tiers[0].monthly_price, paid=True,
    )


@when('eu gero as multas em "{data:Data}"')
def step_gerar_multas(context, data):
    executar(context, lambda: context.cobranca.generate_fines(data))


@then(
    "o cliente {cliente:d} deve ter uma multa de código {codigo:d} no valor de {valor:Dinheiro}"
)
def step_valor_multa(context, cliente, codigo, valor):
    multas = _lancamentos(context, cliente, codigo)
    assert len(multas) == 1, f"Esperada 1 multa {codigo}, encontradas {len(multas)}"
    assert_valor(multas[0].total, valor, "Valor da multa")


@then("o cliente {cliente:d} não deve ter multas")
def step_sem_multas(context, cliente):
    multas = [c for c in context.consumos.for_customer(cliente)
              if c.product_code in CODIGOS_MULTA]
    assert not multas, f"O cliente {cliente} recebeu multas: {multas}"


@then("o cliente {cliente:d} não deve ter multa de código {codigo:d}")
def step_sem_multa_codigo(context, cliente, codigo):
    multas = _lancamentos(context, cliente, codigo)
    assert not multas, f"O cliente {cliente} recebeu a multa {codigo}: {multas}"
