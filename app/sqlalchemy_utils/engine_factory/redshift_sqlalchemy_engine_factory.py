from sqlalchemy import create_engine

from data_sources.models.redshift_connection_config import RedshiftConnectionConfig
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory import SQLAlchemyEngineFactory


class RedshiftSQLAlchemyEngineFactory(SQLAlchemyEngineFactory):
    def create_engine(self, connection_cfg: RedshiftConnectionConfig):
        db_schema = connection_cfg.db_schema
        return create_engine(
            f"postgresql+psycopg2://{connection_cfg.user}:{connection_cfg.password}"
            f"@{connection_cfg.host}:{connection_cfg.port}/{connection_cfg.database}",
            connect_args={"options": f"-csearch_path={db_schema}"}
        )
