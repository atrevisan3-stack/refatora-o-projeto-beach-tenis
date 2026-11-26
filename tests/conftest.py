"""Fixtures compartilhadas.

- ``memory``: serviços sobre o banco em memória (rápido, sem Docker).
- ``postgres``: serviços sobre um PostgreSQL real. Usa ``DANTE_SQUASH_TEST_DSN``
  se definida; senão sobe um contêiner ``postgres:16`` com Testcontainers.
- ``services``: parametrizada, roda o mesmo teste nos dois bancos.
"""

from __future__ import annotations

import os
from datetime import date

import pytest

from dante_squash.composition import ServiceFactory
from tests.support.builders import Scenario
from tests.support.fakes import (
    FixedClock,
    InMemoryDatabase,
    InMemoryUnitOfWorkFactory,
    RecordingExporter,
)

TODAY = date(2026, 3, 12)  # quinta-feira


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(TODAY)


@pytest.fixture
def memory(clock) -> Scenario:
    factory = ServiceFactory(
        InMemoryUnitOfWorkFactory(InMemoryDatabase()), RecordingExporter(), clock
    )
    return Scenario(factory.build(), clock)


@pytest.fixture(scope="session")
def postgres_dsn():
    dsn = os.environ.get("DANTE_SQUASH_TEST_DSN", "").strip()
    if dsn:
        yield dsn
        return
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("Testcontainers não instalado e DANTE_SQUASH_TEST_DSN não definida.")
    try:
        container = PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as error:  # Docker desligado ou indisponível
        pytest.skip(f"Não foi possível iniciar o PostgreSQL no Docker: {error}")
    try:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        yield (
            f"postgresql://{container.username}:{container.password}"
            f"@{host}:{port}/{container.dbname}"
        )
    finally:
        container.stop()


@pytest.fixture
def database(postgres_dsn):
    from dante_squash.infrastructure.postgres import (
        PostgresDatabase,
        PostgresSchema,
        PsycopgConnector,
    )

    db = PostgresDatabase(PsycopgConnector(postgres_dsn), PostgresSchema())
    db.drop_all()
    db.initialize()
    return db


@pytest.fixture
def postgres(database, clock) -> Scenario:
    from dante_squash.infrastructure.postgres import CsvTableExporter, PostgresUnitOfWorkFactory

    factory = ServiceFactory(
        PostgresUnitOfWorkFactory(database), CsvTableExporter(database), clock
    )
    return Scenario(factory.build(), clock)


@pytest.fixture(params=["memória", "postgresql"])
def scenario(request) -> Scenario:
    if request.param == "postgresql":
        return request.getfixturevalue("postgres")
    return request.getfixturevalue("memory")
