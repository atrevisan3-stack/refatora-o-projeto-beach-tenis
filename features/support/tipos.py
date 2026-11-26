"""Tipos de parâmetro usados nos passos (formato brasileiro de datas e dinheiro)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import parse
from behave import register_type

DIAS_DA_SEMANA = {
    "segunda-feira": 1,
    "terça-feira": 2,
    "quarta-feira": 3,
    "quinta-feira": 4,
    "sexta-feira": 5,
    "sábado": 6,
    "domingo": 7,
}


def dinheiro(texto: str) -> Decimal:
    """Converte '1.234,56' em Decimal('1234.56')."""
    return Decimal(texto.strip().replace(".", "").replace(",", "."))


def data_br(texto: str) -> date:
    return datetime.strptime(texto.strip(), "%d/%m/%Y").date()


def lista_codigos(texto: str) -> tuple[int, ...]:
    return tuple(int(parte) for parte in texto.split(",") if parte.strip())


@parse.with_pattern(r"-?\d{1,3}(?:\.\d{3})*,\d{2}")
def _parse_dinheiro(texto: str) -> Decimal:
    return dinheiro(texto)


@parse.with_pattern(r"\d{2}/\d{2}/\d{4}")
def _parse_data(texto: str) -> date:
    return data_br(texto)


@parse.with_pattern(r'[^"]*')
def _parse_texto(texto: str) -> str:
    return texto


@parse.with_pattern(r"(?:na|no|da|do) (?:" + "|".join(DIAS_DA_SEMANA) + ")")
def _parse_dia_semana(texto: str) -> int:
    return DIAS_DA_SEMANA[texto.split(" ", 1)[1]]


@parse.with_pattern(r"um jogo|uma aula")
def _parse_tipo_reserva(texto: str) -> bool:
    return texto == "um jogo"


register_type(
    Dinheiro=_parse_dinheiro,
    Data=_parse_data,
    Texto=_parse_texto,
    DiaSemana=_parse_dia_semana,
    TipoReserva=_parse_tipo_reserva,
)
