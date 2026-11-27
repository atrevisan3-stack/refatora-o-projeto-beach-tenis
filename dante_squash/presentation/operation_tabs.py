"""Abas de operação: consumos, pagamentos, sauna e mensalidades/multas."""

from __future__ import annotations

from tkinter import ttk

from dante_squash.ports import Clock
from dante_squash.presentation.widgets import ApplicationServices, UiToolkit


class ConsumptionTab:
    """RF04: registrar, listar e excluir consumos de clientes cadastrados."""

    def __init__(
        self, tabs: ttk.Notebook, services: ApplicationServices, kit: UiToolkit, clock: Clock
    ) -> None:
        self._services = services
        self._kit = kit
        self.frame = ttk.Frame(tabs, padding=12)
        tabs.add(self.frame, text="Consumos")
        w = kit.widgets
        self.customer = w.lookup(self.frame, "Cliente", lambda: [(c.code, c.name) for c in services.catalog.customers()], row=0)
        self.product = w.lookup(self.frame, "Produto", lambda: [(p.code, p.description) for p in services.catalog.products()], row=1)
        self.quantity, self.day = w.form(self.frame, ("Quantidade", "Data (DD/MM/AAAA)"), row=2)
        w.set_text(self.day, kit.parser.date_text(clock.today()))
        self.register_button = w.button(self.frame, "Registrar consumo", self.register, row=4, column=1)
        self.list_button = w.button(self.frame, "Listar consumos", self.refresh, row=4, column=0)
        self.delete_button = w.button(self.frame, "Excluir consumo", self.delete, row=4, column=2)
        self.table = w.table(
            self.frame, ("Data", "Seq.", "Produto", "Qtd.", "Valor", "Total", "Pago"), row=5
        )

    def register(self) -> None:
        def action() -> None:
            parser = self._kit.parser
            item = self._services.consumptions.register(
                customer_id=parser.code(self.customer.get(), "Cliente"),
                product_code=parser.code(self.product.get(), "Produto"),
                quantity=parser.integer(self.quantity.get(), "Quantidade"),
                consumption_date=parser.day(self.day.get(), "Data"),
            )
            self._load(item.customer_id)
            self._kit.dialogs.info(
                "Consumos", f"Consumo registrado. Total: R$ {parser.money_text(item.total)}"
            )

        self._kit.runner.run(action)

    def refresh(self) -> None:
        self._kit.runner.run(
            lambda: self._load(self._kit.parser.code(self.customer.get(), "Cliente"))
        )

    def delete(self) -> None:
        def action() -> None:
            parser = self._kit.parser
            key = self._kit.widgets.selected_key(self.table, "Selecione um consumo.")
            customer_id, day_text, sequence = key.split("|")
            if not self._kit.dialogs.confirm("Consumos", "Deseja excluir o consumo selecionado?"):
                return
            self._services.consumptions.delete(
                int(customer_id), parser.day(day_text, "Data"), int(sequence)
            )
            self._load(int(customer_id))

        self._kit.runner.run(action)

    def _load(self, customer_id: int) -> None:
        parser = self._kit.parser
        products = self._services.catalog.product_names()
        self._kit.widgets.replace_rows(
            self.table,
            [
                (
                    f"{c.customer_id}|{parser.date_text(c.date)}|{c.sequence}",
                    (
                        parser.date_text(c.date), c.sequence,
                        parser.option_text(c.product_code, products), c.quantity,
                        parser.money_text(c.unit_price), parser.money_text(c.total),
                        "Sim" if c.paid else "Não",
                    ),
                )
                for c in self._services.consumptions.for_customer(customer_id)
            ],
        )


