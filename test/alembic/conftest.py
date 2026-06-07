import os
import pytest
from testcontainers.postgres import PostgresContainer
from app.alembic_runner import run_alembic_migrations



@pytest.fixture(scope="session")
def alembic_container():
    container = PostgresContainer("postgres:16-alpine").with_exposed_ports(5432)
    container.start()
    replace_database_url(container)
    run_alembic_migrations()
    try:
        yield container
    finally:
        container.stop()

def replace_database_url(container):
    name = container.dbname
    host = container.get_container_host_ip()
    port = int(container.get_exposed_port(5432))
    user = container.username
    password = container.password
    database_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    os.environ["DATABASE_URL"] = database_url