from datetime import datetime

from _alembic.services.session_context_manager import managed_session
from elaborations.services.alembic.test_suite_execution_service import (
    TestSuiteExecutionService,
)
from elaborations.services.alembic.test_suite_schedule_service import (
    TestSuiteScheduleService,
    compute_next_run_at,
    utc_now,
)
from elaborations.services.alembic.test_suite_service import TestSuiteService
from elaborations.services.test_suites.test_suite_executor_service import (
    execute_test_suite_by_id,
)
from exceptions.app_exception import QualityFlowAppException


def _build_schedule_event(schedule) -> dict:
    return {
        "trigger": {
            "type": "schedule",
            "schedule_id": str(schedule.id),
            "schedule_description": str(schedule.description or ""),
        }
    }


def _refresh_running_schedule_states(session) -> int:
    schedule_service = TestSuiteScheduleService()
    execution_service = TestSuiteExecutionService()
    updated = 0
    for schedule in schedule_service.get_running_schedules(session):
        execution_id = str(schedule.last_execution_id or "").strip()
        if not execution_id:
            continue
        execution = execution_service.get_by_id(session, execution_id)
        if not execution or str(execution.status or "").strip().lower() == "running":
            continue
        schedule_service.update_fields(
            session,
            schedule.id,
            last_status=str(execution.status or "").strip().lower() or "error",
            last_error_message=str(execution.error_message or "").strip() or None,
            updated_at=utc_now(),
        )
        updated += 1
    return updated


def _serialize_trigger_result(schedule, *, status: str, execution_id: str | None = None, message: str = "") -> dict:
    return {
        "id": str(schedule.id),
        "test_suite_id": str(schedule.test_suite_id),
        "status": status,
        "execution_id": execution_id,
        "message": message,
    }


def trigger_schedule(schedule_id: str, *, manual: bool = False, now: datetime | None = None, tenant_id: str = None) -> dict:
    current_time = now or utc_now()
    with managed_session(tenant_id) as session:
        schedule_service = TestSuiteScheduleService()
        suite_service = TestSuiteService()
        schedule = schedule_service.get_by_id(session, schedule_id)
        if not schedule:
            raise QualityFlowAppException(f"No test suite schedule found with id [ {schedule_id} ]")

        suite = suite_service.get_by_id(session, schedule.test_suite_id)
        if not suite:
            raise QualityFlowAppException(
                f"No test suite found with id [ {schedule.test_suite_id} ]"
            )

        _refresh_running_schedule_states(session)

        if not manual and not bool(schedule.active):
            return _serialize_trigger_result(
                schedule,
                status="inactive",
                message="Schedule is inactive.",
            )

        if schedule.start_at and current_time < schedule.start_at and not manual:
            return _serialize_trigger_result(
                schedule,
                status="not_due",
                message="Schedule is not within the active window yet.",
            )

        if schedule.end_at and current_time > schedule.end_at and not manual:
            schedule_service.update_fields(
                session,
                schedule.id,
                active=False,
                next_run_at=None,
                last_status="idle",
                updated_at=current_time,
            )
            return _serialize_trigger_result(
                schedule,
                status="expired",
                message="Schedule validity window has ended.",
            )

        if schedule_service.has_running_execution(session, schedule.test_suite_id):
            next_run_at = (
                compute_next_run_at(
                    active=bool(schedule.active),
                    frequency_unit=schedule.frequency_unit,
                    frequency_value=int(schedule.frequency_value),
                    start_at=schedule.start_at,
                    end_at=schedule.end_at,
                    now=current_time,
                    reference_time=current_time,
                )
                if bool(schedule.active)
                else schedule.next_run_at
            )
            schedule_service.update_fields(
                session,
                schedule.id,
                next_run_at=next_run_at,
                last_status="skipped",
                last_error_message="Skipped because the suite is already running.",
                updated_at=current_time,
            )
            return _serialize_trigger_result(
                schedule,
                status="skipped",
                message="Skipped because the suite is already running.",
            )

        try:
            execution_id = execute_test_suite_by_id(
                schedule.test_suite_id,
                run_event=_build_schedule_event(schedule),
                tenant_id=tenant_id,
            )
        except Exception as exc:
            next_run_at = (
                compute_next_run_at(
                    active=bool(schedule.active),
                    frequency_unit=schedule.frequency_unit,
                    frequency_value=int(schedule.frequency_value),
                    start_at=schedule.start_at,
                    end_at=schedule.end_at,
                    now=current_time,
                    reference_time=current_time,
                )
                if bool(schedule.active)
                else None
            )
            schedule_service.update_fields(
                session,
                schedule.id,
                next_run_at=next_run_at,
                last_status="error",
                last_error_message=str(exc),
                updated_at=current_time,
            )
            raise

        next_run_at = (
            compute_next_run_at(
                active=bool(schedule.active),
                frequency_unit=schedule.frequency_unit,
                frequency_value=int(schedule.frequency_value),
                start_at=schedule.start_at,
                end_at=schedule.end_at,
                now=current_time,
                reference_time=current_time,
            )
            if bool(schedule.active)
            else None
        )
        schedule_service.update_fields(
            session,
            schedule.id,
            next_run_at=next_run_at,
            last_run_at=current_time,
            last_status="running",
            last_execution_id=execution_id,
            last_error_message=None,
            updated_at=current_time,
        )
        return _serialize_trigger_result(
            schedule,
            status="started",
            execution_id=execution_id,
            message="Scheduled execution started.",
        )


def sync_schedule_execution_states(tenant_id: str = None) -> int:
    with managed_session(tenant_id) as session:
        return _refresh_running_schedule_states(session)


def process_due_schedules(now: datetime | None = None, tenant_id: str = None) -> list[dict]:
    current_time = now or utc_now()
    triggered_results: list[dict] = []
    sync_schedule_execution_states(tenant_id)
    with managed_session(tenant_id) as session:
        due_schedule_ids = [schedule.id for schedule in TestSuiteScheduleService().get_due_schedules(session, now=current_time)]

    for schedule_id in due_schedule_ids:
        triggered_results.append(trigger_schedule(schedule_id, manual=False, now=current_time, tenant_id=tenant_id))
    return triggered_results
