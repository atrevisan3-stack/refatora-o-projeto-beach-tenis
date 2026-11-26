"""Testes de arquitetura (CT18 a CT20) e da regra do professor: nada estático.

Analisam o código-fonte com ``ast``, sem executar o sistema.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "dante_squash"


class SourceModule:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.name = ".".join(path.relative_to(PACKAGE.parent).with_suffix("").parts)
        self.tree = ast.parse(path.read_text(encoding="utf-8"))

    @property
    def layer(self) -> str:
        parts = self.name.split(".")
        return parts[1] if len(parts) > 1 else ""

    def imports(self) -> set[str]:
        found: set[str] = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module)
        return found


MODULES = [SourceModule(p) for p in sorted(PACKAGE.rglob("*.py"))]


def modules_in(*layers: str) -> list[SourceModule]:
    return [m for m in MODULES if m.layer in layers]


def ids(modules):
    return [m.name for m in modules]


# Camada -> camadas internas que ela pode importar.
ALLOWED = {
    "domain": set(),
    "ports": {"domain"},
    "services": {"domain", "ports", "services"},
    "infrastructure": {"domain", "ports", "infrastructure"},
    "presentation": {"domain", "ports", "services", "presentation"},
}


@pytest.mark.parametrize("module", modules_in(*ALLOWED), ids=ids(modules_in(*ALLOWED)))
def test_ct18_camadas_so_dependem_das_camadas_permitidas(module):
    internal = {
        imp.split(".")[1]
        for imp in module.imports()
        if imp.startswith("dante_squash.") and len(imp.split(".")) > 1
    }
    assert internal <= ALLOWED[module.layer], (
        f"{module.name} ({module.layer}) importa {sorted(internal - ALLOWED[module.layer])}"
    )


@pytest.mark.parametrize(
    "module",
    modules_in("domain", "ports", "services", "infrastructure"),
    ids=ids(modules_in("domain", "ports", "services", "infrastructure")),
)
def test_ct19_regras_e_banco_nao_dependem_de_interface_grafica(module):
    assert not any(imp.split(".")[0] == "tkinter" for imp in module.imports())


@pytest.mark.parametrize(
    "module", modules_in("domain", "ports", "services"),
    ids=ids(modules_in("domain", "ports", "services")),
)
def test_ct19_regras_nao_dependem_do_driver_do_banco(module):
    assert not any(imp.split(".")[0] in {"psycopg", "psycopg2"} for imp in module.imports())


def test_ct20_sem_ciclos_entre_camadas():
    graph: dict[str, set[str]] = {}
    for module in MODULES:
        for imp in module.imports():
            parts = imp.split(".")
            if parts[0] == "dante_squash" and len(parts) > 1 and parts[1] != module.layer:
                graph.setdefault(module.layer, set()).add(parts[1])

    def reaches(start, target, seen=None):
        seen = seen or set()
        for nxt in graph.get(start, ()):
            if nxt == target or (nxt not in seen and reaches(nxt, target, seen | {nxt})):
                return True
        return False

    cycles = [layer for layer in graph if reaches(layer, layer)]
    assert cycles == []


@pytest.mark.parametrize("module", MODULES, ids=ids(MODULES))
def test_nada_estatico_sem_staticmethod_nem_classmethod(module):
    decorated = [
        f"{node.name} (linha {node.lineno})"
        for node in ast.walk(module.tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for decorator in node.decorator_list
        if isinstance(decorator, ast.Name) and decorator.id in {"staticmethod", "classmethod"}
    ]
    assert decorated == []


@pytest.mark.parametrize("module", MODULES, ids=ids(MODULES))
def test_nada_estatico_sem_funcoes_nem_variaveis_soltas_no_modulo(module):
    """No módulo só ficam imports, classes, docstring e o ``if __name__``."""
    loose = []
    for node in module.tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if isinstance(node, ast.If) and "__name__" in ast.unparse(node.test):
            continue
        loose.append(f"{type(node).__name__} (linha {node.lineno})")
    assert loose == []


@pytest.mark.parametrize("module", MODULES, ids=ids(MODULES))
def test_nada_estatico_sem_atributos_de_classe(module):
    """Classes não guardam valores no nível da classe (anotações de campo são permitidas)."""
    found = []
    for cls in ast.walk(module.tree):
        if not isinstance(cls, ast.ClassDef):
            continue
        for item in cls.body:
            if isinstance(item, ast.Assign):
                found.append(f"{cls.name}.{ast.unparse(item.targets[0])} (linha {item.lineno})")
            elif isinstance(item, ast.AnnAssign) and item.value is not None:
                found.append(f"{cls.name}.{ast.unparse(item.target)} (linha {item.lineno})")
    assert found == []


def test_nomenclatura_dos_repositorios_postgres():
    infra = next(m for m in MODULES if m.name.endswith("infrastructure.postgres"))
    repositories = [
        node.name for node in infra.tree.body
        if isinstance(node, ast.ClassDef) and node.name.endswith("Repository")
    ]
    assert repositories and all(name.startswith("Postgres") for name in repositories)
