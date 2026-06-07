import pytest
from docker.errors import DockerException
from sqlalchemy import create_engine, text
from testcontainers.core.exceptions import ContainerStartException
from testcontainers.mssql import SqlServerContainer
from testcontainers.oracle import OracleDbContainer
from testcontainers.postgres import PostgresContainer

from app.data_sources.models.oracle_connection_config import OracleConnectionConfig
from app.data_sources.models.postgres_connection_config import PostgresConnectionConfig
from app.data_sources.models.redshift_connection_config import RedshiftConnectionConfig
from app.data_sources.models.sqlserver_connection_config import SqlServerConnectionConfig
from app.sqlalchemy_utils.engine_factory.oracle_sqlalchemy_engine_factory import (
    OracleSQLAlchemyEngineFactory,
)
from app.sqlalchemy_utils.engine_factory.postgres_sqlalchemy_engine_factory import (
    PostgresSQLAlchemyEngineFactory,
)
from app.sqlalchemy_utils.engine_factory.redshift_sqlalchemy_engine_factory import (
    RedshiftSQLAlchemyEngineFactory,
)
from app.sqlalchemy_utils.engine_factory.sqlserver_sqlalchemy_engine_factory import (
    SqlServerSQLAlchemyEngineFactory,
)

def _start_container_or_skip(container, name: str):
    try:
        return container.start()
    except (DockerException, ContainerStartException) as exc:
        pytest.skip(f"Cannot start {name} test container: {exc}")


@pytest.fixture(scope="module")
def postgres_container():
    container = PostgresContainer("postgres:16-alpine")
    started_container = _start_container_or_skip(container, "postgres")
    try:
        yield started_container
    finally:
        started_container.stop()


@pytest.fixture(scope="module")
def sqlserver_container():
    container = SqlServerContainer("mcr.microsoft.com/mssql/server:2022-latest")
    started_container = _start_container_or_skip(container, "sqlserver")
    try:
        yield started_container
    finally:
        started_container.stop()


@pytest.fixture(scope="module")
def oracle_container():
    container = OracleDbContainer(
        image="gvenzl/oracle-free:slim",
        oracle_password="1Secure*Password1",
    )
    started_container = _start_container_or_skip(container, "oracle")
    try:
        yield started_container
    finally:
        started_container.stop()


def test_postgres_sqlalchemy_engine_factory(postgres_container):
    schema_name = "quality_flow_test"

    admin_engine = create_engine(postgres_container.get_connection_url())
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
    finally:
        admin_engine.dispose()

    config = PostgresConnectionConfig(
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(5432)),
        database=postgres_container.dbname,
        db_schema=schema_name,
        user=postgres_container.username,
        password=postgres_container.password,
    )

    engine = PostgresSQLAlchemyEngineFactory().create_engine(config)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            assert connection.execute(text("SELECT current_schema()")).scalar_one() == schema_name
    finally:
        engine.dispose()


def test_sqlserver_sqlalchemy_engine_factory(sqlserver_container):
    config = SqlServerConnectionConfig(
        host=sqlserver_container.get_container_host_ip(),
        port=int(sqlserver_container.get_exposed_port(1433)),
        database=sqlserver_container.dbname,
        db_schema="dbo",
        user=sqlserver_container.username,
        password=sqlserver_container.password,
    )

    engine = SqlServerSQLAlchemyEngineFactory().create_engine(config)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            assert (
                connection.execute(text("SELECT DB_NAME()")).scalar_one().lower()
                == config.database.lower()
            )
    finally:
        engine.dispose()


def test_oracle_sqlalchemy_engine_factory(oracle_container):
    service_name = oracle_container.dbname or "FREEPDB1"
    config = OracleConnectionConfig(
        host=oracle_container.get_container_host_ip(),
        port=int(oracle_container.get_exposed_port(1521)),
        database=service_name,
        db_schema="SYSTEM",
        user="system",
        password=oracle_container.oracle_password,
    )

    engine = OracleSQLAlchemyEngineFactory().create_engine(config)
    try:
        with engine.connect() as connection:
            assert int(connection.execute(text("SELECT 1 FROM dual")).scalar_one()) == 1
            current_service_name = connection.execute(
                text("SELECT SYS_CONTEXT('USERENV', 'SERVICE_NAME') FROM dual")
            ).scalar_one()
            assert current_service_name.upper() == service_name.upper()
    finally:
        engine.dispose()


@pytest.fixture(scope="module")
def redshift_container():
    # Redshift uses the Postgres wire protocol; a Postgres container is sufficient
    # for verifying dialect, schema routing, and engine creation.
    container = PostgresContainer("postgres:16-alpine")
    started_container = _start_container_or_skip(container, "redshift (postgres-compat)")
    try:
        yield started_container
    finally:
        started_container.stop()


def test_redshift_sqlalchemy_engine_factory(redshift_container):
    schema_name = "quality_flow_test"

    admin_engine = create_engine(redshift_container.get_connection_url())
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
    finally:
        admin_engine.dispose()

    config = RedshiftConnectionConfig(
        host=redshift_container.get_container_host_ip(),
        port=int(redshift_container.get_exposed_port(5432)),
        database=redshift_container.dbname,
        db_schema=schema_name,
        user=redshift_container.username,
        password=redshift_container.password,
    )

    engine = RedshiftSQLAlchemyEngineFactory().create_engine(config)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            assert connection.execute(text("SELECT current_schema()")).scalar_one() == schema_name
    finally:
        engine.dispose()
