"""Fluxos principais de ponta a ponta, sem interface (CT01 e CT02).

Rodam no banco em memória e no PostgreSQL real.
"""

from datetime import date
from decimal import Decimal


def by_category(lines):
    return {line.category: (line.paid, line.unpaid) for line in lines}


def test_ct01_squash_reserva_mensalidade_pagamento_e_caixa(scenario):
    services = scenario.services
    scenario.default_prices()
    ana, bruno = scenario.customer("Ana"), scenario.customer("Bruno")
    scenario.game(1, "18:00", 1, ana, bruno)

    generated = services.monthly_billing.generate_monthly_charges(date(2026, 3, 12))
    assert sorted((c.customer_id, c.product_code, c.unit_price) for c in generated) == [
        (ana, -1, Decimal("100.00")),
        (bruno, -1, Decimal("100.00")),
    ]

    result = services.payments.settle(
        customer_id=ana, payment_date=date(2026, 3, 12),
        amount_paid=Decimal("100.00"), discount=Decimal("0"),
    )
    assert result.paid_in_full
    assert services.payments.total_due(ana) == Decimal("0.00")
    assert services.payments.total_due(bruno) == Decimal("100.00")
    assert by_category(services.reports.cash_flow(date(2026, 3, 12)))["Squash"] == (
        Decimal("100.00"),
        Decimal("100.00"),
    )


def test_ct02_sauna_entrada_consumo_fechamento_e_caixa(scenario):
    services = scenario.services
    scenario.default_prices()
    today = scenario.clock.today()
    agua = scenario.product("Água", "5.00")

    services.sauna.add_attendee("Carla", today)
    services.sauna.add_product_consumption(
        name="Carla", account_date=today, product_code=agua, quantity=2
    )
    (account,) = services.sauna.accounts(today)
    assert account.total == Decimal("40.00")

    services.sauna.close_account("Carla", today, Decimal("40.00"))
    (account,) = services.sauna.accounts(today)
    assert account.closed and all(c.paid for c in account.consumptions)
    lines = by_category(services.reports.cash_flow(today))
    assert lines["Sauna"] == (Decimal("30.00"), Decimal("0.00"))
    assert lines["Produtos"] == (Decimal("10.00"), Decimal("0.00"))
