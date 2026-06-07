from fastapi import APIRouter

from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.services.session_context_manager import managed_session
from exceptions.app_exception import QualityFlowAppException
from json_utils.models.dtos.create_json_payload_dto import CreateJsonPayloadDto
from json_utils.models.dtos.update_json_payload_dto import UpdateJsonPayloadDto
from json_utils.models.enums.json_type import JsonType
from json_utils.services.alembic.json_files_service import JsonFilesService

router = APIRouter(prefix="/data-source")


@router.post("/json-array")
async def insert_json_array_api(dto: CreateJsonPayloadDto):
    with managed_session() as session:
        entity = JsonPayloadEntity()
        entity.description = dto.description
        entity.json_type = JsonType.JSON_ARRAY.value
        entity.payload = dto.payload
        _id = JsonFilesService().insert(session, entity)
        return {"id": _id, "message": "Json array added"}


@router.put("/json-array")
async def update_json_array_api(dto: UpdateJsonPayloadDto):
    with managed_session() as session:
        _id = JsonFilesService().update(session, dto.id,
                                        description=dto.description,
                                        json_type=JsonType.JSON_ARRAY.value,
                                        payload=dto.payload
                                        )
        return {"message": "Json array updated"}


@router.get("/json-array")
async def find_all_json_array_api():
    result = []
    with managed_session() as session:
        all = JsonFilesService().get_all_by_type(session, JsonType.JSON_ARRAY)
        for data in all:
            result.append({
                "id": data.id,
                "description": data.description,
                "payload": data.payload
            })
    return result


@router.get("/json-array/{_id}")
async def find_json_array_api(_id: str):
    with managed_session() as session:
        entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, _id)
        if not entity:
            raise QualityFlowAppException(f"No data found with id [ {_id} ]")
        return {
            "id": entity.id,
            "description": entity.description,
            "payload": entity.payload
        }


@router.delete("/json-array/{_id}")
async def delete_json_array_api(_id: str):
    with managed_session() as session:
        count = JsonFilesService().delete_by_id(session,_id)
        if count == 0:
            raise QualityFlowAppException(f"No Json array item found with id [ {_id} ]")
        return {"message": f"Json array item deleted successfully"}
