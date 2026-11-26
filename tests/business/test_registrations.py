"""RF01, RF02, RF04, RF09 e RF10 — cadastros, consumos e reservas (CT11, CT12, CT14)."""

from datetime import date
from decimal import Decimal

import pytest

from dante_squash.domain import BusinessRuleError, Customer, Product, Reservation


def test_ct14_codigo_do_cliente_e_maior_mais_um(scenario):
    first = scenario.customer("Ana")
    second = scenario.customer("Bruno")
    assert second == first + 1
    scenario.services.catalog.save_customer(Customer(first, "Ana Paula", "", "", ""))
    assert scenario.services.catalog.customer(first).name == "Ana Paula"
    assert len(scenario.services.catalog.customers()) == 2


def test_cliente_interno_da_sauna_nao_aparece_nem_pode_ser_alterado(scenario):
    assert all(c.code != 0 for c in scenario.services.catalog.customers())
    with pytest.raises(BusinessRuleError, match="uso interno"):
        scenario.services.catalog.save_customer(Customer(0, "X", "", "", ""))


def test_ct12_cliente_com_consumo_nao_pode_ser_excluido(scenario):
    ana = scenario.customer("Ana")
    agua = scenario.product("Água", "5.00")
    scenario.services.consumptions.register(
        customer_id=ana, product_code=agua, quantity=1, consumption_date=date(2026, 3, 12)
    )
    with pytest.raises(BusinessRuleError, match="não pode ser excluído"):
        scenario.services.catalog.delete_customer(ana)


def test_cliente_com_reserva_nao_pode_ser_excluido(scenario):
    """No legado a reserva não era verificada e o erro vinha do banco."""
    ana = scenario.customer("Ana")
    scenario.game(1, "18:00", 1, ana)
    with pytest.raises(BusinessRuleError, match="não pode ser excluído"):
        scenario.services.catalog.delete_customer(ana)


def test_cliente_sem_vinculos_e_excluido(scenario):
    ana = scenario.customer("Ana")
    scenario.services.catalog.delete_customer(ana)
    assert scenario.services.catalog.customers() == []


def test_produto_usado_nao_pode_ser_excluido_e_livre_pode(scenario):
    ana = scenario.customer("Ana")
    agua, toalha = scenario.product("Água", "5.00"), scenario.product("Toalha", "8.00")
    scenario.services.consumptions.register(
        customer_id=ana, product_code=agua, quantity=1, consumption_date=date(2026, 3, 12)
    )
    with pytest.raises(BusinessRuleError, match="não pode ser excluído"):
        scenario.services.catalog.delete_product(agua)
    scenario.services.catalog.delete_product(toalha)
    assert [p.code for p in scenario.services.catalog.products()] == [agua]


def test_produto_novo_recebe_codigo_a_partir_de_2(scenario):
    code = scenario.services.catalog.save_product(Product(None, "Água", Decimal("5"), "un")).code
    assert code == 2


def test_ct11_consumo_pago_nao_pode_ser_excluido(scenario):
    ana = scenario.customer("Ana")
    agua = scenario.product("Água", "5.00")
    item = scenario.services.consumptions.register(
        customer_id=ana, product_code=agua, quantity=1, consumption_date=date(2026, 3, 12)
    )
    scenario.services.payments.settle(
        customer_id=ana, payment_date=date(2026, 3, 12),
        amount_paid=Decimal("5.00"), discount=Decimal("0"),
    )
    with pytest.raises(BusinessRuleError, match="já foi pago"):
        scenario.services.consumptions.delete(ana, item.date, item.sequence)


def test_consumo_aberto_pode_ser_excluido(scenario):
    ana = scenario.customer("Ana")
    agua = scenario.product("Água", "5.00")
    item = scenario.services.consumptions.register(
        customer_id=ana, product_code=agua, quantity=3, consumption_date=date(2026, 3, 12)
    )
    assert item.total == Decimal("15.00")
    scenario.services.consumptions.delete(ana, item.date, item.sequence)
    assert scenario.services.consumptions.for_customer(ana) == []


def test_consumo_de_produto_interno_e_rejeitado(scenario):
    ana = scenario.customer("Ana")
    with pytest.raises(BusinessRuleError, match="produto consumido"):
        scenario.services.consumptions.register(
            customer_id=ana, product_code=1, quantity=1, consumption_date=date(2026, 3, 12)
        )


def test_reserva_existente_so_e_substituida_com_confirmacao(scenario):
    ana, bruno, caio = (scenario.customer(n) for n in ("Ana", "Bruno", "Caio"))
    scenario.game(3, "15:45", 3, ana, bruno)
    reservations = scenario.services.reservations
    with pytest.raises(BusinessRuleError, match="confirme a substituição"):
        reservations.save(Reservation(3, "15:45", 3, True, (caio,)), replace_existing=False)
    reservations.save(Reservation(3, "15:45", 3, True, (caio,)), replace_existing=True)
    assert [r.customer_ids for r in reservations.reservations()] == [(caio,)]


def test_reserva_com_cliente_inexistente_e_rejeitada(scenario):
    with pytest.raises(BusinessRuleError, match="não cadastrado"):
        scenario.services.reservations.save(
            Reservation(1, "18:00", 1, True, (99,)), replace_existing=False
        )


def test_excluir_reserva(scenario):
    ana = scenario.customer("Ana")
    scenario.game(1, "18:00", 1, ana)
    scenario.services.reservations.delete(1, "18:00", 1)
    assert scenario.services.reservations.reservations() == []


def test_grade_do_dia_marca_aula(scenario):
    ana, bruno = scenario.customer("Ana"), scenario.customer("Bruno")
    scenario.lesson(2, "10:00", 2, ana)
    scenario.game(2, "18:00", 1, ana, bruno)
    grid = {row.time: row.courts for row in scenario.services.reservations.day_grid(date(2026, 3, 10))}
    assert grid["10:00"] == ("", "Ana (AULA)", "")
    assert grid["18:00"] == ("Ana, Bruno", "", "")
    domingo = scenario.services.reservations.day_grid(date(2026, 3, 15))
    assert all(cell == "" for row in domingo for cell in row.courts)
