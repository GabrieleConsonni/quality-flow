from fastapi import APIRouter

from _alembic.services.session_context_manager import managed_session
from exceptions.app_exception import QualityFlowAppException
from mock_servers.models.dtos.mock_server_dto import CreateMockServerDto, UpdateMockServerDto
from mock_servers.services.alembic.mock_server_service import MockServerService
from mock_servers.services.mock_server_payload_service import (
    create_mock_server,
    serialize_mock_server,
    update_mock_server,
)
from mock_servers.services.runtime.mock_server_runtime_registry import (
    MockServerRuntimeRegistry,
)

router = APIRouter(prefix="/mock-server")


@router.get("")
async def find_all_mock_servers_api():
    with managed_session() as session:
        entities = MockServerService().get_all_ordered(session)
        return [serialize_mock_server(session, entity) for entity in entities]


@router.get("/{mock_server_id}")
async def find_mock_server_by_id_api(mock_server_id: str):
    with managed_session() as session:
        entity = MockServerService().get_by_id(session, mock_server_id)
        if not entity:
            raise QualityFlowAppException(f"No mock server found with id [ {mock_server_id} ]")
        return serialize_mock_server(session, entity)


@router.post("")
async def create_mock_server_api(dto: CreateMockServerDto):
    try:
        with managed_session() as session:
            mock_server_id = create_mock_server(session, dto)
    except Exception as exc:
        raise QualityFlowAppException(str(exc)) from exc

    if dto.is_active:
        try:
            MockServerRuntimeRegistry.start_server(mock_server_id)
        except Exception as exc:
            with managed_session() as session:
                MockServerService().update(session, mock_server_id, is_active=False)
            raise QualityFlowAppException(
                f"Mock server created but failed to activate: {str(exc)}"
            ) from exc
    return {"id": mock_server_id, "message": "Mock server created"}


@router.put("")
async def update_mock_server_api(dto: UpdateMockServerDto):
    try:
        with managed_session() as session:
            update_mock_server(session, dto)
    except Exception as exc:
        raise QualityFlowAppException(str(exc)) from exc

    try:
        if dto.is_active:
            MockServerRuntimeRegistry.start_server(dto.id)
        else:
            MockServerRuntimeRegistry.stop_server(dto.id)
    except Exception as exc:
        if dto.is_active:
            with managed_session() as session:
                MockServerService().update(session, dto.id, is_active=False)
        raise QualityFlowAppException(
            f"Mock server updated but failed to update runtime state: {str(exc)}"
        ) from exc
    return {"id": dto.id, "message": "Mock server updated"}


@router.delete("/{mock_server_id}")
async def delete_mock_server_api(mock_server_id: str):
    MockServerRuntimeRegistry.remove_server(mock_server_id)
    with managed_session() as session:
        deleted = MockServerService().delete_by_id(session, mock_server_id)
        if deleted == 0:
            raise QualityFlowAppException(f"No mock server found with id [ {mock_server_id} ]")
    return {"message": "Mock server deleted"}


@router.post("/{mock_server_id}/activate")
async def activate_mock_server_api(mock_server_id: str):
    with managed_session() as session:
        entity = MockServerService().update(session, mock_server_id, is_active=True)
        if not entity:
            raise QualityFlowAppException(f"No mock server found with id [ {mock_server_id} ]")
    try:
        MockServerRuntimeRegistry.start_server(mock_server_id)
    except Exception as exc:
        with managed_session() as session:
            MockServerService().update(session, mock_server_id, is_active=False)
        raise QualityFlowAppException(f"Cannot activate mock server: {str(exc)}") from exc
    return {"id": mock_server_id, "message": "Mock server activated"}


@router.post("/{mock_server_id}/deactivate")
async def deactivate_mock_server_api(mock_server_id: str):
    with managed_session() as session:
        entity = MockServerService().update(session, mock_server_id, is_active=False)
        if not entity:
            raise QualityFlowAppException(f"No mock server found with id [ {mock_server_id} ]")
    MockServerRuntimeRegistry.stop_server(mock_server_id)
    return {"id": mock_server_id, "message": "Mock server deactivated"}
