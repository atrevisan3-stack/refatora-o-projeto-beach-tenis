"""RF11 e RF12 — mensalidades e multas do squash (CT06 a CT09, CT17)."""

from datetime import date
from decimal import Decimal

import pytest

from dante_squash.domain import BusinessRuleError, DueTier, PriceSchedule


def charges(scenario, customer_id, product_code):
    return [
        c for c in scenario.services.consumptions.for_customer(customer_id)
        if c.product_code == product_code
    ]


def test_ct06_jogo_divide_o_valor_mensal_entre_os_jogadores(scenario):
    scenario.services.catalog.save_prices(
        PriceSchedule(Decimal("30"), Decimal("50"), (DueTier(10, Decimal("210")),))
    )
    ana, bruno, caio = (scenario.customer(n) for n in ("Ana", "Bruno", "Caio"))
    scenario.game(1, "18:00", 1, ana, bruno, caio)
    generated = scenario.services.monthly_billing.generate_monthly_charges(date(2026, 3, 12))
    assert len(generated) == 3
    assert {c.unit_price for c in generated} == {Decimal("70.00")}


@pytest.mark.parametrize("mes, aulas", [(2, 4), (3, 5)])
def test_ct06_aula_cobra_o_numero_real_de_semanas_d08(scenario, mes, aulas):
    scenario.default_prices()
    ana = scenario.customer("Ana")
    scenario.lesson(2, "10:00", 2, ana)  # terças-feiras
    generated = scenario.services.monthly_billing.generate_monthly_charges(date(2026, mes, 5))
    assert [c.unit_price for c in generated] == [Decimal("50.00") * aulas]


def test_ct07_geracao_repetida_no_mes_nao_duplica(scenario):
    scenario.default_prices()
    ana, bruno = scenario.customer("Ana"), scenario.customer("Bruno")
    scenario.game(1, "18:00", 1, ana, bruno)
    billing = scenario.services.monthly_billing
    assert len(billing.generate_monthly_charges(date(2026, 3, 12))) == 2
    assert billing.generate_monthly_charges(date(2026, 3, 20)) == []
    assert len(charges(scenario, ana, -1)) == 1


@pytest.fixture
def march_game(scenario):
    """Jogo de Ana e Bruno com mensalidades de março geradas; Bruno pagou em 12/03."""
    scenario.default_prices()
    ana, bruno = scenario.customer("Ana"), scenario.customer("Bruno")
    scenario.game(1, "18:00", 1, ana, bruno)
    scenario.lesson(2, "10:00", 2, scenario.customer("Carla"))
    scenario.services.monthly_billing.generate_monthly_charges(date(2026, 3, 2))
    scenario.services.payments.settle(
        customer_id=bruno, payment_date=date(2026, 3, 12),
        amount_paid=Decimal("100.00"), discount=Decimal("0"),
    )
    return ana, bruno


def test_ct08_primeira_multa_so_para_quem_nao_pagou(scenario, march_game):
    ana, bruno = march_game
    generated = scenario.services.monthly_billing.generate_fines(date(2026, 3, 16))
    assert [(c.customer_id, c.product_code, c.unit_price) for c in generated] == [
        (ana, -2, Decimal("10.00"))  # (220 − 200) ÷ 2 jogadores; aula ignorada
    ]
    assert charges(scenario, bruno, -2) == []


def test_ct09_segunda_multa_e_gerada_apos_a_primeira_d01(scenario, march_game):
    ana, _ = march_game
    billing = scenario.services.monthly_billing
    billing.generate_fines(date(2026, 3, 16))
    second = billing.generate_fines(date(2026, 3, 22))
    assert [(c.customer_id, c.product_code, c.unit_price) for c in second] == [
        (ana, -3, Decimal("10.00"))  # (240 − 220) ÷ 2
    ]


def test_multa_repetida_no_mesmo_mes_e_rejeitada(scenario, march_game):
    billing = scenario.services.monthly_billing
    billing.generate_fines(date(2026, 3, 16))
    with pytest.raises(BusinessRuleError, match="já foram geradas"):
        billing.generate_fines(date(2026, 3, 18))


def test_multa_fora_do_periodo_e_rejeitada(scenario, march_game):
    with pytest.raises(BusinessRuleError, match="fora do período"):
        scenario.services.monthly_billing.generate_fines(date(2026, 3, 12))


def test_ct17_pagamento_nos_dias_1_a_9_e_reconhecido_d02(scenario):
    """No legado, datas de 7 dígitos (dias 1 a 9) liam o mês errado."""
    scenario.default_prices()
    ana, bruno = scenario.customer("Ana"), scenario.customer("Bruno")
    scenario.game(1, "18:00", 1, ana, bruno)
    scenario.services.monthly_billing.generate_monthly_charges(date(2026, 3, 2))
    scenario.services.payments.settle(
        customer_id=ana, payment_date=date(2026, 3, 5),
        amount_paid=Decimal("100.00"), discount=Decimal("0"),
    )
    generated = scenario.services.monthly_billing.generate_fines(date(2026, 3, 16))
    assert [c.customer_id for c in generated] == [bruno]
