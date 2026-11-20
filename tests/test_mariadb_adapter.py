from contextlib import contextmanager
import unittest

from dante_squash.infrastructure.mariadb import (
    MariaDBDatabase,
    MariaDBUnitOfWork,
    _MYSQL_SCHEMA_STATEMENTS,
)


class _Cursor:
    def __init__(self, statements):
        self.statements = statements

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, statement, parameters=()):
        self.statements.append((statement, parameters))


class _Connection:
    def __init__(self):
        self.statements = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return _Cursor(self.statements)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class MariaDBAdapterTests(unittest.TestCase):
    def test_initialization_creates_innodb_tables_and_seeds_idempotently(self) -> None:
        connection = _Connection()
        database = MariaDBDatabase(lambda: connection)

        database.initialize()

        ddl = [
            statement for statement, _parameters in connection.statements
            if statement.startswith("CREATE TABLE")
        ]
        inserts = [
            statement for statement, _parameters in connection.statements
            if statement.startswith("INSERT IGNORE")
        ]
        self.assertEqual(len(ddl), 8)
        self.assertEqual(len(_MYSQL_SCHEMA_STATEMENTS), 8)
        self.assertTrue(all("ENGINE=InnoDB" in statement for statement in ddl))
        self.assertTrue(all("DOUBLE PRECISION" not in statement for statement in ddl))
        self.assertEqual(len(inserts), 6)
        self.assertEqual(connection.commits, 1)
        self.assertTrue(connection.closed)

    def test_unit_of_work_commits_on_success_and_rolls_back_on_error(self) -> None:
        committed = _Connection()
        with MariaDBUnitOfWork(MariaDBDatabase(lambda: committed)):
            pass
        self.assertEqual(committed.commits, 1)
        self.assertEqual(committed.rollbacks, 0)

        rolled_back = _Connection()
        with self.assertRaises(RuntimeError):
            with MariaDBUnitOfWork(MariaDBDatabase(lambda: rolled_back)):
                raise RuntimeError("forced failure")
        self.assertEqual(rolled_back.commits, 0)
        self.assertEqual(rolled_back.rollbacks, 1)
        self.assertTrue(rolled_back.closed)

    def test_mariadb_dsn_is_required_without_disclosing_credentials(self) -> None:
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DANTE_SQUASH_MARIADB_DSN"):
                MariaDBDatabase.from_environment()


if __name__ == "__main__":
    unittest.main()
