import json

from fastapi import APIRouter

from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.services.session_context_manager import managed_session
from json_utils.models.dtos.create_json_payload_dto import CreateJsonPayloadDto
from json_utils.models.dtos.update_json_payload_dto import UpdateJsonPayloadDto
from json_utils.models.enums.json_type import JsonType
from json_utils.services.alembic.json_files_service import JsonFilesService
from json_utils.services.dto.json_payload_dto_service import convertDtoToEntity, convertEntityToDto

router = APIRouter(prefix="/broker")

@router.post("/connection")
async def insert_broker_connection_api(dto: CreateJsonPayloadDto):
    with managed_session() as session:
        _id = JsonFilesService().insert(session,convertDtoToEntity(dto.model_dump(),JsonType.BROKER_CONNECTION))
    return {"id":_id, "message": "Broker connection added"}

@router.put("/connection")
async def update_broker_connection_api(dto: UpdateJsonPayloadDto):
    with managed_session() as session:
        entity = JsonFilesService().update(
            session,
            dto.id,
            description=dto.description,
            payload=dto.payload
        )
        return {"message": "Broker connection updated"}

@router.get("/connection")
async def find_all_broker_connections_api():
    with managed_session() as session:
        service = JsonFilesService()
        all = service.get_all_by_type(session=session, j_type=JsonType.BROKER_CONNECTION)
        return [convertEntityToDto(e) for e in all]

@router.get("/connection/{_id}")
async def find_broker_connection_api(_id:str):
    with managed_session() as session:
        service = JsonFilesService()
        entity:JsonPayloadEntity = service.get_by_id(session, _id)
        if not entity:
            return {"message": f"No data found with id [ {_id} ]"}
        return convertEntityToDto(entity)

@router.delete("/connection/{_id}")
async def delete_broker_connection_api(_id: str):
    with managed_session() as session:
        count = JsonFilesService().delete_by_id(session,_id)
        if count == 0:
            return {"message": f"No broker connection found with id [ {_id} ]"}
        return {"message": f"Broker connection deleted successfully"}

