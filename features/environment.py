"""Ganchos do behave: cada cenário recebe um sistema novo e isolado.

Os serviços são montados pela mesma raiz de composição da aplicação
(``ServiceFactory``), sobre o banco em memória de ``tests/support/fakes.py``,
que implementa as portas de ``dante_squash/ports.py``.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

FEATURES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FEATURES_DIR.parent
for path in (str(PROJECT_ROOT), str(FEATURES_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from dante_squash.composition import ServiceFactory  # noqa: E402
from tests.support.fakes import (  # noqa: E402
    FixedClock,
    InMemoryDatabase,
    InMemoryUnitOfWorkFactory,
    RecordingExporter,
)


def before_scenario(context, scenario) -> None:
    context.banco = InMemoryDatabase()
    context.relogio = FixedClock(date(2026, 3, 12))
    context.erro = None
    context.resultado = None
    servicos = ServiceFactory(
        InMemoryUnitOfWorkFactory(context.banco), RecordingExporter(), context.relogio
    ).build()
    context.catalogo = servicos.catalog
    context.reservas = servicos.reservations
    context.consumos = servicos.consumptions
    context.pagamentos = servicos.payments
    context.cobranca = servicos.monthly_billing
    context.sauna = servicos.sauna
