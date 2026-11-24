"""RF05 — pagamento de cliente cadastrado (CT04, CT05, CT27)."""

from datetime import date
from decimal import Decimal

import pytest

from dante_squash.domain import BusinessRuleError


@pytest.fixture
def ana(scenario):
    """Ana com R$ 100,00 em aberto (2 × R$ 50,00)."""
    customer = scenario.customer("Ana")
    product = scenario.product("Raquete alugada", "50.00")
    scenario.services.consumptions.register(
        customer_id=customer, product_code=product, quantity=2, consumption_date=date(2026, 3, 12)
    )
    return customer


def test_total_a_pagar_soma_consumos_nao_pagos(scenario, ana):
    assert scenario.services.payments.total_due(ana) == Decimal("100.00")


def test_ct04_pagamento_parcial_gera_saldo_devedor(scenario, ana):
    result = scenario.services.payments.settle(
        customer_id=ana, payment_date=date(2026, 3, 12),
        amount_paid=Decimal("60.00"), discount=Decimal("0"),
    )
    assert not result.paid_in_full
    history = scenario.services.consumptions.for_customer(ana)
    saldo = [c for c in history if c.product_code == 0]
    assert len(saldo) == 1 and saldo[0].unit_price == Decimal("40.00") and not saldo[0].paid
    assert all(c.paid for c in history if c.product_code != 0)
    assert scenario.services.payments.total_due(ana) == Decimal("40.00")


def test_ct05_pagamento_com_desconto_quita_a_divida(scenario, ana):
    result = scenario.services.payments.settle(
        customer_id=ana, payment_date=date(2026, 3, 12),
        amount_paid=Decimal("90.00"), discount=Decimal("10.00"),
    )
    assert result.paid_in_full
    desconto = [c for c in scenario.services.consumptions.for_customer(ana) if c.product_code == 0]
    assert len(desconto) == 1 and desconto[0].unit_price == Decimal("-10.00") and desconto[0].paid
    assert scenario.services.payments.total_due(ana) == Decimal("0.00")


def test_d05_pagamento_nan_e_rejeitado_e_nada_e_gravado(scenario, ana):
    with pytest.raises(BusinessRuleError, match="valor a ser pago"):
        scenario.services.payments.settle(
            customer_id=ana, payment_date=date(2026, 3, 12),
            amount_paid=Decimal("NaN"), discount=Decimal("0"),
        )
    assert scenario.services.payments.total_due(ana) == Decimal("100.00")


def test_cliente_sem_divida_nao_pode_pagar(scenario):
    bruno = scenario.customer("Bruno")
    with pytest.raises(BusinessRuleError, match="não possui valores em aberto"):
        scenario.services.payments.settle(
            customer_id=bruno, payment_date=date(2026, 3, 12),
            amount_paid=Decimal("10"), discount=Decimal("0"),
        )
