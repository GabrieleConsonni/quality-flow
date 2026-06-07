from fastapi import APIRouter

from _alembic.models.dataset_entity import DatasetEntity
from _alembic.services.session_context_manager import managed_session
from data_sources.models.dtos.create_dataset_dto import CreateDatasetDto
from data_sources.models.dtos.update_dataset_dto import UpdateDatasetDto
from data_sources.services.alembic.dataset_service import DatasetService
from data_sources.services.dataset_query_service import DatasetQueryService
from exceptions.app_exception import QualityFlowAppException

router = APIRouter(prefix="/data-source")

@router.post("/database")
async def insert_database_data_source_api(dto: CreateDatasetDto):
    payload = dict(dto.payload or {})
    DatasetQueryService.validate_dataset_configuration(payload)
    perimeter = DatasetQueryService.normalize_perimeter(dto.perimeter)

    with managed_session() as session:
        entity = DatasetEntity(
            description=dto.description,
            configuration_json=payload,
            perimeter=perimeter,
        )
        _id = DatasetService().insert(session, entity)
        return {"id": _id, "message": "Database datasource added"}


@router.put("/database")
async def update_database_data_source_api(dto: UpdateDatasetDto):
    payload = dict(dto.payload or {})
    DatasetQueryService.validate_dataset_configuration(payload)
    perimeter = DatasetQueryService.normalize_perimeter(dto.perimeter)

    with managed_session() as session:
        updated = DatasetService().update(
            session,
            dto.id,
            description=dto.description,
            configuration_json=payload,
            perimeter=perimeter,
        )
        if not updated:
            raise QualityFlowAppException(f"No database datasource found with id [ {dto.id} ]")
        return {"message": "Database datasource updated"}


@router.get("/database")
async def find_all_database_data_source_api():
    with managed_session() as session:
        all_data = DatasetService().get_all_datasets(session)
        return [DatasetQueryService.serialize_dataset(dataset) for dataset in all_data]


@router.get("/database/{_id}")
async def find_database_data_source_api(_id: str):
    with managed_session() as session:
        entity = DatasetQueryService.get_dataset_or_raise(session, _id)
        return DatasetQueryService.serialize_dataset(entity)


@router.get("/database/{_id}/preview")
async def preview_database_data_source_api(_id: str, limit: int = 100):
    with managed_session() as session:
        entity = DatasetQueryService.get_dataset_or_raise(session, _id)
        payload = entity.configuration_json if isinstance(entity.configuration_json, dict) else {}
        perimeter = entity.perimeter if isinstance(entity.perimeter, dict) else None
        return DatasetQueryService.execute_dataset_query(
            payload,
            perimeter,
            limit=limit,
            dataset_id=str(entity.id or "").strip() or _id,
            session=session,
        )


@router.delete("/database/{_id}")
async def delete_database_data_source_api(_id: str):
    with managed_session() as session:
        entity = DatasetQueryService.get_dataset_or_raise(session, _id)
        count = DatasetService().delete_by_id(session, entity.id)
        if count == 0:
            raise QualityFlowAppException(f"No database datasource found with id [ {_id} ]")
        return {"message": "Database datasource deleted successfully"}
