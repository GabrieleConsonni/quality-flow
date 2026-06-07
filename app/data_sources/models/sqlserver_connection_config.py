from data_sources.models.database_connection_config import DatabaseConnectionConfig
from data_sources.models.db_type import DbType


class SqlServerConnectionConfig(DatabaseConnectionConfig):
    database_type: str = DbType.SQLSERVER
    port: int = 1433

