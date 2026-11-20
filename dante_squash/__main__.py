"""Start the desktop application."""

import tkinter as tk
from tkinter import messagebox

import os

from dante_squash.infrastructure.mariadb import MariaDBDatabase, MariaDBUnitOfWork
from dante_squash.infrastructure.postgres import PostgresDatabase, PostgresUnitOfWork
from dante_squash.presentation.tk_app import DanteSquashApp
from dante_squash.services.catalog import CatalogService
from dante_squash.services.consumptions import ConsumptionService
from dante_squash.services.monthly_billing import MonthlyBillingService
from dante_squash.services.payments import PaymentService
from dante_squash.services.sauna import SaunaService


def main() -> None:
    root = tk.Tk()
    try:
        database_type = os.environ.get("DANTE_SQUASH_DATABASE", "postgresql").lower()
        if database_type == "mariadb":
            database = MariaDBDatabase.from_environment()
            unit_of_work_type = MariaDBUnitOfWork
        elif database_type == "postgresql":
            database = PostgresDatabase.from_environment()
            unit_of_work_type = PostgresUnitOfWork
        else:
            raise RuntimeError(
                "DANTE_SQUASH_DATABASE deve ser 'postgresql' ou 'mariadb'."
            )
        database.initialize()
    except Exception as error:
        root.withdraw()
        messagebox.showerror("Falha ao iniciar", str(error))
        root.destroy()
        raise
    unit_of_work = lambda: unit_of_work_type(database)
    DanteSquashApp(
        root,
        CatalogService(unit_of_work),
        PaymentService(unit_of_work),
        SaunaService(unit_of_work),
        MonthlyBillingService(unit_of_work),
        ConsumptionService(unit_of_work),
    )
    root.mainloop()


if __name__ == "__main__":
    main()
