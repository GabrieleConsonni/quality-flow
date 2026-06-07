from sqlalchemy import create_engine

from data_sources.models.oracle_connection_config import OracleConnectionConfig
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory import SQLAlchemyEngineFactory


class OracleSQLAlchemyEngineFactory(SQLAlchemyEngineFactory):
    def create_engine(self, connection_cfg: OracleConnectionConfig):
        return create_engine(
            f"oracle+oracledb://{connection_cfg.user}:{connection_cfg.password}"
            f"@{connection_cfg.host}:{connection_cfg.port}/?service_name={connection_cfg.database}"
        )

