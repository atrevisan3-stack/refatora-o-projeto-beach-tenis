"""Regras de validação do domínio (RN01, RN03, RN05, RN06, RN14, RN19)."""

from decimal import Decimal

import pytest

from dante_squash.domain import (
    BusinessRuleError,
    Customer,
    DueTier,
    Money,
    PaymentCalculator,
    PriceSchedule,
    Product,
    Reservation,
    SaunaRules,
    SquashCalendar,
)


def tiers(*pairs):
    return tuple(DueTier(day, None if price is None else Decimal(price)) for day, price in pairs)


def schedule(*pairs):
    return PriceSchedule(Decimal("30"), Decimal("50"), tiers(*pairs))


class TestCliente:
    def test_nome_obrigatorio(self):
        with pytest.raises(BusinessRuleError, match="nome do cliente deve ser informado"):
            Customer(None, "   ", "", "", "").validate()

    @pytest.mark.parametrize("tamanho, valido", [(50, True), (51, False)])
    def test_nome_ate_50_caracteres(self, tamanho, valido):
        customer = Customer(None, "A" * tamanho, "", "", "")
        if valido:
            customer.validate()
        else:
            with pytest.raises(BusinessRuleError):
                customer.validate()

    def test_cpf_ate_11_caracteres(self):
        with pytest.raises(BusinessRuleError, match="CPF"):
            Customer(None, "Ana", "123456789012", "", "").validate()


class TestProduto:
    def test_preco_deve_ser_positivo(self):
        with pytest.raises(BusinessRuleError, match="preço"):
            Product(None, "Água", Decimal("0"), "un").validate()

    @pytest.mark.parametrize("codigo", [0, 1, -1, -3])
    def test_codigos_internos_sao_protegidos(self, codigo):
        with pytest.raises(BusinessRuleError, match="uso interno"):
            Product(codigo, "Água", Decimal("5"), "un").validate()

    def test_produto_novo_sem_codigo_e_valido(self):
        Product(None, "Água", Decimal("5"), "un").validate()


class TestValores:
    """CT03: limites de vencimento e faixas incompletas ou repetidas."""

    @pytest.mark.parametrize("dia", [0, 29])
    def test_vencimento_fora_de_1_a_28_e_rejeitado(self, dia):
        with pytest.raises(BusinessRuleError):
            schedule((dia, "200")).validate()

    def test_vencimento_28_e_aceito(self):
        schedule((28, "200")).validate()

    def test_faixa_incompleta_e_rejeitada(self):
        with pytest.raises(BusinessRuleError, match="informados juntos"):
            schedule((10, "200"), (15, None)).validate()

    def test_dias_repetidos_sao_rejeitados(self):
        with pytest.raises(BusinessRuleError, match="diferentes"):
            schedule((10, "200"), (10, "220")).validate()


class TestReserva:
    def test_aula_admite_um_unico_cliente(self):
        with pytest.raises(BusinessRuleError, match="somente um cliente"):
            Reservation(3, "15:45", 3, False, (1, 2)).validate()

    def test_jogo_admite_varios_clientes(self):
        Reservation(1, "18:00", 1, True, (1, 2, 3)).validate()

    def test_mesmo_cliente_duas_vezes_e_rejeitado(self):
        with pytest.raises(BusinessRuleError, match="já foi incluído"):
            Reservation(1, "18:00", 1, True, (1, 1)).validate()

    @pytest.mark.parametrize(
        "dia, horario, quadra", [(7, "18:00", 1), (1, "18:10", 1), (1, "18:00", 4)]
    )
    def test_dia_horario_e_quadra_validos(self, dia, horario, quadra):
        with pytest.raises(BusinessRuleError):
            Reservation(dia, horario, quadra, True, (1,)).validate()


class TestSauna:
    def test_nome_unico_no_dia_sem_diferenciar_maiusculas(self):
        with pytest.raises(BusinessRuleError, match="diferente de outro cliente"):
            SaunaRules().validate_name("ana", ("Ana",))


class TestPagamento:
    """RN12 e correção dos defeitos D04 (ponto flutuante) e D05 (NaN)."""

    def setup_method(self):
        self.calculator = PaymentCalculator(Money())

    def test_pagamento_integral(self):
        result = self.calculator.calculate(
            total_due=Decimal("100"), amount_paid=Decimal("100"), discount=Decimal("0")
        )
        assert result.paid_in_full and result.balance == 0

    def test_pagamento_parcial_gera_saldo_devedor(self):
        result = self.calculator.calculate(
            total_due=Decimal("100"), amount_paid=Decimal("60"), discount=Decimal("0")
        )
        assert not result.paid_in_full
        assert result.balance == Decimal("40.00")

    def test_valor_pago_a_maior_gera_credito(self):
        result = self.calculator.calculate(
            total_due=Decimal("100"), amount_paid=Decimal("120"), discount=Decimal("0")
        )
        assert result.balance == Decimal("-20.00")

    def test_d04_centavos_nao_geram_saldo_falso(self):
        """Em double, 0,1 + 0,2 − 0,3 ≠ 0; com Decimal o pagamento fica integral."""
        result = self.calculator.calculate(
            total_due=Decimal("0.1") + Decimal("0.2"),
            amount_paid=Decimal("0.3"),
            discount=Decimal("0"),
        )
        assert result.paid_in_full

    @pytest.mark.parametrize("valor", ["NaN", "Infinity", "0", "-5"])
    def test_d05_valor_invalido_e_rejeitado(self, valor):
        with pytest.raises(BusinessRuleError, match="valor a ser pago"):
            self.calculator.calculate(
                total_due=Decimal("100"), amount_paid=Decimal(valor), discount=Decimal("0")
            )


class TestCalendarioDoSquash:
    """Correção do D08: aulas contadas pelo número real de semanas do mês."""

    @pytest.mark.parametrize(
        "dia_semana, ano, mes, esperado",
        [
            (2, 2026, 3, 5),  # março/2026 tem 5 terças-feiras
            (2, 2026, 2, 4),  # fevereiro/2026 tem 4 terças-feiras
            (1, 2026, 3, 5),  # março/2026 tem 5 segundas-feiras
            (4, 2026, 4, 5),  # abril/2026 tem 5 quintas-feiras
        ],
    )
    def test_aulas_no_mes(self, dia_semana, ano, mes, esperado):
        assert SquashCalendar().lessons_in_month(dia_semana, ano, mes) == esperado
