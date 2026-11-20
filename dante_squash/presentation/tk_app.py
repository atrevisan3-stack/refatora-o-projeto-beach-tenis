"""Tkinter desktop interface; all business decisions remain in application services."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from dante_squash.domain import (
    BusinessRuleError,
    Customer,
    DueTier,
    PriceSchedule,
    Product,
    Reservation,
)
from dante_squash.services.catalog import CatalogService
from dante_squash.services.consumptions import ConsumptionService
from dante_squash.services.monthly_billing import MonthlyBillingService
from dante_squash.services.payments import PaymentService
from dante_squash.services.sauna import SaunaService

logger = logging.getLogger(__name__)


class DanteSquashApp:
    def __init__(
        self,
        root: tk.Tk,
        catalog: CatalogService,
        payments: PaymentService,
        sauna: SaunaService,
        monthly_billing: MonthlyBillingService,
        consumptions: ConsumptionService,
    ) -> None:
        self.root = root
        self.catalog = catalog
        self.payments = payments
        self.sauna = sauna
        self.monthly_billing = monthly_billing
        self.consumptions = consumptions
        root.title("Dante Squash & Sauna")
        root.geometry("1000x700")

        tabs = ttk.Notebook(root)
        tabs.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._customer_tab(tabs)
        self._product_tab(tabs)
        self._prices_tab(tabs)
        self._reservations_tab(tabs)
        self._payments_tab(tabs)
        self._sauna_tab(tabs)
        self._monthly_billing_tab(tabs)
        self._consumptions_tab(tabs)

    def _customer_tab(self, tabs: ttk.Notebook) -> None:
        frame = ttk.Frame(tabs, padding=12)
        tabs.add(frame, text="Clientes")
        self.customer_fields = self._form(
            frame,
            ("Nome", "CPF", "Data de aniversário (DDMMAAAA)", "Telefone"),
            row=0,
        )
        self.customer_code: int | None = None
        ttk.Button(frame, text="Salvar cliente", command=self._save_customer).grid(
            row=4, column=1, sticky="e", pady=6
        )
        self.customer_table = self._table(
            frame,
            ("Código", "Nome", "CPF", "Aniversário", "Telefone"),
            row=5,
        )
        self.customer_table.bind("<<TreeviewSelect>>", self._select_customer)
        self._refresh_customers()

    def _product_tab(self, tabs: ttk.Notebook) -> None:
        frame = ttk.Frame(tabs, padding=12)
        tabs.add(frame, text="Produtos")
        self.product_fields = self._form(frame, ("Descrição", "Preço", "Unidade"), row=0)
        self.product_code: int | None = None
        ttk.Button(frame, text="Salvar produto", command=self._save_product).grid(
            row=3, column=1, sticky="e", pady=6
        )
        self.product_table = self._table(frame, ("Código", "Descrição", "Preço", "Unidade"), row=4)
        self.product_table.bind("<<TreeviewSelect>>", self._select_product)
        self._refresh_products()

    def _prices_tab(self, tabs: ttk.Notebook) -> None:
        frame = ttk.Frame(tabs, padding=12)
        tabs.add(frame, text="Valores")
        labels = (
            "Valor da sauna",
            "Valor da aula de squash",
            "Vencimento 1",
            "Mensalidade 1",
            "Vencimento 2 (opcional)",
            "Mensalidade 2 (opcional)",
            "Vencimento 3 (opcional)",
            "Mensalidade 3 (opcional)",
        )
        self.price_fields = self._form(frame, labels, row=0)
        ttk.Button(frame, text="Salvar valores", command=self._save_prices).grid(
            row=len(labels), column=1, sticky="e", pady=6
        )
        self._load_prices()

    def _reservations_tab(self, tabs: ttk.Notebook) -> None:
        frame = ttk.Frame(tabs, padding=12)
        tabs.add(frame, text="Reservas de squash")
        self.reservation_fields = self._form(
            frame,
            ("Dia da semana (1=segunda, 6=sábado)", "Horário (HH:MM)", "Quadra (1 a 3)", "Códigos dos clientes (separados por vírgula)"),
            row=0,
        )
        self.game_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Jogo (desmarque para aula)", variable=self.game_var).grid(
            row=4, column=1, sticky="w", pady=4
        )
        ttk.Button(frame, text="Salvar reserva", command=self._save_reservation).grid(
            row=5, column=1, sticky="e", pady=6
        )
        self.reservation_table = self._table(
            frame, ("Dia", "Horário", "Quadra", "Tipo", "Clientes"), row=6
        )
        self._refresh_reservations()

    def _payments_tab(self, tabs: ttk.Notebook) -> None:
        frame = ttk.Frame(tabs, padding=12)
        tabs.add(frame, text="Pagamentos")
        self.payment_fields = self._form(
            frame,
            ("Código do cliente", "Data (AAAA-MM-DD)", "Valor pago", "Desconto"),
            row=0,
        )
        self.payment_fields[1].insert(0, date.today().isoformat())
        ttk.Button(frame, text="Consultar total", command=self._show_total_due).grid(
            row=4, column=0, sticky="w", pady=6
        )
        ttk.Button(frame, text="Registrar pagamento", command=self._settle_payment).grid(
            row=4, column=1, sticky="e", pady=6
        )

    def _sauna_tab(self, tabs: ttk.Notebook) -> None:
        frame = ttk.Frame(tabs, padding=12)
        tabs.add(frame, text="Sauna")
        self.sauna_name = ttk.Entry(frame, width=38)
        ttk.Label(frame, text="Nome do frequentador").grid(row=0, column=0, sticky="w", pady=3)
        self.sauna_name.grid(row=0, column=1, sticky="ew", pady=3)
        ttk.Button(frame, text="Registrar entrada", command=self._add_sauna_attendee).grid(
            row=0, column=2, padx=6
        )
        self.sauna_product_fields = self._form(
            frame,
            ("Código do produto", "Quantidade"),
            row=1,
        )
        ttk.Button(frame, text="Adicionar consumo", command=self._add_sauna_consumption).grid(
            row=3, column=1, sticky="e", pady=6
        )
        self.sauna_payment_fields = self._form(frame, ("Valor pago",), row=4)
        ttk.Button(frame, text="Fechar conta selecionada", command=self._close_sauna_account).grid(
            row=5, column=1, sticky="e", pady=6
        )
        self.sauna_table = self._table(
            frame, ("Frequentador", "Total", "Situação"), row=6
        )
        self.sauna_table.bind("<<TreeviewSelect>>", self._select_sauna_account)
        self._refresh_sauna_accounts()

    def _monthly_billing_tab(self, tabs: ttk.Notebook) -> None:
        frame = ttk.Frame(tabs, padding=12)
        tabs.add(frame, text="Mensalidades e multas")
        ttk.Label(frame, text="Data da geração (AAAA-MM-DD)").grid(
            row=0, column=0, sticky="w", pady=3
        )
        self.billing_date = ttk.Entry(frame, width=38)
        self.billing_date.insert(0, date.today().isoformat())
        self.billing_date.grid(row=0, column=1, sticky="ew", pady=3)
        ttk.Button(
            frame,
            text="Gerar mensalidades",
            command=self._generate_monthly_charges,
        ).grid(row=1, column=1, sticky="e", pady=6)
        ttk.Button(frame, text="Gerar multas", command=self._generate_fines).grid(
            row=2, column=1, sticky="e", pady=6
        )

    def _consumptions_tab(self, tabs: ttk.Notebook) -> None:
        frame = ttk.Frame(tabs, padding=12)
        tabs.add(frame, text="Consumos de clientes")
        self.consumption_fields = self._form(
            frame,
            ("Código do cliente", "Código do produto", "Quantidade", "Data (AAAA-MM-DD)"),
            row=0,
        )
        self.consumption_fields[3].insert(0, date.today().isoformat())
        ttk.Button(frame, text="Registrar consumo", command=self._register_consumption).grid(
            row=4, column=1, sticky="e", pady=6
        )

    @staticmethod
    def _form(
        parent: ttk.Frame,
        labels: tuple[str, ...],
        *,
        row: int,
    ) -> list[ttk.Entry]:
        fields: list[ttk.Entry] = []
        for offset, label in enumerate(labels):
            ttk.Label(parent, text=label).grid(row=row + offset, column=0, sticky="w", pady=3)
            entry = ttk.Entry(parent, width=38)
            entry.grid(row=row + offset, column=1, sticky="ew", pady=3)
            fields.append(entry)
        parent.columnconfigure(1, weight=1)
        return fields

    @staticmethod
    def _table(
        parent: ttk.Frame,
        columns: tuple[str, ...],
        *,
        row: int,
    ) -> ttk.Treeview:
        table = ttk.Treeview(parent, columns=columns, show="headings", height=14)
        for column in columns:
            table.heading(column, text=column)
            table.column(column, width=150, anchor="w")
        table.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=12)
        parent.rowconfigure(row, weight=1)
        return table

    @staticmethod
    def _replace_table(table: ttk.Treeview, rows: list[tuple[object, ...]]) -> None:
        table.delete(*table.get_children())
        for row in rows:
            table.insert("", tk.END, values=row)

    @staticmethod
    def _decimal(value: str) -> Decimal:
        try:
            return Decimal(value.strip().replace(",", "."))
        except InvalidOperation as error:
            raise BusinessRuleError("Informe um valor numérico válido.") from error

    @staticmethod
    def _integer(value: str) -> int:
        try:
            return int(value.strip())
        except ValueError as error:
            raise BusinessRuleError("Informe um número inteiro válido.") from error

    @staticmethod
    def _report_error(action: Callable[[], None]) -> None:
        try:
            action()
        except (BusinessRuleError, ValueError) as error:
            messagebox.showerror("Dante Squash & Sauna", str(error))
        except Exception as error:
            logger.exception("Falha na operação da interface")
            messagebox.showerror("Erro de operação", f"A operação falhou: {error}")

    def _save_customer(self) -> None:
        def action() -> None:
            name, cpf, birthday, phone = (field.get() for field in self.customer_fields)
            customer = self.catalog.save_customer(
                Customer(self.customer_code or 0, name, cpf, birthday, phone)
            )
            self.customer_code = None
            for field in self.customer_fields:
                field.delete(0, tk.END)
            self._refresh_customers()
            messagebox.showinfo("Cliente", f"Cliente {customer.code} salvo.")

        self._report_error(action)

    def _select_customer(self, _event: tk.Event) -> None:
        selected = self.customer_table.selection()
        if not selected:
            return
        values = self.customer_table.item(selected[0], "values")
        self.customer_code = int(values[0])
        for field, value in zip(self.customer_fields, values[1:]):
            field.delete(0, tk.END)
            field.insert(0, value)

    def _refresh_customers(self) -> None:
        self._replace_table(
            self.customer_table,
            [
                (item.code, item.name, item.cpf, item.birthday, item.phone)
                for item in self.catalog.customers()
                if item.code != 0
            ],
        )

    def _save_product(self) -> None:
        def action() -> None:
            description, price, unit = (field.get() for field in self.product_fields)
            product = self.catalog.save_product(
                Product(
                    self.product_code or 0,
                    description,
                    self._decimal(price),
                    unit,
                )
            )
            self.product_code = None
            for field in self.product_fields:
                field.delete(0, tk.END)
            self._refresh_products()
            messagebox.showinfo("Produto", f"Produto {product.code} salvo.")

        self._report_error(action)

    def _select_product(self, _event: tk.Event) -> None:
        selected = self.product_table.selection()
        if not selected:
            return
        values = self.product_table.item(selected[0], "values")
        self.product_code = int(values[0])
        for field, value in zip(self.product_fields, values[1:]):
            field.delete(0, tk.END)
            field.insert(0, value)

    def _refresh_products(self) -> None:
        self._replace_table(
            self.product_table,
            [
                (item.code, item.description, f"{item.price:.2f}", item.unit)
                for item in self.catalog.products()
                if item.code not in (0, 1)
            ],
        )

    def _load_prices(self) -> None:
        schedule = self.catalog.prices()
        if schedule is None:
            return
        fields = self.price_fields
        fields[0].insert(0, str(schedule.sauna_price))
        fields[1].insert(0, str(schedule.squash_lesson_price))
        for index, tier in enumerate(schedule.due_tiers):
            fields[2 + index * 2].insert(0, str(tier.day))
            fields[3 + index * 2].insert(0, str(tier.monthly_price))

    def _save_prices(self) -> None:
        def action() -> None:
            values = [field.get().strip() for field in self.price_fields]
            tiers: list[DueTier] = []
            for index in range(0, 6, 2):
                day_text, price_text = values[2 + index], values[3 + index]
                if not day_text and not price_text:
                    continue
                tiers.append(
                    DueTier(
                        self._integer(day_text) if day_text else 0,
                        self._decimal(price_text) if price_text else None,
                    )
                )
            self.catalog.save_prices(
                PriceSchedule(
                    self._decimal(values[0]),
                    self._decimal(values[1]),
                    tuple(tiers),
                )
            )
            messagebox.showinfo("Valores", "Tabela de valores salva.")

        self._report_error(action)

    def _save_reservation(self) -> None:
        def action() -> None:
            weekday, time, court, customer_ids = (
                field.get().strip() for field in self.reservation_fields
            )
            reservation = Reservation(
                weekday=self._integer(weekday),
                time=time,
                court=self._integer(court),
                is_game=self.game_var.get(),
                customer_ids=tuple(self._integer(code) for code in customer_ids.split(",")),
            )
            has_conflict = any(
                item.weekday == reservation.weekday
                and item.time == reservation.time
                and item.court == reservation.court
                for item in self.catalog.reservations()
            )
            replace_existing = not has_conflict or messagebox.askyesno(
                "Substituir reserva",
                "Já existe uma reserva para este horário. Deseja substituí-la?",
            )
            self.catalog.save_reservation(
                reservation,
                replace_existing=replace_existing,
            )
            self._refresh_reservations()
            messagebox.showinfo("Squash", "Reserva salva.")

        self._report_error(action)

    def _refresh_reservations(self) -> None:
        self._replace_table(
            self.reservation_table,
            [
                (
                    item.weekday,
                    item.time,
                    item.court,
                    "Jogo" if item.is_game else "Aula",
                    ", ".join(str(code) for code in item.customer_ids),
                )
                for item in self.catalog.reservations()
            ],
        )

    def _show_total_due(self) -> None:
        def action() -> None:
            customer_id = self._integer(self.payment_fields[0].get())
            total = self.payments.total_due(customer_id)
            messagebox.showinfo("Pagamento", f"Total em aberto: R$ {total:.2f}")

        self._report_error(action)

    def _settle_payment(self) -> None:
        def action() -> None:
            customer_id = self._integer(self.payment_fields[0].get())
            payment_date = date.fromisoformat(self.payment_fields[1].get().strip())
            result = self.payments.settle(
                customer_id=customer_id,
                payment_date=payment_date,
                amount_paid=self._decimal(self.payment_fields[2].get()),
                discount=self._decimal(self.payment_fields[3].get() or "0"),
            )
            status = "integral" if result.paid_in_full else "parcial"
            messagebox.showinfo(
                "Pagamento",
                f"Pagamento {status} registrado. Saldo: R$ {result.balance:.2f}",
            )

        self._report_error(action)

    def _add_sauna_attendee(self) -> None:
        def action() -> None:
            self.sauna.add_attendee(self.sauna_name.get(), date.today())
            self.sauna_name.delete(0, tk.END)
            self._refresh_sauna_accounts()

        self._report_error(action)

    def _add_sauna_consumption(self) -> None:
        def action() -> None:
            name = self._selected_sauna_name()
            self.sauna.add_product_consumption(
                name=name,
                account_date=date.today(),
                product_code=self._integer(self.sauna_product_fields[0].get()),
                quantity=self._integer(self.sauna_product_fields[1].get()),
            )
            self._refresh_sauna_accounts()

        self._report_error(action)

    def _close_sauna_account(self) -> None:
        def action() -> None:
            self.sauna.close_account(
                self._selected_sauna_name(),
                date.today(),
                self._decimal(self.sauna_payment_fields[0].get()),
            )
            self._refresh_sauna_accounts()

        self._report_error(action)

    def _select_sauna_account(self, _event: tk.Event) -> None:
        selected = self.sauna_table.selection()
        if selected:
            self.sauna_name.delete(0, tk.END)
            self.sauna_name.insert(0, self.sauna_table.item(selected[0], "values")[0])

    def _selected_sauna_name(self) -> str:
        selected = self.sauna_table.selection()
        if not selected:
            raise BusinessRuleError("Selecione um frequentador da sauna.")
        return str(self.sauna_table.item(selected[0], "values")[0])

    def _refresh_sauna_accounts(self) -> None:
        accounts = self.sauna.accounts(date.today())
        self._replace_table(
            self.sauna_table,
            [
                (
                    account.name,
                    f"{sum((item.total for item in account.consumptions), Decimal('0')):.2f}",
                    "Encerrada" if account.closed else "Em aberto",
                )
                for account in accounts
            ],
        )

    def _generate_monthly_charges(self) -> None:
        def action() -> None:
            generated = self.monthly_billing.generate_monthly_charges(
                date.fromisoformat(self.billing_date.get().strip())
            )
            messagebox.showinfo("Mensalidades", f"{generated} mensalidade(s) gerada(s).")

        self._report_error(action)

    def _generate_fines(self) -> None:
        def action() -> None:
            generated = self.monthly_billing.generate_fines(
                date.fromisoformat(self.billing_date.get().strip())
            )
            messagebox.showinfo("Multas", f"{generated} multa(s) gerada(s).")

        self._report_error(action)

    def _register_consumption(self) -> None:
        def action() -> None:
            fields = self.consumption_fields
            item = self.consumptions.register(
                customer_id=self._integer(fields[0].get()),
                product_code=self._integer(fields[1].get()),
                quantity=self._integer(fields[2].get()),
                consumption_date=date.fromisoformat(fields[3].get().strip()),
            )
            messagebox.showinfo(
                "Consumo",
                f"Consumo registrado. Total: R$ {item.total:.2f}",
            )

        self._report_error(action)
