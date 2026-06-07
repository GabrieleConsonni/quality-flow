from datetime import datetime

from app._alembic.models.test_suite_entity import TestSuiteEntity
from app._alembic.models.test_suite_execution_entity import TestSuiteExecutionEntity as SuiteExecutionEntity
from app._alembic.services.session_context_manager import managed_session
from app.elaborations.services.alembic.test_suite_execution_service import (
    TestSuiteExecutionService,
)
from app.elaborations.services.alembic.test_suite_service import TestSuiteService


def _insert_execution(
    session,
    *,
    execution_id: str,
    test_suite_id: str,
    status: str,
    started_at: datetime,
):
    TestSuiteExecutionService().insert(
        session,
        SuiteExecutionEntity(
            id=execution_id,
            test_suite_id=test_suite_id,
            test_suite_description=f"suite-{test_suite_id}",
            status=status,
            vars_init_json={},
            include_previous=False,
            error_message=None,
            started_at=started_at,
            finished_at=started_at,
        ),
    )


def test_search_filters_by_suite_status_and_started_at(alembic_container):
    with managed_session() as session:
        suite_alpha = TestSuiteService().insert(session, TestSuiteEntity(description="Suite Alpha"))
        suite_beta = TestSuiteService().insert(session, TestSuiteEntity(description="Suite Beta"))
        _insert_execution(
            session,
            execution_id="exec-alpha-1",
            test_suite_id=suite_alpha,
            status="success",
            started_at=datetime(2026, 3, 20, 10, 0, 0),
        )
        _insert_execution(
            session,
            execution_id="exec-alpha-2",
            test_suite_id=suite_alpha,
            status="error",
            started_at=datetime(2026, 3, 21, 10, 0, 0),
        )
        _insert_execution(
            session,
            execution_id="exec-beta-1",
            test_suite_id=suite_beta,
            status="success",
            started_at=datetime(2026, 3, 21, 12, 0, 0),
        )

    with managed_session() as session:
        items, total, resolved_page_number = TestSuiteExecutionService().search(
            session,
            test_suite_id=suite_alpha,
            status="error",
            started_from=datetime(2026, 3, 21, 0, 0, 0),
            started_to=datetime(2026, 3, 21, 23, 59, 59),
            page_size=10,
            page_number=1,
        )
        item_ids = [item.id for item in items]

    assert total == 1
    assert resolved_page_number == 1
    assert item_ids == ["exec-alpha-2"]


def test_search_orders_by_started_at_desc_and_id_desc_with_pagination(alembic_container):
    with managed_session() as session:
        suite_id = TestSuiteService().insert(session, TestSuiteEntity(description="Suite Ordered"))
        _insert_execution(
            session,
            execution_id="exec-001",
            test_suite_id=suite_id,
            status="success",
            started_at=datetime(2026, 3, 19, 9, 0, 0),
        )
        _insert_execution(
            session,
            execution_id="exec-aaa",
            test_suite_id=suite_id,
            status="success",
            started_at=datetime(2026, 3, 20, 9, 0, 0),
        )
        _insert_execution(
            session,
            execution_id="exec-zzz",
            test_suite_id=suite_id,
            status="success",
            started_at=datetime(2026, 3, 20, 9, 0, 0),
        )

    with managed_session() as session:
        page_one, total, resolved_page_one = TestSuiteExecutionService().search(
            session,
            test_suite_id=suite_id,
            page_size=2,
            page_number=1,
        )
        page_two, _, resolved_page_two = TestSuiteExecutionService().search(
            session,
            test_suite_id=suite_id,
            page_size=2,
            page_number=2,
        )
        page_one_ids = [item.id for item in page_one]
        page_two_ids = [item.id for item in page_two]

    assert total == 3
    assert resolved_page_one == 1
    assert resolved_page_two == 2
    assert page_one_ids == ["exec-zzz", "exec-aaa"]
    assert page_two_ids == ["exec-001"]


def test_search_clamps_page_number_to_last_available_page(alembic_container):
    with managed_session() as session:
        suite_id = TestSuiteService().insert(session, TestSuiteEntity(description="Suite Clamp"))
        _insert_execution(
            session,
            execution_id="exec-clamp-1",
            test_suite_id=suite_id,
            status="success",
            started_at=datetime(2026, 3, 21, 9, 0, 0),
        )

    with managed_session() as session:
        items, total, resolved_page_number = TestSuiteExecutionService().search(
            session,
            test_suite_id=suite_id,
            page_size=20,
            page_number=99,
        )
        item_ids = [item.id for item in items]

    assert total == 1
    assert resolved_page_number == 1
    assert item_ids == ["exec-clamp-1"]
