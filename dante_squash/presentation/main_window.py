"""Janela principal: reúne todas as abas do sistema."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from dante_squash.domain import SquashCalendar
from dante_squash.ports import Clock
from dante_squash.presentation.operation_tabs import (
    ConsumptionTab,
    MonthlyBillingTab,
    PaymentTab,
    SaunaTab,
)
from dante_squash.presentation.registration_tabs import (
    CustomerTab,
    DayGridTab,
    PricesTab,
    ProductTab,
    ReservationTab,
)
from dante_squash.presentation.report_tabs import (
    BackupTab,
    CashFlowTab,
    CustomerSheetTab,
    MonthlySummaryTab,
)
from dante_squash.presentation.widgets import ApplicationServices, UiToolkit


class MainWindow:
    def __init__(
        self,
        root: tk.Tk,
        services: ApplicationServices,
        kit: UiToolkit,
        clock: Clock,
        squash: SquashCalendar,
    ) -> None:
        self.root = root
        root.title("Dante Squash & Sauna")
        root.geometry("1100x760")
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.sauna = SaunaTab(self.tabs, services, kit, clock)
        self.day_grid = DayGridTab(self.tabs, services, kit, clock)
        self.reservations = ReservationTab(self.tabs, services, kit)
        self.monthly_billing = MonthlyBillingTab(self.tabs, services, kit, clock)
        self.customers = CustomerTab(self.tabs, services, kit)
        self.products = ProductTab(self.tabs, services, kit)
        self.prices = PricesTab(self.tabs, services, kit)
        self.consumptions = ConsumptionTab(self.tabs, services, kit, clock)
        self.payments = PaymentTab(self.tabs, services, kit, clock)
        self.customer_sheet = CustomerSheetTab(self.tabs, services, kit, squash)
        self.cash_flow = CashFlowTab(self.tabs, services, kit, clock)
        self.monthly_summary = MonthlySummaryTab(self.tabs, services, kit, clock)
        self.backup = BackupTab(self.tabs, services, kit)
        self._refreshable = {
            str(tab.frame): tab
            for tab in (self.sauna, self.reservations, self.customers, self.products, self.prices)
        }
        self.tabs.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, _event: object = None) -> None:
        """Recarrega a aba aberta, para mostrar alterações feitas em outras abas."""
        tab = self._refreshable.get(str(self.tabs.select()))
        if tab is not None:
            tab.refresh()
