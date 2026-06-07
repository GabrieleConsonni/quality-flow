from data_sources.models.db_type import DbType
from data_sources.models.postgres_connection_config import PostgresConnectionConfig
from data_sources.models.oracle_connection_config import OracleConnectionConfig
from data_sources.models.redshift_connection_config import RedshiftConnectionConfig
from data_sources.models.sqlserver_connection_config import SqlServerConnectionConfig

DatabaseConnectionConfigTypes = (
    PostgresConnectionConfig
    | OracleConnectionConfig
    | SqlServerConnectionConfig
    | RedshiftConnectionConfig
)

def convert_database_connection_config(config: dict) -> DatabaseConnectionConfigTypes:
    database_type = str(config.get("database_type") or "").strip().lower()
    if database_type == DbType.POSTGRES:
        return PostgresConnectionConfig(**config)
    if database_type == DbType.ORACLE:
        return OracleConnectionConfig(**config)
    if database_type == DbType.SQLSERVER:
        return SqlServerConnectionConfig(**config)
    if database_type == DbType.REDSHIFT:
        return RedshiftConnectionConfig(**config)
    raise ValueError(f"Unsupported database connection type: {database_type}")
