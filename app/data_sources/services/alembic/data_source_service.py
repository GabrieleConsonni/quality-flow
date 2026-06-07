from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.services.session_context_manager import managed_session
from json_utils.services.alembic.json_files_service import JsonFilesService


def load_json_array(_id: str) -> list[dict]:

    with managed_session() as session:
        json_payload_entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, _id)

    if not json_payload_entity:
        raise ValueError(f"Json array '{_id}' not found")

    if isinstance(json_payload_entity.payload, list):
        return json_payload_entity.payload
    else:
        return [json_payload_entity.payload]

