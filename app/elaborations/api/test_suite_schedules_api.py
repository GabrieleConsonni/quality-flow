from fastapi import APIRouter, Query

from _alembic.models.test_suite_schedule_entity import TestSuiteScheduleEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.models.dtos.test_suite_schedule_dto import (
    CreateTestSuiteScheduleDto,
    UpdateTestSuiteScheduleDto,
)
from elaborations.services.alembic.test_suite_schedule_service import (
    TestSuiteScheduleService,
    compute_next_run_at,
    utc_now,
)
from elaborations.services.alembic.test_suite_service import TestSuiteService
from elaborations.services.test_suite_schedules.test_suite_scheduler_service import (
    trigger_schedule,
)
from exceptions.app_exception import QualityFlowAppException

router = APIRouter(prefix="/elaborations")


def _serialize_test_suite_schedule(entity: TestSuiteScheduleEntity, suite_description: str = "") -> dict:
    return {
        "id": entity.id,
        "test_suite_id": entity.test_suite_id,
        "test_suite_description": suite_description,
        "description": entity.description,
        "active": bool(entity.active),
        "frequency_unit": entity.frequency_unit,
        "frequency_value": int(entity.frequency_value),
        "start_at": entity.start_at,
        "end_at": entity.end_at,
        "next_run_at": entity.next_run_at,
        "last_run_at": entity.last_run_at,
        "last_status": entity.last_status,
        "last_execution_id": entity.last_execution_id,
        "last_error_message": entity.last_error_message,
        "created_at": entity.created_at,
        "updated_at": entity.updated_at,
    }


def _get_suite_descriptions(session) -> dict[str, str]:
    return {
        str(suite.id): str(suite.description or "")
        for suite in TestSuiteService().get_all(session)
    }


def _build_schedule_entity(dto: CreateTestSuiteScheduleDto) -> TestSuiteScheduleEntity:
    current_time = utc_now()
    next_run_at = compute_next_run_at(
        active=bool(dto.active),
        frequency_unit=dto.frequency_unit.value,
        frequency_value=int(dto.frequency_value),
        start_at=dto.start_at,
        end_at=dto.end_at,
        now=current_time,
    )
    return TestSuiteScheduleEntity(
        test_suite_id=dto.test_suite_id,
        description=dto.description,
        active=bool(dto.active),
        frequency_unit=dto.frequency_unit.value,
        frequency_value=int(dto.frequency_value),
        start_at=dto.start_at,
        end_at=dto.end_at,
        next_run_at=next_run_at,
        last_status="idle",
        last_execution_id=None,
        last_error_message=None,
    )


@router.get("/test-suite-schedule")
async def find_all_test_suite_schedules_api(
    test_suite_id: str | None = Query(default=None),
):
    with managed_session() as session:
        schedule_service = TestSuiteScheduleService()
        suite_descriptions = _get_suite_descriptions(session)
        schedules = schedule_service.get_all_ordered(session, test_suite_id=test_suite_id)
        return [
            _serialize_test_suite_schedule(
                entity,
                suite_descriptions.get(str(entity.test_suite_id), ""),
            )
            for entity in schedules
        ]


@router.get("/test-suite-schedule/{schedule_id}")
async def find_test_suite_schedule_api(schedule_id: str):
    with managed_session() as session:
        entity = TestSuiteScheduleService().get_by_id(session, schedule_id)
        if not entity:
            raise QualityFlowAppException(f"No test suite schedule found with id [ {schedule_id} ]")
        suite = TestSuiteService().get_by_id(session, entity.test_suite_id)
        return _serialize_test_suite_schedule(entity, str((suite.description if suite else "") or ""))


@router.post("/test-suite-schedule")
async def insert_test_suite_schedule_api(dto: CreateTestSuiteScheduleDto):
    with managed_session() as session:
        suite = TestSuiteService().get_by_id(session, dto.test_suite_id)
        if not suite:
            raise QualityFlowAppException(f"No test suite found with id [ {dto.test_suite_id} ]")
        entity = _build_schedule_entity(dto)
        schedule_id = TestSuiteScheduleService().insert(session, entity)
        created = TestSuiteScheduleService().get_by_id(session, schedule_id)
        return _serialize_test_suite_schedule(created, str(suite.description or ""))


