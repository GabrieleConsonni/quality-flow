from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.services.session_context_manager import managed_session
from data_sources.models.database_connection_config_types import DatabaseConnectionConfigTypes
from data_sources.models.db_type import DbType
from data_sources.models.oracle_connection_config import OracleConnectionConfig
from data_sources.models.postgres_connection_config import PostgresConnectionConfig
from data_sources.models.redshift_connection_config import RedshiftConnectionConfig
from data_sources.models.sqlserver_connection_config import SqlServerConnectionConfig
from json_utils.services.alembic.json_files_service import JsonFilesService

_CONNECTION_MAPPING: dict[str, type[DatabaseConnectionConfigTypes]] = {
    DbType.POSTGRES: PostgresConnectionConfig,
    DbType.ORACLE: OracleConnectionConfig,
    DbType.SQLSERVER: SqlServerConnectionConfig,
    DbType.REDSHIFT: RedshiftConnectionConfig,
}


def load_database_connection(_id: str) -> DatabaseConnectionConfigTypes:

    with managed_session() as session:
        json_payload_entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, _id)

        if not json_payload_entity:
            raise ValueError(f"Database connection '{_id}' not found")

        config_class = _CONNECTION_MAPPING.get(json_payload_entity.payload.get("database_type"))

        if not config_class:
            raise ValueError(f"Unsupported database connection type: {json_payload_entity.payload.get('database_type')}")

        return config_class.model_validate(json_payload_entity.payload)
