"""Ganchos do behave: cada cenário recebe um sistema novo e isolado."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

FEATURES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FEATURES_DIR.parent
for path in (str(PROJECT_ROOT), str(FEATURES_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from dante_squash.services.catalog import CatalogService  # noqa: E402
from dante_squash.services.consumptions import ConsumptionService  # noqa: E402
from dante_squash.services.monthly_billing import MonthlyBillingService  # noqa: E402
from dante_squash.services.payments import PaymentService  # noqa: E402
from dante_squash.services.sauna import SaunaService  # noqa: E402
from support.memoria import InMemoryUnitOfWork  # noqa: E402


def before_scenario(context, scenario) -> None:
    context.banco = InMemoryUnitOfWork()
    context.hoje = date(2026, 3, 12)
    context.erro = None
    context.resultado = None
    context.catalogo = CatalogService(context.banco)
    context.consumos = ConsumptionService(context.banco)
    context.pagamentos = PaymentService(context.banco)
    context.cobranca = MonthlyBillingService(context.banco)
    context.sauna = SaunaService(context.banco, clock=lambda: context.hoje)
