from data_sources.models.database_connection_config import DatabaseConnectionConfig
from data_sources.models.db_type import DbType


class RedshiftConnectionConfig(DatabaseConnectionConfig):
    database_type: str = DbType.REDSHIFT
    port: int = 5439