class PaymentTab:
    """RF05: total em aberto e pagamento total, parcial ou com desconto."""

    def __init__(
        self, tabs: ttk.Notebook, services: ApplicationServices, kit: UiToolkit, clock: Clock
    ) -> None:
        self._services = services
        self._kit = kit
        self.frame = ttk.Frame(tabs, padding=12)
        tabs.add(self.frame, text="Pagamentos")
        w = kit.widgets
        self.customer = w.lookup(self.frame, "Cliente", lambda: [(c.code, c.name) for c in services.catalog.customers()], row=0)
        self.day, self.amount, self.discount = w.form(
            self.frame, ("Data (DD/MM/AAAA)", "Valor pago (R$)", "Desconto (R$)"), row=1
        )
        w.set_text(self.day, kit.parser.date_text(clock.today()))
        self.total_label = ttk.Label(self.frame, text="Total em aberto: -")
        self.total_label.grid(row=4, column=1, sticky="w")
        self.total_button = w.button(self.frame, "Consultar total", self.show_total, row=5, column=0)
        self.pay_button = w.button(self.frame, "Registrar pagamento", self.pay, row=5, column=1)

    def show_total(self) -> None:
        def action() -> None:
            parser = self._kit.parser
            total = self._services.payments.total_due(
                parser.code(self.customer.get(), "Cliente")
            )
            self.total_label.configure(text=f"Total em aberto: R$ {parser.money_text(total)}")

        self._kit.runner.run(action)

    def pay(self) -> None:
        def action() -> None:
            parser = self._kit.parser
            customer_id = parser.code(self.customer.get(), "Cliente")
            amount = parser.decimal(self.amount.get(), "Valor pago")
            discount = parser.optional_decimal(self.discount.get(), "Desconto")
            total = self._services.payments.total_due(customer_id)
            if amount + discount < total and not self._kit.dialogs.confirm(
                "Pagamentos",
                "O valor pago é menor que o total. Confirma o pagamento parcial?",
            ):
                return
            result = self._services.payments.settle(
                customer_id=customer_id,
                payment_date=parser.day(self.day.get(), "Data"),
                amount_paid=amount,
                discount=discount,
            )
            kind = "total" if result.paid_in_full else "parcial"
            self._kit.dialogs.info(
                "Pagamentos",
                f"Pagamento {kind} registrado. Saldo: R$ {parser.money_text(result.balance)}",
            )
            self.show_total()

        self._kit.runner.run(action)


class SaunaTab:
    """RF06 a RF08: frequentadores do dia, consumo e fechamento de conta."""

    def __init__(
        self, tabs: ttk.Notebook, services: ApplicationServices, kit: UiToolkit, clock: Clock
    ) -> None:
        self._services = services
        self._kit = kit
        self._clock = clock
        self._accounts: dict = {}
        self.frame = ttk.Frame(tabs, padding=12)
        tabs.add(self.frame, text="Sauna")
        w = kit.widgets
        (self.day,) = w.form(self.frame, ("Data (DD/MM/AAAA)",), row=0)
        w.set_text(self.day, kit.parser.date_text(clock.today()))
        (self.name,) = w.form(self.frame, ("Nome do frequentador",), row=1)
        self.show_button = w.button(self.frame, "Mostrar dia", self.refresh, row=2, column=0)
        self.add_button = w.button(self.frame, "Adicionar frequentador", self.add_attendee, row=2, column=1)
        self.remove_button = w.button(self.frame, "Excluir frequentador", self.remove_attendee, row=2, column=2)
        self.accounts = w.table(self.frame, ("Frequentador", "Total", "Situação"), row=3, height=6)
        self.accounts.bind("<<TreeviewSelect>>", self.select_account)
        self.product = w.lookup(self.frame, "Produto", lambda: [(p.code, p.description) for p in services.catalog.products()], row=4)
        (self.quantity,) = w.form(self.frame, ("Quantidade",), row=5)
        self.consume_button = w.button(self.frame, "Adicionar consumo", self.add_consumption, row=6, column=1)
        self.remove_item_button = w.button(self.frame, "Excluir consumo", self.remove_consumption, row=6, column=2)
        self.items = w.table(self.frame, ("Seq.", "Produto", "Qtd.", "Valor", "Total"), row=7, height=6)
        (self.amount,) = w.form(self.frame, ("Valor pago (R$)",), row=8)
        self.close_button = w.button(self.frame, "Fechar conta", self.close_account, row=9, column=1)
        self.refresh()

    def _date(self):
        return self._kit.parser.day(self.day.get(), "Data")

    def _selected_name(self) -> str:
        return self._kit.widgets.selected_key(self.accounts, "Selecione um frequentador.")

    def add_attendee(self) -> None:
        def action() -> None:
            self._services.sauna.add_attendee(self.name.get(), self._date())
            self._kit.widgets.clear((self.name,))
            self.refresh()

        self._kit.runner.run(action)

    def remove_attendee(self) -> None:
        def action() -> None:
            name = self._selected_name()
            if not self._kit.dialogs.confirm("Sauna", f"Deseja excluir o frequentador {name}?"):
                return
            self._services.sauna.remove_attendee(name, self._date())
            self.refresh()

        self._kit.runner.run(action)

    def add_consumption(self) -> None:
        def action() -> None:
            parser = self._kit.parser
            name = self._selected_name()
            self._services.sauna.add_product_consumption(
                name=name,
                account_date=self._date(),
                product_code=parser.code(self.product.get(), "Produto"),
                quantity=parser.integer(self.quantity.get(), "Quantidade"),
            )
            self.refresh(select=name)

        self._kit.runner.run(action)

    def remove_consumption(self) -> None:
        def action() -> None:
            name = self._selected_name()
            sequence = int(self._kit.widgets.selected_key(self.items, "Selecione um consumo."))
            self._services.sauna.remove_product_consumption(name, self._date(), sequence)
            self.refresh(select=name)

        self._kit.runner.run(action)

    def close_account(self) -> None:
        def action() -> None:
            name = self._selected_name()
            amount = self._kit.parser.decimal(self.amount.get(), "Valor pago")
            self._services.sauna.close_account(name, self._date(), amount)
            self._kit.widgets.clear((self.amount,))
            self.refresh(select=name)
            self._kit.dialogs.info("Sauna", f"Conta de {name} encerrada.")

        self._kit.runner.run(action)

    def refresh(self, select: str | None = None) -> None:
        def action() -> None:
            parser = self._kit.parser
            self._accounts = {a.name: a for a in self._services.sauna.accounts(self._date())}
            self._kit.widgets.replace_rows(
                self.accounts,
                [
                    (
                        a.name,
                        (a.name, parser.money_text(a.total), "Encerrada" if a.closed else "Aberta"),
                    )
                    for a in self._accounts.values()
                ],
            )
            if select in self._accounts:
                self.accounts.selection_set(select)
                self.select_account()
            else:
                self._kit.widgets.replace_rows(self.items, [])

        self._kit.runner.run(action)

    def select_account(self, _event: object = None) -> None:
        selection = self.accounts.selection()
        if not selection:
            return
        parser = self._kit.parser
        account = self._accounts.get(str(selection[0]))
        if account is None:
            return
        products = self._services.catalog.product_names()
        self._kit.widgets.replace_rows(
            self.items,
            [
                (
                    str(c.sequence),
                    (c.sequence, parser.option_text(c.product_code, products), c.quantity,
                     parser.money_text(c.unit_price), parser.money_text(c.total)),
                )
                for c in account.consumptions
            ],
        )


