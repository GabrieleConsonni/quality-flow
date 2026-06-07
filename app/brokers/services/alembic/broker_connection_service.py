from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.services.session_context_manager import managed_session
from json_utils.services.alembic.json_files_service import JsonFilesService
from brokers.models.connections.broker_connection_config_types import convert_to_broker_connection_config


def load_broker_connection(_id: str):

    with managed_session() as session:
        json_payload_entity:JsonPayloadEntity = JsonFilesService().get_by_id(session,_id)

        if not json_payload_entity:
            raise ValueError(f"Broker connection '{_id}' not found")

        return convert_to_broker_connection_config(json_payload_entity.payload)