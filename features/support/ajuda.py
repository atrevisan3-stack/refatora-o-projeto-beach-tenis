"""Funções auxiliares compartilhadas pelos arquivos de passos."""

from __future__ import annotations

from decimal import Decimal

from dante_squash.domain import BusinessRuleError, DueTier
from support.tipos import dinheiro


def executar(context, acao):
    """Executa um caso de uso guardando o resultado ou a regra de negócio violada."""
    context.erro = None
    context.resultado = None
    try:
        context.resultado = acao()
    except BusinessRuleError as erro:
        context.erro = erro
    return context.resultado


def faixas_da_tabela(table) -> tuple[DueTier, ...]:
    faixas = []
    for linha in table:
        valor = linha["valor"].strip()
        faixas.append(
            DueTier(
                day=int(linha["dia"]),
                monthly_price=None if valor in ("", "vazio") else dinheiro(valor),
            )
        )
    return tuple(faixas)


def assert_valor(obtido, esperado: Decimal, descricao: str) -> None:
    assert Decimal(obtido) == esperado, f"{descricao}: esperado {esperado}, obtido {obtido}"
