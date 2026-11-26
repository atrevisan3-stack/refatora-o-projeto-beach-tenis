"""Conjunto de serviços de aplicação entregue à interface."""

from __future__ import annotations

from dataclasses import dataclass

from dante_squash.services.backup import BackupService
from dante_squash.services.catalog import CatalogService
from dante_squash.services.consumptions import ConsumptionService
from dante_squash.services.monthly_billing import MonthlyBillingService
from dante_squash.services.payments import PaymentService
from dante_squash.services.reports import ReportService
from dante_squash.services.reservations import ReservationService
from dante_squash.services.sauna import SaunaService


@dataclass(frozen=True)
class ApplicationServices:
    catalog: CatalogService
    reservations: ReservationService
    consumptions: ConsumptionService
    payments: PaymentService
    sauna: SaunaService
    monthly_billing: MonthlyBillingService
    reports: ReportService
    backup: BackupService