class MonthlyBillingTab:
    """RF11 e RF12: gerar mensalidades e multas e listar o que foi gerado."""

    def __init__(
        self, tabs: ttk.Notebook, services: ApplicationServices, kit: UiToolkit, clock: Clock
    ) -> None:
        self._services = services
        self._kit = kit
        self.frame = ttk.Frame(tabs, padding=12)
        tabs.add(self.frame, text="Mensalidades e multas")
        w = kit.widgets
        (self.day,) = w.form(self.frame, ("Data da geração (DD/MM/AAAA)",), row=0)
        w.set_text(self.day, kit.parser.date_text(clock.today()))
        self.charges_button = w.button(self.frame, "Gerar mensalidades", self.generate_charges, row=1, column=0)
        self.fines_button = w.button(self.frame, "Gerar multas", self.generate_fines, row=1, column=1)
        self.table = w.table(self.frame, ("Cliente", "Produto", "Valor"), row=2)

    def generate_charges(self) -> None:
        self._generate(self._services.monthly_billing.generate_monthly_charges, "mensalidade(s)")

    def generate_fines(self) -> None:
        self._generate(self._services.monthly_billing.generate_fines, "multa(s)")

    def _generate(self, operation, label: str) -> None:
        def action() -> None:
            parser = self._kit.parser
            generated = operation(parser.day(self.day.get(), "Data"))
            customers = self._services.catalog.customer_names()
            products = self._services.catalog.product_names()
            self._kit.widgets.replace_rows(
                self.table,
                [
                    (
                        f"{c.customer_id}|{c.sequence}",
                        (parser.option_text(c.customer_id, customers),
                         parser.option_text(c.product_code, products),
                         parser.money_text(c.unit_price)),
                    )
                    for c in generated
                ],
            )
            self._kit.dialogs.info("Squash", f"{len(generated)} {label} gerada(s).")

        self._kit.runner.run(action)
