"""Backup das tabelas em arquivos nomeados com o instante da exportação (RF16)."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from dante_squash.domain import BusinessRuleError
from dante_squash.ports import Clock, TableExporter


class BackupService:
    def __init__(self, exporter: TableExporter, clock: Clock) -> None:
        self._exporter = exporter
        self._clock = clock

    def export(self, directory: Path) -> Sequence[Path]:
        if not directory.is_dir():
            raise BusinessRuleError("Selecione uma pasta existente para o backup.")
        stamp = self._clock.now().strftime("%Y%m%d_%H%M%S")
        return self._exporter.export_all(directory, stamp)
