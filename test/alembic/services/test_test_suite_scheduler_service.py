from datetime import datetime, timedelta

from app._alembic.models.test_suite_entity import TestSuiteEntity
from app._alembic.models.test_suite_execution_entity import TestSuiteExecutionEntity
from app._alembic.models.test_suite_schedule_entity import TestSuiteScheduleEntity
from app._alembic.services.session_context_manager import managed_session
from app.elaborations.services.alembic.test_suite_schedule_service import (
    TestSuiteScheduleService,
)
from app.elaborations.services.alembic.test_suite_service import TestSuiteService
from app.elaborations.services.test_suite_schedules.test_suite_scheduler_service import (
    sync_schedule_execution_states,
    trigger_schedule,
)


def test_trigger_schedule_marks_schedule_running_and_stores_execution_id(alembic_container, monkeypatch):
    now = datetime(2026, 3, 16, 10, 0, 0)

    with managed_session() as session:
        test_suite_id = TestSuiteService().insert(
            session,
            TestSuiteEntity(description="scheduled suite"),
        )
        schedule_id = TestSuiteScheduleService().insert(
            session,
            TestSuiteScheduleEntity(
                test_suite_id=test_suite_id,
                description="every 5 minutes",
                active=True,
                frequency_unit="minutes",
                frequency_value=5,
                next_run_at=now,
                last_status="idle",
            ),
        )

    captured = {}

    def _fake_execute_test_suite_by_id(test_suite_id: str, *, run_event=None, vars_init=None, invocation_id=None):
        captured["test_suite_id"] = test_suite_id
        captured["run_event"] = run_event
        return "exec-001"

    monkeypatch.setattr(
        "app.elaborations.services.test_suite_schedules.test_suite_scheduler_service.execute_test_suite_by_id",
        _fake_execute_test_suite_by_id,
    )

    result = trigger_schedule(schedule_id, manual=True, now=now)

    assert result["status"] == "started"
    assert result["execution_id"] == "exec-001"
    assert captured["test_suite_id"] == test_suite_id
    assert captured["run_event"]["trigger"]["type"] == "schedule"
    assert captured["run_event"]["trigger"]["schedule_id"] == schedule_id

    with managed_session() as session:
        schedule = TestSuiteScheduleService().get_by_id(session, schedule_id)
        assert schedule.last_status == "running"
        assert schedule.last_execution_id == "exec-001"
        assert schedule.last_run_at == now
        assert schedule.next_run_at == now + timedelta(minutes=5)


def test_trigger_schedule_skips_when_suite_execution_is_already_running(alembic_container):
    now = datetime(2026, 3, 16, 10, 0, 0)

    with managed_session() as session:
        test_suite_id = TestSuiteService().insert(
            session,
            TestSuiteEntity(description="suite already running"),
        )
        TestSuiteScheduleService().insert(
            session,
            TestSuiteScheduleEntity(
                test_suite_id=test_suite_id,
                description="every 10 minutes",
                active=True,
                frequency_unit="minutes",
                frequency_value=10,
                next_run_at=now,
                last_status="idle",
            ),
        )
        schedule_id = (
            TestSuiteScheduleService().get_all_ordered(session, test_suite_id=test_suite_id)[0].id
        )
        session.add(
            TestSuiteExecutionEntity(
                id="running-exec-001",
                test_suite_id=test_suite_id,
                test_suite_description="suite already running",
                status="running",
                vars_init_json={},
                include_previous=False,
            )
        )

    result = trigger_schedule(schedule_id, manual=False, now=now)

    assert result["status"] == "skipped"

    with managed_session() as session:
        schedule = TestSuiteScheduleService().get_by_id(session, schedule_id)
        assert schedule.last_status == "skipped"
        assert "already running" in str(schedule.last_error_message or "")
        assert schedule.next_run_at == now + timedelta(minutes=10)


def test_sync_schedule_execution_states_reads_latest_execution_status(alembic_container):
    now = datetime(2026, 3, 16, 10, 0, 0)

    with managed_session() as session:
        test_suite_id = TestSuiteService().insert(
            session,
            TestSuiteEntity(description="suite finished"),
        )
        session.add(
            TestSuiteExecutionEntity(
                id="exec-finished-001",
                test_suite_id=test_suite_id,
                test_suite_description="suite finished",
                status="success",
                vars_init_json={},
                include_previous=False,
                finished_at=now,
            )
        )
        schedule_id = TestSuiteScheduleService().insert(
            session,
            TestSuiteScheduleEntity(
                test_suite_id=test_suite_id,
                description="sync state",
                active=True,
                frequency_unit="hours",
                frequency_value=1,
                next_run_at=now + timedelta(hours=1),
                last_status="running",
                last_execution_id="exec-finished-001",
            ),
        )

    updated = sync_schedule_execution_states()

    assert updated == 1

    with managed_session() as session:
        schedule = TestSuiteScheduleService().get_by_id(session, schedule_id)
        assert schedule.last_status == "success"