@router.put("/test-suite-schedule")
async def update_test_suite_schedule_api(dto: UpdateTestSuiteScheduleDto):
    with managed_session() as session:
        suite = TestSuiteService().get_by_id(session, dto.test_suite_id)
        if not suite:
            raise QualityFlowAppException(f"No test suite found with id [ {dto.test_suite_id} ]")

        schedule_service = TestSuiteScheduleService()
        entity = schedule_service.get_by_id(session, dto.id)
        if not entity:
            raise QualityFlowAppException(f"No test suite schedule found with id [ {dto.id} ]")

        next_run_at = compute_next_run_at(
            active=bool(dto.active),
            frequency_unit=dto.frequency_unit.value,
            frequency_value=int(dto.frequency_value),
            start_at=dto.start_at,
            end_at=dto.end_at,
            now=utc_now(),
        )
        updated = schedule_service.update_fields(
            session,
            dto.id,
            test_suite_id=dto.test_suite_id,
            description=dto.description,
            active=bool(dto.active),
            frequency_unit=dto.frequency_unit.value,
            frequency_value=int(dto.frequency_value),
            start_at=dto.start_at,
            end_at=dto.end_at,
            next_run_at=next_run_at,
            updated_at=utc_now(),
        )
        return _serialize_test_suite_schedule(updated, str(suite.description or ""))


@router.delete("/test-suite-schedule/{schedule_id}")
async def delete_test_suite_schedule_api(schedule_id: str):
    with managed_session() as session:
        deleted = TestSuiteScheduleService().delete_by_id(session, schedule_id)
        if deleted == 0:
            raise QualityFlowAppException(f"No test suite schedule found with id [ {schedule_id} ]")
        return {"message": f"{deleted} test suite schedule(s) deleted"}


@router.post("/test-suite-schedule/{schedule_id}/activate")
async def activate_test_suite_schedule_api(schedule_id: str):
    with managed_session() as session:
        schedule_service = TestSuiteScheduleService()
        schedule = schedule_service.get_by_id(session, schedule_id)
        if not schedule:
            raise QualityFlowAppException(f"No test suite schedule found with id [ {schedule_id} ]")

        next_run_at = compute_next_run_at(
            active=True,
            frequency_unit=schedule.frequency_unit,
            frequency_value=int(schedule.frequency_value),
            start_at=schedule.start_at,
            end_at=schedule.end_at,
            now=utc_now(),
        )
        updated = schedule_service.update_fields(
            session,
            schedule_id,
            active=True,
            next_run_at=next_run_at,
            updated_at=utc_now(),
        )
        suite = TestSuiteService().get_by_id(session, updated.test_suite_id)
        return _serialize_test_suite_schedule(updated, str((suite.description if suite else "") or ""))


@router.post("/test-suite-schedule/{schedule_id}/deactivate")
async def deactivate_test_suite_schedule_api(schedule_id: str):
    with managed_session() as session:
        schedule_service = TestSuiteScheduleService()
        schedule = schedule_service.get_by_id(session, schedule_id)
        if not schedule:
            raise QualityFlowAppException(f"No test suite schedule found with id [ {schedule_id} ]")

        updated = schedule_service.update_fields(
            session,
            schedule_id,
            active=False,
            next_run_at=None,
            updated_at=utc_now(),
        )
        suite = TestSuiteService().get_by_id(session, updated.test_suite_id)
        return _serialize_test_suite_schedule(updated, str((suite.description if suite else "") or ""))


@router.post("/test-suite-schedule/{schedule_id}/run-now")
async def run_test_suite_schedule_now_api(schedule_id: str):
    result = trigger_schedule(schedule_id, manual=True)
    return {
        "message": result["message"],
        "execution_id": result["execution_id"],
        "status": result["status"],
    }
