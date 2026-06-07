from sqlalchemy.orm import Session, InstrumentedAttribute

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.services.base_id_service import BaseIdEntityService
from json_utils.models.enums.json_type import JsonType


class JsonFilesService(BaseIdEntityService):

    def get_entity_class(self) -> type[BaseIdEntity]:
        return JsonPayloadEntity

    def get_all_by_type(self, session:Session, j_type: JsonType)->list[JsonPayloadEntity]:
        json_type_attr: InstrumentedAttribute = JsonPayloadEntity.json_type
        query = session.query(JsonPayloadEntity).filter(json_type_attr == j_type.value)
        return query.all()

