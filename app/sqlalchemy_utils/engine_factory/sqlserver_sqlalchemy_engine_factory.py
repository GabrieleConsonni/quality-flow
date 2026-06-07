from sqlalchemy import create_engine

from data_sources.models.sqlserver_connection_config import SqlServerConnectionConfig
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory import SQLAlchemyEngineFactory


class SqlServerSQLAlchemyEngineFactory(SQLAlchemyEngineFactory):
    def create_engine(self, connection_cfg: SqlServerConnectionConfig):
        return create_engine(
            f"mssql+pymssql://{connection_cfg.user}:{connection_cfg.password}"
            f"@{connection_cfg.host}:{connection_cfg.port}/{connection_cfg.database}"
        )

