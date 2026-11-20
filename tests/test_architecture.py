import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "dante_squash"


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


class LayeringTests(unittest.TestCase):
    def test_domain_and_services_do_not_depend_on_framework_or_database_adapters(self) -> None:
        forbidden = {"tkinter", "infrastructure", "presentation"}
        for layer in ("domain.py", "services"):
            paths = [ROOT / layer] if layer.endswith(".py") else list((ROOT / layer).glob("*.py"))
            for path in paths:
                with self.subTest(path=path.relative_to(ROOT)):
                    self.assertTrue(_imported_roots(path).isdisjoint(forbidden))

    def test_infrastructure_does_not_depend_on_user_interface_or_use_cases(self) -> None:
        for path in (ROOT / "infrastructure").glob("*.py"):
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertTrue(
                    _imported_roots(path).isdisjoint({"presentation", "services"})
                )


if __name__ == "__main__":
    unittest.main()
