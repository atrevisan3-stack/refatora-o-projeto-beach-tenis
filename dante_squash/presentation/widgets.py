"""Peças reutilizáveis da interface: diálogos, conversão de valores e widgets.

Os diálogos são injetados na aplicação; nos testes de interface eles são
substituídos por um objeto que apenas registra as mensagens.
"""

from __future__ import annotations

import logging
import tkinter as tk
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Sequence

from dante_squash.domain import BusinessRuleError
from dante_squash.services.application_services import ApplicationServices


class TkDialogs:
    """Diálogos reais do Tkinter."""

    def info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)

    def error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)

    def confirm(self, title: str, message: str) -> bool:
        return bool(messagebox.askyesno(title, message))

    def choose_directory(self, title: str) -> str:
        return filedialog.askdirectory(title=title) or ""


class ValueParser:
    """Converte o texto digitado em valores, com mensagens de erro claras."""

    def decimal(self, text: str, field: str) -> Decimal:
        try:
            value = Decimal(text.strip().replace(",", "."))
        except InvalidOperation as error:
            raise BusinessRuleError(f"Informe um valor numérico válido em {field}.") from error
        if not value.is_finite():
            raise BusinessRuleError(f"Informe um valor numérico válido em {field}.")
        return value

    def optional_decimal(self, text: str, field: str) -> Decimal:
        return self.decimal(text, field) if text.strip() else Decimal("0")

    def integer(self, text: str, field: str) -> int:
        try:
            return int(text.strip())
        except ValueError as error:
            raise BusinessRuleError(f"Informe um número inteiro em {field}.") from error

    def day(self, text: str, field: str) -> date:
        cleaned = text.strip()
        for pattern in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(cleaned, pattern).date()
            except ValueError:
                continue
        raise BusinessRuleError(f"Informe a data em {field} no formato DD/MM/AAAA.")

    def money_text(self, value: Decimal) -> str:
        return f"{value:.2f}".replace(".", ",")

    def date_text(self, value: date) -> str:
        return value.strftime("%d/%m/%Y")


class ActionRunner:
    """Executa a ação de um botão e mostra o erro de regra de negócio, se houver."""

    def __init__(self, dialogs: TkDialogs, logger: logging.Logger) -> None:
        self._dialogs = dialogs
        self._logger = logger

    def run(self, action: Callable[[], None]) -> None:
        try:
            action()
        except BusinessRuleError as error:
            self._dialogs.error("Dante Squash & Sauna", str(error))
        except Exception as error:  # falha inesperada (ex.: banco fora do ar)
            self._logger.exception("Falha na operação da interface")
            self._dialogs.error("Erro de operação", f"A operação falhou: {error}")


class WidgetFactory:
    """Monta formulários e tabelas com o mesmo padrão visual."""

    def form(self, parent: ttk.Frame, labels: Sequence[str], *, row: int) -> list[ttk.Entry]:
        fields: list[ttk.Entry] = []
        for offset, label in enumerate(labels):
            ttk.Label(parent, text=label).grid(row=row + offset, column=0, sticky="w", pady=3)
            entry = ttk.Entry(parent, width=40)
            entry.grid(row=row + offset, column=1, sticky="ew", pady=3)
            fields.append(entry)
        parent.columnconfigure(1, weight=1)
        return fields

    def button(
        self, parent: ttk.Frame, text: str, command: Callable[[], None], *, row: int, column: int
    ) -> ttk.Button:
        button = ttk.Button(parent, text=text, command=command)
        button.grid(row=row, column=column, sticky="ew", padx=4, pady=6)
        return button

    def table(
        self, parent: ttk.Frame, columns: Sequence[str], *, row: int, height: int = 12
    ) -> ttk.Treeview:
        table = ttk.Treeview(parent, columns=tuple(columns), show="headings", height=height)
        for column in columns:
            table.heading(column, text=column)
            table.column(column, width=130, anchor="w")
        table.grid(row=row, column=0, columnspan=4, sticky="nsew", pady=10)
        parent.rowconfigure(row, weight=1)
        return table

    def replace_rows(self, table: ttk.Treeview, rows: Sequence[tuple[str, tuple[object, ...]]]) -> None:
        """Troca as linhas da tabela; cada linha é (chave, valores)."""
        table.delete(*table.get_children())
        for key, values in rows:
            table.insert("", tk.END, iid=key, values=values)

    def set_text(self, entry: ttk.Entry, text: str) -> None:
        entry.delete(0, tk.END)
        entry.insert(0, text)

    def clear(self, entries: Sequence[ttk.Entry]) -> None:
        for entry in entries:
            entry.delete(0, tk.END)

    def selected_key(self, table: ttk.Treeview, message: str) -> str:
        selection = table.selection()
        if not selection:
            raise BusinessRuleError(message)
        return str(selection[0])


@dataclass(frozen=True)
class UiToolkit:
    """Dependências compartilhadas por todas as abas."""

    dialogs: TkDialogs
    parser: ValueParser
    widgets: WidgetFactory
    runner: ActionRunner
