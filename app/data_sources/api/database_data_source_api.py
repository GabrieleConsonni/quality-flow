from fastapi import APIRouter
from sqlalchemy import MetaData, Table, inspect, select

from _alembic.services.session_context_manager import managed_session
from data_sources.models.database_connection_config_types import (
    convert_database_connection_config,
)
from sqlalchemy_utils.database_table_reader import DatabaseTableReader
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import create_sqlalchemy_engine
from data_sources.services.alembic.database_connection_service import load_database_connection
from exceptions.app_exception import QualityFlowAppException
from json_utils.models.dtos.create_json_payload_dto import CreateJsonPayloadDto
from _alembic.models.json_payload_entity import JsonPayloadEntity
from json_utils.models.enums.json_type import JsonType
from json_utils.models.dtos.update_json_payload_dto import UpdateJsonPayloadDto
from json_utils.services.alembic.json_files_service import JsonFilesService

router = APIRouter(prefix="/database")


def _safe_limit(limit: int) -> int:
    if limit <= 0:
        return 1
    if limit > 500:
        return 500
    return limit


def _normalize_object_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"table", "base table"}:
        return "table"
    if normalized == "view":
        return "view"
    raise QualityFlowAppException(f"Unsupported object type: {value}")


def _list_database_objects(connection, schema: str | None = None) -> dict:
    engine = create_sqlalchemy_engine(connection)
    inspector = inspect(engine)
    selected_schema = schema or connection.db_schema or None

    table_names = sorted(inspector.get_table_names(schema=selected_schema))
    view_names = sorted(inspector.get_view_names(schema=selected_schema))

    items = []
    for table_name in table_names:
        items.append(
            {
                "schema": selected_schema,
                "name": table_name,
                "object_type": "table",
                "qualified_name": (
                    f"{selected_schema}.{table_name}" if selected_schema else table_name
                ),
            }
        )
    for view_name in view_names:
        items.append(
            {
                "schema": selected_schema,
                "name": view_name,
                "object_type": "view",
                "qualified_name": (
                    f"{selected_schema}.{view_name}" if selected_schema else view_name
                ),
            }
        )

    return {
        "schema": selected_schema,
        "tables": table_names,
        "views": view_names,
        "items": sorted(items, key=lambda item: (item["object_type"], item["name"])),
    }

@router.post("/connection")
async def insert_database_connection_api(dto: CreateJsonPayloadDto):
    with managed_session() as session:
        entity = JsonPayloadEntity()
        entity.description = dto.description
        entity.json_type = JsonType.DATABASE_CONNECTION.value
        entity.payload = dto.payload
        _id = JsonFilesService().insert(session, entity)
    return {"id":_id,"message": "Database connection added"}

@router.put("/connection")
async def update_database_connection_api(dto: UpdateJsonPayloadDto):
    with managed_session() as session:
        _id = JsonFilesService().update(session, dto.id,
                                        description=dto.description,
                                        json_type=JsonType.DATABASE_CONNECTION.value,
                                        payload=dto.payload)
    return {"message": "Database connection updated"}

@router.get("/connection")
async def find_database_connections_api():
    result = []
    with managed_session() as session:
        all =  JsonFilesService().get_all_by_type(session,JsonType.DATABASE_CONNECTION)
        for data in all:
            result.append({
                "id": data.id,
                "description": data.description,
                "payload": data.payload
            })
    return result

@router.get("/connection/{_id}")
async def find_database_connection_by_id_api(_id:str):
    with managed_session() as session:
        entity: JsonPayloadEntity = JsonFilesService().get_by_id(session,_id)
        if not entity:
            raise QualityFlowAppException(f"No database connection found with id [ {_id} ]")
        return {
            "id": entity.id,
            "description": entity.description,
            "payload": entity.payload
        }

@router.get("/connection/{_id}/test")
async def test_database_connection_api(_id: str):
    connection = load_database_connection(_id)
    if not connection:
        raise QualityFlowAppException(f"No database connection found with id [ {_id} ]")

    engine = create_sqlalchemy_engine(connection)

    if DatabaseTableReader.test_connection(engine):
        return {"message": "Connection successful"}

    return {"message": "Connection failed"}


@router.post("/connection/test")
async def test_database_connection_from_payload_api(dto: CreateJsonPayloadDto):
    if not isinstance(dto.payload, dict):
        raise QualityFlowAppException("Invalid payload: expected object.")

    try:
        connection = convert_database_connection_config(dto.payload)
        engine = create_sqlalchemy_engine(connection)
    except Exception as exc:
        raise QualityFlowAppException(f"Invalid connection payload: {str(exc)}")

    if DatabaseTableReader.test_connection(engine):
        return {"message": "Connection successful"}

    return {"message": "Connection failed"}


@router.get("/connection/{_id}/objects")
async def list_database_objects_api(_id: str, schema: str | None = None):
    connection = load_database_connection(_id)
    if not connection:
        raise QualityFlowAppException(f"No database connection found with id [ {_id} ]")

    try:
        return _list_database_objects(connection, schema=schema)
    except Exception as exc:
        raise QualityFlowAppException(f"Error loading database objects: {str(exc)}")


@router.get("/connection/{_id}/object-preview")
async def preview_database_object_api(
    _id: str,
    object_name: str,
    object_type: str = "table",
    schema: str | None = None,
    limit: int = 100,
):
    connection = load_database_connection(_id)
    if not connection:
        raise QualityFlowAppException(f"No database connection found with id [ {_id} ]")
    if not object_name:
        raise QualityFlowAppException("Missing object_name query param.")

    normalized_type = _normalize_object_type(object_type)
    max_rows = _safe_limit(limit)

    try:
        objects = _list_database_objects(connection, schema=schema)
        allowed_names = (
            objects.get("tables", [])
            if normalized_type == "table"
            else objects.get("views", [])
        )
        if object_name not in allowed_names:
            raise QualityFlowAppException(
                f"Object [ {object_name} ] not found for type [ {normalized_type} ]"
            )

        engine = create_sqlalchemy_engine(connection)
        metadata = MetaData()
        table = Table(
            object_name,
            metadata,
            schema=objects.get("schema"),
            autoload_with=engine,
        )
        stmt = select(table).limit(max_rows)
        with engine.connect() as db_connection:
            result = db_connection.execute(stmt)
            rows = [dict(row._mapping) for row in result]

        return {
            "schema": objects.get("schema"),
            "object_name": object_name,
            "object_type": normalized_type,
            "columns": [str(col.name) for col in table.columns],
            "rows": rows,
            "count": len(rows),
        }
    except QualityFlowAppException:
        raise
    except Exception as exc:
        raise QualityFlowAppException(f"Error previewing object [ {object_name} ]: {str(exc)}")

@router.delete("/connection/{_id}")
async def delete_database_connection_api(_id: str):
    with managed_session() as session:
        count = JsonFilesService().delete_by_id(session,_id)
        if count == 0:
            raise QualityFlowAppException(f"No database connection found with id [ {_id} ]")
        return {"message": f"Database connection deleted successfully"}
