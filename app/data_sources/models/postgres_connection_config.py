from data_sources.models.database_connection_config import DatabaseConnectionConfig
from data_sources.models.db_type import DbType


class PostgresConnectionConfig(DatabaseConnectionConfig):
    database_type: str  = DbType.POSTGRES
    port: int = 5432


