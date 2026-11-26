"""Fixture da interface: janela Tkinter real, escondida, sobre o banco em memória."""

from __future__ import annotations

import logging

import pytest

from tests.support.fakes import FakeDialogs


class GuiHarness:
    def __init__(self, window, dialogs: FakeDialogs, scenario) -> None:
        self.window = window
        self.dialogs = dialogs
        self.scenario = scenario

    def type(self, entry, text: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, text)

    def rows(self, table) -> list[tuple[str, ...]]:
        return [tuple(str(v) for v in table.item(key, "values")) for key in table.get_children()]

    def select(self, table, key: str) -> None:
        table.selection_set(key)


@pytest.fixture
def gui(memory):
    tk = pytest.importorskip("tkinter")
    from dante_squash.presentation.main_window import MainWindow
    from dante_squash.presentation.widgets import (
        ActionRunner,
        UiToolkit,
        ValueParser,
        WidgetFactory,
    )

    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"Sem tela disponível para o Tkinter: {error}")
    root.withdraw()
    dialogs = FakeDialogs()
    kit = UiToolkit(
        dialogs=dialogs,
        parser=ValueParser(),
        widgets=WidgetFactory(),
        runner=ActionRunner(dialogs, logging.getLogger("teste")),
    )
    from dante_squash.domain import SquashCalendar

    window = MainWindow(root, memory.services, kit, memory.clock, SquashCalendar())
    yield GuiHarness(window, dialogs, memory)
    root.destroy()
