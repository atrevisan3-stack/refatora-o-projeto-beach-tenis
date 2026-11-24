"""Raiz de composição: cria e conecta todos os objetos do sistema.

É o único lugar que conhece as implementações concretas (PostgreSQL, Tkinter);
o restante do código depende apenas das portas em ``ports.py``.
"""

from __future__ import annotations

import logging
from typing import Mapping

from dante_squash.domain import (
    InternalProducts,
    Money,
    PaymentCalculator,
    SaunaRules,
    SquashCalendar,
)
from dante_squash.ports import Clock, TableExporter, UnitOfWorkFactory
from dante_squash.services.application_services import ApplicationServices
from dante_squash.services.backup import BackupService
from dante_squash.services.catalog import CatalogService
from dante_squash.services.consumptions import ConsumptionService
from dante_squash.services.monthly_billing import MonthlyBillingService
from dante_squash.services.payments import PaymentService
from dante_squash.services.reports import CashFlowClassifier, ReportService
from dante_squash.services.reservations import ReservationService
from dante_squash.services.sauna import SaunaService
from dante_squash.services.squash_billing import SquashBillingCalculator


class ServiceFactory:
    """Monta os serviços sobre qualquer unidade de trabalho (banco real ou de teste)."""

    def __init__(self, unit_of_work: UnitOfWorkFactory, exporter: TableExporter, clock: Clock) -> None:
        self.unit_of_work = unit_of_work
        self.exporter = exporter
        self.clock = clock
        self.products = InternalProducts()
        self.money = Money()
        self.squash = SquashCalendar()

    def build(self) -> ApplicationServices:
        uow = self.unit_of_work
        return ApplicationServices(
            catalog=CatalogService(uow, self.products),
            reservations=ReservationService(uow, self.squash),
            consumptions=ConsumptionService(uow, self.products),
            payments=PaymentService(uow, PaymentCalculator(self.money), self.products, self.money),
            sauna=SaunaService(uow, self.clock, SaunaRules(), self.products, self.money),
            monthly_billing=MonthlyBillingService(
                uow,
                SquashBillingCalculator(self.products, self.squash, self.money),
                self.products,
            ),
            reports=ReportService(uow, CashFlowClassifier(self.products), self.money),
            backup=BackupService(self.exporter, self.clock),
        )


class Application:
    """Conecta ao PostgreSQL, cria as tabelas ausentes e abre a janela (RF17, RF18)."""

    def __init__(self, environment: Mapping[str, str]) -> None:
        self._environment = environment

    def run(self) -> None:
        import tkinter as tk

        from dante_squash.infrastructure.clock import SystemClock
        from dante_squash.infrastructure.postgres import (
            CsvTableExporter,
            EnvironmentSettings,
            PostgresDatabase,
            PostgresSchema,
            PostgresUnitOfWorkFactory,
            PsycopgConnector,
        )
        from dante_squash.presentation.main_window import MainWindow
        from dante_squash.presentation.widgets import (
            ActionRunner,
            TkDialogs,
            UiToolkit,
            ValueParser,
            WidgetFactory,
        )

        logging.basicConfig(level=logging.INFO)
        dialogs = TkDialogs()
        root = tk.Tk()
        try:
            database = PostgresDatabase(
                PsycopgConnector(EnvironmentSettings(self._environment).dsn()), PostgresSchema()
            )
            database.initialize()
        except Exception as error:
            root.withdraw()
            dialogs.error("Falha ao conectar ao banco de dados", str(error))
            root.destroy()
            raise SystemExit(1) from error
        clock = SystemClock()
        factory = ServiceFactory(
            PostgresUnitOfWorkFactory(database), CsvTableExporter(database), clock
        )
        kit = UiToolkit(
            dialogs=dialogs,
            parser=ValueParser(),
            widgets=WidgetFactory(),
            runner=ActionRunner(dialogs, logging.getLogger("dante_squash")),
        )
        MainWindow(root, factory.build(), kit, clock, factory.squash)
        root.mainloop()
