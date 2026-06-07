"""Unit tests for Redshift connection config, type mapping, and engine factory composite."""
import pytest

from data_sources.models.db_type import DbType
from data_sources.models.redshift_connection_config import RedshiftConnectionConfig
from data_sources.models.postgres_connection_config import PostgresConnectionConfig
from data_sources.models.database_connection_config_types import (
    convert_database_connection_config,
)
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import (
    create_sqlalchemy_engine,
)
from sqlalchemy_utils.engine_factory.redshift_sqlalchemy_engine_factory import (
    RedshiftSQLAlchemyEngineFactory,
)


_BASE_CONFIG = {
    "host": "redshift-host.example.com",
    "port": 5439,
    "database": "mydb",
    "db_schema": "public",
    "user": "admin",
    "password": "secret",
}


class TestDbTypeRedshift:
    def test_redshift_constant_value(self):
        assert DbType.REDSHIFT == "redshift"


class TestRedshiftConnectionConfig:
    def test_default_port_is_5439(self):
        config = RedshiftConnectionConfig(**_BASE_CONFIG)
        assert config.port == 5439

    def test_default_port_applied_when_omitted(self):
        payload = {k: v for k, v in _BASE_CONFIG.items() if k != "port"}
        config = RedshiftConnectionConfig(**payload)
        assert config.port == 5439

    def test_database_type_is_redshift(self):
        config = RedshiftConnectionConfig(**_BASE_CONFIG)
        assert config.database_type == DbType.REDSHIFT

    def test_database_type_string_value(self):
        config = RedshiftConnectionConfig(**_BASE_CONFIG)
        assert config.database_type == "redshift"

    def test_model_validate_round_trip(self):
        payload = {"database_type": "redshift", **_BASE_CONFIG}
        config = RedshiftConnectionConfig.model_validate(payload)
        assert config.database_type == DbType.REDSHIFT
        assert config.port == 5439
        assert config.host == "redshift-host.example.com"


class TestConvertDatabaseConnectionConfigRedshift:
    def test_convert_redshift_returns_redshift_config(self):
        payload = {"database_type": "redshift", **_BASE_CONFIG}
        result = convert_database_connection_config(payload)
        assert isinstance(result, RedshiftConnectionConfig)
        assert result.database_type == DbType.REDSHIFT

    def test_convert_postgres_not_affected(self):
        payload = {"database_type": "postgres", **{**_BASE_CONFIG, "port": 5432}}
        result = convert_database_connection_config(payload)
        assert isinstance(result, PostgresConnectionConfig)

    def test_convert_unsupported_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported database connection type"):
            convert_database_connection_config({"database_type": "unknown_db"})


class TestRedshiftEngineFactoryComposite:
    def test_create_sqlalchemy_engine_returns_engine(self):
        config = RedshiftConnectionConfig(**_BASE_CONFIG)
        engine = create_sqlalchemy_engine(config)
        # SQLAlchemy engine creation is lazy; engine object is returned
        # even for a non-reachable host.
        assert engine is not None
        engine.dispose()

    def test_unsupported_subclass_raises_value_error(self):
        class _FakeConfig(RedshiftConnectionConfig):
            pass

        with pytest.raises(ValueError, match="Unsupported sqlalchemy engine factory type"):
            create_sqlalchemy_engine(_FakeConfig(**_BASE_CONFIG))


class TestRedshiftSQLAlchemyEngineFactory:
    def test_engine_url_uses_psycopg2_dialect(self):
        config = RedshiftConnectionConfig(**_BASE_CONFIG)
        factory = RedshiftSQLAlchemyEngineFactory()
        engine = factory.create_engine(config)
        try:
            assert engine.url.drivername == "postgresql+psycopg2"
            assert engine.url.host == "redshift-host.example.com"
            assert engine.url.port == 5439
            assert engine.url.database == "mydb"
        finally:
            engine.dispose()

    def test_engine_creation_config_host_and_port(self):
        config = RedshiftConnectionConfig(**_BASE_CONFIG)
        factory = RedshiftSQLAlchemyEngineFactory()
        engine = factory.create_engine(config)
        try:
            assert engine.url.host == config.host
            assert engine.url.port == config.port
            assert engine.url.database == config.database
            assert engine.url.username == config.user
        finally:
            engine.dispose()
