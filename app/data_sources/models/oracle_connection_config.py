from data_sources.models.database_connection_config import DatabaseConnectionConfig
from data_sources.models.db_type import DbType


class OracleConnectionConfig(DatabaseConnectionConfig):
    database_type: str = DbType.ORACLE
    port: int = 1521

