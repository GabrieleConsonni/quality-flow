from app._alembic.models.json_payload_entity import JsonPayloadEntity
from app._alembic.services.session_context_manager import managed_session
from app.json_utils.models.enums.json_type import JsonType

from app.json_utils.services.alembic.json_files_service import JsonFilesService

entity = JsonPayloadEntity(
    description="test payload",
    json_type=JsonType.BROKER_CONNECTION.value,
    payload={"key": "value"}
)

def test_json_files_service(alembic_container):
    new_id = _verify_insert_entity()
    _verify_get_all_by_type(expected_count=1)
    _verify_update_entity(new_id)
    _verify_delete_entity(new_id)

def _verify_insert_entity()->str:
    with managed_session() as session:
        service = JsonFilesService()

        inserted_id = service.insert(session, entity)

        retrieved_entity = service.get_by_id(session, inserted_id)

        assert retrieved_entity is not None
        assert retrieved_entity.description == "test payload"
        assert retrieved_entity.json_type == JsonType.BROKER_CONNECTION.value
        assert retrieved_entity.payload == {"key": "value"}

        return inserted_id

def _verify_get_all_by_type(expected_count:int):
    with managed_session() as session:
        service = JsonFilesService()

        entities = service.get_all_by_type(session, JsonType.BROKER_CONNECTION)

        assert len(entities) == expected_count

def _verify_update_entity(_id:str):
    with managed_session() as session:
        service = JsonFilesService()

        updated_entity = service.update(
            session,
            _id,
            description="updated payload",
            payload={"new_key": "new_value"}
        )

        assert updated_entity is not None
        assert updated_entity.description == "updated payload"
        assert updated_entity.payload == {"new_key": "new_value"}

def _verify_delete_entity(_id:str):
    with managed_session() as session:
        service = JsonFilesService()

        delete_count = service.delete_by_id(session, _id)
        assert delete_count == 1



        retrieved_entity = service.get_by_id(session, _id)
        assert retrieved_entity is None

