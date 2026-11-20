from contextlib import contextmanager
import unittest

from dante_squash.infrastructure.postgres import (
    PostgresDatabase,
    PostgresUnitOfWork,
    SCHEMA_STATEMENTS,
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
        self.exit_exception = None

    def __enter__(self):
        return self

    def __exit__(self, exception_type, _exception, _traceback):
        self.exit_exception = exception_type
        return False

    def cursor(self):
        return _Cursor(self.statements)


class PostgresAdapterTests(unittest.TestCase):
    def test_initialization_creates_eight_tables_and_parameterizes_seed_rows(self) -> None:
        connection = _Connection()
        database = PostgresDatabase(lambda: connection)

        database.initialize()

        create_statements = [
            statement for statement, _parameters in connection.statements
            if statement.startswith("CREATE TABLE")
        ]
        parameterized_inserts = [
            parameters for statement, parameters in connection.statements
            if statement.startswith("INSERT INTO")
        ]
        self.assertEqual(len(SCHEMA_STATEMENTS), 8)
        self.assertEqual(len(create_statements), 8)
        self.assertEqual(len(parameterized_inserts), 6)

    def test_unit_of_work_propagates_errors_for_transaction_rollback(self) -> None:
        connection = _Connection()
        database = PostgresDatabase(lambda: connection)

        with self.assertRaises(RuntimeError):
            with PostgresUnitOfWork(database):
                raise RuntimeError("forced failure")

        self.assertIs(connection.exit_exception, RuntimeError)


if __name__ == "__main__":
    unittest.main()
