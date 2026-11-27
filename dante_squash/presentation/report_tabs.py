"""Abas de consulta: ficha do cliente, fluxo de caixa, resumo mensal e backup."""

from __future__ import annotations

from pathlib import Path
from tkinter import ttk

from dante_squash.domain import SquashCalendar
from dante_squash.ports import Clock
from dante_squash.presentation.widgets import ApplicationServices, UiToolkit


class CustomerSheetTab:
    """RF13: reservas, total devido e histórico de consumos do cliente."""

    def __init__(
        self,
        tabs: ttk.Notebook,
        services: ApplicationServices,
        kit: UiToolkit,
        squash: SquashCalendar,
    ) -> None:
        self._services = services
        self._kit = kit
        self._squash = squash
        self.frame = ttk.Frame(tabs, padding=12)
        tabs.add(self.frame, text="Ficha do cliente")
        w = kit.widgets
        self.customer = w.lookup(self.frame, "Cliente", lambda: [(c.code, c.name) for c in services.catalog.customers()], row=0)
        self.show_button = w.button(self.frame, "Mostrar ficha", self.show, row=1, column=1)
        self.summary = ttk.Label(self.frame, text="")
        self.summary.grid(row=2, column=0, columnspan=4, sticky="w")
        self.reservations = w.table(self.frame, ("Dia", "Horário", "Quadra", "Tipo"), row=3, height=5)
        self.history = w.table(
            self.frame, ("Data", "Seq.", "Produto", "Qtd.", "Total", "Pago"), row=4, height=10
        )

    def show(self) -> None:
        def action() -> None:
            parser = self._kit.parser
            sheet = self._services.reports.customer_sheet(
                parser.code(self.customer.get(), "Cliente")
            )
            self.summary.configure(
                text=f"{sheet.customer.name} — total devido: R$ {parser.money_text(sheet.total_due)}"
            )
            self._kit.widgets.replace_rows(
                self.reservations,
                [
                    (
                        f"{r.weekday}|{r.time}|{r.court}",
                        (self._squash.weekday_names[r.weekday], r.time, r.court,
                         "Jogo" if r.is_game else "Aula"),
                    )
                    for r in sheet.reservations
                ],
            )
            self._kit.widgets.replace_rows(
                self.history,
                [
                    (
                        f"{parser.date_text(c.date)}|{c.sequence}",
                        (parser.date_text(c.date), c.sequence, description, c.quantity,
                         parser.money_text(c.total), "Sim" if c.paid else "Não"),
                    )
                    for c, description in sheet.history
                ],
            )

        self._kit.runner.run(action)


class CashFlowTab:
    """RF14: valores pagos e não pagos de sauna, squash e produtos no dia."""

    def __init__(
        self, tabs: ttk.Notebook, services: ApplicationServices, kit: UiToolkit, clock: Clock
    ) -> None:
        self._services = services
        self._kit = kit
        self.frame = ttk.Frame(tabs, padding=12)
        tabs.add(self.frame, text="Fluxo de caixa")
        w = kit.widgets
        (self.day,) = w.form(self.frame, ("Data (DD/MM/AAAA)",), row=0)
        w.set_text(self.day, kit.parser.date_text(clock.today()))
        self.show_button = w.button(self.frame, "Mostrar caixa", self.show, row=1, column=1)
        self.table = w.table(self.frame, ("Categoria", "Pago", "Não pago", "Total"), row=2, height=5)

    def show(self) -> None:
        def action() -> None:
            parser = self._kit.parser
            lines = self._services.reports.cash_flow(parser.day(self.day.get(), "Data"))
            rows = [
                (line.category, (line.category, parser.money_text(line.paid),
                                 parser.money_text(line.unpaid), parser.money_text(line.sold)))
                for line in lines
            ]
            paid = sum((line.paid for line in lines), 0)
            unpaid = sum((line.unpaid for line in lines), 0)
            rows.append(
                ("total", ("Total", parser.money_text(paid), parser.money_text(unpaid),
                           parser.money_text(paid + unpaid)))
            )
            self._kit.widgets.replace_rows(self.table, rows)

        self._kit.runner.run(action)


class MonthlySummaryTab:
    """RF15: vendido e pago por dia do mês, a receber e totais."""

    def __init__(
        self, tabs: ttk.Notebook, services: ApplicationServices, kit: UiToolkit, clock: Clock
    ) -> None:
        self._services = services
        self._kit = kit
        self.frame = ttk.Frame(tabs, padding=12)
        tabs.add(self.frame, text="Resumo mensal")
        w = kit.widgets
        self.month, self.year = w.form(self.frame, ("Mês (1 a 12)", "Ano"), row=0)
        today = clock.today()
        w.set_text(self.month, str(today.month))
        w.set_text(self.year, str(today.year))
        self.show_button = w.button(self.frame, "Mostrar resumo", self.show, row=2, column=1)
        self.table = w.table(
            self.frame,
            ("Dia", "Sauna", "Squash", "Produtos", "Vendido", "Pago", "A receber"),
            row=3,
            height=16,
        )

    def show(self) -> None:
        def action() -> None:
            parser = self._kit.parser
            days = self._services.reports.monthly_summary(
                parser.integer(self.year.get(), "Ano"), parser.integer(self.month.get(), "Mês")
            )
            rows = []
            for summary in days:
                sold = {line.category: line.sold for line in summary.lines}
                rows.append(
                    (
                        str(summary.day.day),
                        (summary.day.day, parser.money_text(sold["Sauna"]),
                         parser.money_text(sold["Squash"]), parser.money_text(sold["Produtos"]),
                         parser.money_text(summary.sold), parser.money_text(summary.paid),
                         parser.money_text(summary.to_receive)),
                    )
                )
            total_sold = sum((d.sold for d in days), 0)
            total_paid = sum((d.paid for d in days), 0)
            rows.append(
                ("total", ("Total", "", "", "", parser.money_text(total_sold),
                           parser.money_text(total_paid), parser.money_text(total_sold - total_paid)))
            )
            self._kit.widgets.replace_rows(self.table, rows)

        self._kit.runner.run(action)


class BackupTab:
    """RF16: exporta as oito tabelas para arquivos CSV."""

    def __init__(self, tabs: ttk.Notebook, services: ApplicationServices, kit: UiToolkit) -> None:
        self._services = services
        self._kit = kit
        self.frame = ttk.Frame(tabs, padding=12)
        tabs.add(self.frame, text="Backup")
        ttk.Label(
            self.frame, text="Exporta todas as tabelas para arquivos .csv na pasta escolhida."
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        self.backup_button = kit.widgets.button(self.frame, "Fazer backup", self.backup, row=1, column=0)

    def backup(self) -> None:
        def action() -> None:
            folder = self._kit.dialogs.choose_directory("Pasta do backup")
            if not folder:
                return
            files = self._services.backup.export(Path(folder))
            self._kit.dialogs.info("Backup", f"{len(files)} tabela(s) exportada(s) para {folder}.")

        self._kit.runner.run(action)
