"""Abas de cadastro: clientes, produtos, valores e reservas de squash."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import ttk

from dante_squash.domain import (
    Customer,
    DueTier,
    PriceSchedule,
    Product,
    Reservation,
    SquashCalendar,
)
from dante_squash.ports import Clock
from dante_squash.presentation.widgets import ApplicationServices, UiToolkit


class CustomerTab:
    """RF01: incluir, alterar, excluir e listar clientes."""

    def __init__(self, tabs: ttk.Notebook, services: ApplicationServices, kit: UiToolkit) -> None:
        self._services = services
        self._kit = kit
        self.frame = ttk.Frame(tabs, padding=12)
        tabs.add(self.frame, text="Clientes")
        w = kit.widgets
        self.name, self.cpf, self.birthday, self.phone = w.form(
            self.frame, ("Nome", "CPF", "Aniversário (DDMMAAAA)", "Telefone"), row=0
        )
        self.code: int | None = None
        self.save_button = w.button(self.frame, "Salvar cliente", self.save, row=4, column=1)
        self.new_button = w.button(self.frame, "Novo", self.new, row=4, column=0)
        self.delete_button = w.button(self.frame, "Excluir cliente", self.delete, row=4, column=2)
        self.table = w.table(self.frame, ("Código", "Nome", "CPF", "Aniversário", "Telefone"), row=5)
        self.table.bind("<<TreeviewSelect>>", self.select)
        self.refresh()

    def save(self) -> None:
        def action() -> None:
            customer = self._services.catalog.save_customer(
                Customer(self.code, self.name.get(), self.cpf.get(), self.birthday.get(), self.phone.get())
            )
            self.new()
            self.refresh()
            self._kit.dialogs.info("Clientes", f"Cliente {customer.code} salvo com sucesso!")

        self._kit.runner.run(action)

    def delete(self) -> None:
        def action() -> None:
            code = int(self._kit.widgets.selected_key(self.table, "Selecione um cliente."))
            if not self._kit.dialogs.confirm("Clientes", "Deseja excluir o cliente selecionado?"):
                return
            self._services.catalog.delete_customer(code)
            self.new()
            self.refresh()
            self._kit.dialogs.info("Clientes", "Cliente excluído com sucesso!")

        self._kit.runner.run(action)

    def new(self) -> None:
        self.code = None
        self._kit.widgets.clear((self.name, self.cpf, self.birthday, self.phone))

    def select(self, _event: object = None) -> None:
        selection = self.table.selection()
        if not selection:
            return
        values = self.table.item(selection[0], "values")
        self.code = int(values[0])
        for entry, value in zip((self.name, self.cpf, self.birthday, self.phone), values[1:]):
            self._kit.widgets.set_text(entry, str(value))

    def refresh(self) -> None:
        self._kit.widgets.replace_rows(
            self.table,
            [
                (str(c.code), (c.code, c.name, c.cpf, c.birthday, c.phone))
                for c in self._services.catalog.customers()
            ],
        )


class ProductTab:
    """RF02: incluir, alterar, excluir e listar produtos."""

    def __init__(self, tabs: ttk.Notebook, services: ApplicationServices, kit: UiToolkit) -> None:
        self._services = services
        self._kit = kit
        self.frame = ttk.Frame(tabs, padding=12)
        tabs.add(self.frame, text="Produtos")
        w = kit.widgets
        self.description, self.price, self.unit = w.form(
            self.frame, ("Descrição", "Preço (R$)", "Unidade"), row=0
        )
        self.code: int | None = None
        self.new_button = w.button(self.frame, "Novo", self.new, row=3, column=0)
        self.save_button = w.button(self.frame, "Salvar produto", self.save, row=3, column=1)
        self.delete_button = w.button(self.frame, "Excluir produto", self.delete, row=3, column=2)
        self.table = w.table(self.frame, ("Código", "Descrição", "Preço", "Unidade"), row=4)
        self.table.bind("<<TreeviewSelect>>", self.select)
        self.refresh()

    def save(self) -> None:
        def action() -> None:
            price = self._kit.parser.decimal(self.price.get(), "Preço")
            product = self._services.catalog.save_product(
                Product(self.code, self.description.get(), price, self.unit.get())
            )
            self.new()
            self.refresh()
            self._kit.dialogs.info("Produtos", f"Produto {product.code} salvo com sucesso!")

        self._kit.runner.run(action)

    def delete(self) -> None:
        def action() -> None:
            code = int(self._kit.widgets.selected_key(self.table, "Selecione um produto."))
            if not self._kit.dialogs.confirm("Produtos", "Deseja excluir o produto selecionado?"):
                return
            self._services.catalog.delete_product(code)
            self.new()
            self.refresh()
            self._kit.dialogs.info("Produtos", "Produto excluído com sucesso!")

        self._kit.runner.run(action)

    def new(self) -> None:
        self.code = None
        self._kit.widgets.clear((self.description, self.price, self.unit))

    def select(self, _event: object = None) -> None:
        selection = self.table.selection()
        if not selection:
            return
        values = self.table.item(selection[0], "values")
        self.code = int(values[0])
        for entry, value in zip((self.description, self.price, self.unit), values[1:]):
            self._kit.widgets.set_text(entry, str(value))

    def refresh(self) -> None:
        money = self._kit.parser.money_text
        self._kit.widgets.replace_rows(
            self.table,
            [
                (str(p.code), (p.code, p.description, money(p.price), p.unit))
                for p in self._services.catalog.products()
            ],
        )


class PricesTab:
    """RF03: valor da sauna, da aula e até três faixas de vencimento."""

    def __init__(self, tabs: ttk.Notebook, services: ApplicationServices, kit: UiToolkit) -> None:
        self._services = services
        self._kit = kit
        self.frame = ttk.Frame(tabs, padding=12)
        tabs.add(self.frame, text="Valores")
        labels = (
            "Valor da sauna", "Valor da aula de squash",
            "Vencimento 1 (dia)", "Valor mensal 1",
            "Vencimento 2 (dia, opcional)", "Valor mensal 2 (opcional)",
            "Vencimento 3 (dia, opcional)", "Valor mensal 3 (opcional)",
        )
        self.fields = kit.widgets.form(self.frame, labels, row=0)
        self.save_button = kit.widgets.button(self.frame, "Salvar valores", self.save, row=8, column=1)
        self.refresh()

    def refresh(self) -> None:
        schedule = self._services.catalog.prices()
        if schedule is None:
            return
        texts = [str(schedule.sauna_price), str(schedule.squash_lesson_price)]
        for tier in schedule.due_tiers:
            texts += [str(tier.day), str(tier.monthly_price)]
        for entry, text in zip(self.fields, texts):
            self._kit.widgets.set_text(entry, text)

    def save(self) -> None:
        def action() -> None:
            parser = self._kit.parser
            values = [entry.get().strip() for entry in self.fields]
            tiers: list[DueTier] = []
            for number in range(3):
                day_text, price_text = values[2 + number * 2], values[3 + number * 2]
                if not day_text and not price_text:
                    continue
                tiers.append(
                    DueTier(
                        parser.integer(day_text, f"Vencimento {number + 1}") if day_text else 0,
                        parser.decimal(price_text, f"Valor mensal {number + 1}") if price_text else None,
                    )
                )
            self._services.catalog.save_prices(
                PriceSchedule(
                    parser.decimal(values[0], "Valor da sauna"),
                    parser.decimal(values[1], "Valor da aula"),
                    tuple(tiers),
                )
            )
            self._kit.dialogs.info("Valores", "Tabela de valores salva com sucesso!")

        self._kit.runner.run(action)


class ReservationTab:
    """RF09: reservas semanais de quadras; aula só com um cliente."""

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
        tabs.add(self.frame, text="Reservas de squash")
        w = kit.widgets
        self.weekday = w.choice(
            self.frame,
            "Dia da semana",
            [f"{number} - {name}" for number, name in squash.weekday_names.items()],
            row=0,
        )
        self.time = w.choice(self.frame, "Horário", squash.time_slots, row=1)
        self.court = w.choice(self.frame, "Quadra", [str(court) for court in squash.courts], row=2)
        self.customer_pick = w.lookup(
            self.frame,
            "Cliente",
            lambda: [(c.code, c.name) for c in services.catalog.customers()],
            row=3,
        )
        self.add_customer_button = w.button(
            self.frame, "Adicionar cliente", self.add_customer, row=3, column=2
        )
        (self.customers,) = w.form(self.frame, ("Clientes da reserva",), row=4)
        self.clear_customers_button = w.button(
            self.frame, "Limpar clientes", self.clear_customers, row=4, column=2
        )
        self.is_game = tk.BooleanVar(value=True)
        self.game_check = ttk.Checkbutton(self.frame, text="Jogo (desmarque para aula)", variable=self.is_game)
        self.game_check.grid(row=5, column=1, sticky="w")
        self.save_button = w.button(self.frame, "Salvar reserva", self.save, row=6, column=1)
        self.delete_button = w.button(self.frame, "Excluir reserva", self.delete, row=6, column=2)
        self.table = w.table(self.frame, ("Dia", "Horário", "Quadra", "Tipo", "Clientes"), row=7)
        self.table.bind("<<TreeviewSelect>>", self.select)
        self.refresh()

    def add_customer(self) -> None:
        def action() -> None:
            picked = self.customer_pick.get().strip()
            self._kit.parser.code(picked, "Cliente")
            current = self.customers.get().strip()
            self._kit.widgets.set_text(self.customers, f"{current}; {picked}" if current else picked)
            self._kit.widgets.clear((self.customer_pick,))

        self._kit.runner.run(action)

    def clear_customers(self) -> None:
        self._kit.widgets.clear((self.customers,))

    def select(self, _event: object = None) -> None:
        """Ao clicar numa reserva, preenche o formulário com ela."""
        selection = self.table.selection()
        if not selection:
            return
        weekday, time, court = str(selection[0]).split("|")
        reservation = next(
            (
                r for r in self._services.reservations.reservations()
                if (r.weekday, r.time, r.court) == (int(weekday), time, int(court))
            ),
            None,
        )
        if reservation is None:
            return
        names = self._services.catalog.customer_names()
        parser, w = self._kit.parser, self._kit.widgets
        w.set_text(self.weekday, parser.option_text(reservation.weekday, self._squash.weekday_names))
        w.set_text(self.time, reservation.time)
        w.set_text(self.court, str(reservation.court))
        w.set_text(
            self.customers,
            "; ".join(parser.option_text(code, names) for code in reservation.customer_ids),
        )
        self.is_game.set(reservation.is_game)

    def save(self) -> None:
        def action() -> None:
            parser = self._kit.parser
            reservation = Reservation(
                weekday=parser.code(self.weekday.get(), "Dia da semana"),
                time=self.time.get().strip(),
                court=parser.integer(self.court.get(), "Quadra"),
                is_game=self.is_game.get(),
                customer_ids=tuple(parser.codes(self.customers.get(), "Clientes")),
            )
            reservation.validate()
            replace = True
            if self._services.reservations.has_reservation(
                reservation.weekday, reservation.time, reservation.court
            ):
                replace = self._kit.dialogs.confirm(
                    "Reservas", "Já existe uma reserva para este horário. Deseja substituí-la?"
                )
                if not replace:
                    return
            self._services.reservations.save(reservation, replace_existing=replace)
            self.refresh()
            self._kit.dialogs.info("Reservas", "Reserva salva com sucesso!")

        self._kit.runner.run(action)

    def delete(self) -> None:
        def action() -> None:
            key = self._kit.widgets.selected_key(self.table, "Selecione uma reserva.")
            weekday, time, court = key.split("|")
            if not self._kit.dialogs.confirm("Reservas", "Deseja excluir a reserva selecionada?"):
                return
            self._services.reservations.delete(int(weekday), time, int(court))
            self.refresh()

        self._kit.runner.run(action)

    def refresh(self) -> None:
        parser = self._kit.parser
        names = self._services.catalog.customer_names()
        self._kit.widgets.replace_rows(
            self.table,
            [
                (
                    f"{r.weekday}|{r.time}|{r.court}",
                    (parser.option_text(r.weekday, self._squash.weekday_names), r.time, r.court,
                     "Jogo" if r.is_game else "Aula",
                     "; ".join(parser.option_text(code, names) for code in r.customer_ids)),
                )
                for r in self._services.reservations.reservations()
            ],
        )


class DayGridTab:
    """RF10: ocupantes de cada horário e quadra na data escolhida."""

    def __init__(
        self, tabs: ttk.Notebook, services: ApplicationServices, kit: UiToolkit, clock: Clock
    ) -> None:
        self._services = services
        self._kit = kit
        self.frame = ttk.Frame(tabs, padding=12)
        tabs.add(self.frame, text="Grade do squash")
        (self.day,) = kit.widgets.form(self.frame, ("Data (DD/MM/AAAA)",), row=0)
        kit.widgets.set_text(self.day, kit.parser.date_text(clock.today()))
        self.show_button = kit.widgets.button(self.frame, "Mostrar grade", self.show, row=1, column=1)
        self.table = kit.widgets.table(
            self.frame, ("Horário", "Quadra 1", "Quadra 2", "Quadra 3"), row=2, height=14
        )
        self.show()

    def show(self) -> None:
        def action() -> None:
            day: date = self._kit.parser.day(self.day.get(), "Data")
            rows = self._services.reservations.day_grid(day)
            self._kit.widgets.replace_rows(
                self.table, [(row.time, (row.time, *row.courts)) for row in rows]
            )

        self._kit.runner.run(action)
