from _alembic.models.json_payload_entity import JsonPayloadEntity
from json_utils.models.enums.json_type import JsonType


def convertEntityToDto(entity:JsonPayloadEntity)->dict:
    dto = {
        "id": entity.id,
        "description": entity.description,
        "payload": entity.payload,
        "created_date": entity.created_date if entity.created_date else None,
        "modified_date": entity.modified_date if entity.modified_date else None,
    }
    return dto

def convertDtoToEntity(dto:dict,json_type:JsonType)->JsonPayloadEntity:
    entity = JsonPayloadEntity()
    entity.id = dto.get("id", None)
    entity.description = dto.get("description", None)
    entity.json_type = json_type.value
    entity.payload = dto["payload"]
    return entity
