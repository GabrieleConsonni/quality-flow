import math
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.test_suite_execution_entity import TestSuiteExecutionEntity
from _alembic.services.base_id_service import BaseIdEntityService


class TestSuiteExecutionService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return TestSuiteExecutionEntity

    def _build_filtered_query(
        self,
        session: Session,
        *,
        test_suite_id: str | None = None,
        status: str | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
    ):
        query = session.query(TestSuiteExecutionEntity)

        suite_id = str(test_suite_id or "").strip()
        if suite_id:
            suite_id_attr: InstrumentedAttribute = TestSuiteExecutionEntity.test_suite_id
            query = query.filter(suite_id_attr == suite_id)

        normalized_status = str(status or "").strip().lower()
        if normalized_status:
            status_attr: InstrumentedAttribute = TestSuiteExecutionEntity.status
            query = query.filter(status_attr == normalized_status)

        if started_from is not None:
            query = query.filter(TestSuiteExecutionEntity.started_at >= started_from)

        if started_to is not None:
            query = query.filter(TestSuiteExecutionEntity.started_at <= started_to)

        return query

    def get_all_ordered(self, session: Session, limit: int = 50) -> list[TestSuiteExecutionEntity]:
        return (
            self._build_filtered_query(session)
            .order_by(desc(TestSuiteExecutionEntity.started_at), desc(TestSuiteExecutionEntity.id))
            .limit(limit)
            .all()
        )

    def get_all_by_suite_id(
        self,
        session: Session,
        test_suite_id: str,
        limit: int = 50,
    ) -> list[TestSuiteExecutionEntity]:
        return (
            self._build_filtered_query(session, test_suite_id=test_suite_id)
            .order_by(desc(TestSuiteExecutionEntity.started_at), desc(TestSuiteExecutionEntity.id))
            .limit(limit)
            .all()
        )

    def search(
        self,
        session: Session,
        *,
        test_suite_id: str | None = None,
        status: str | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
        page_size: int = 20,
        page_number: int = 1,
    ) -> tuple[list[TestSuiteExecutionEntity], int, int]:
        page_size_value = max(int(page_size or 20), 1)
        page_number_value = max(int(page_number or 1), 1)

        query = self._build_filtered_query(
            session,
            test_suite_id=test_suite_id,
            status=status,
            started_from=started_from,
            started_to=started_to,
        )
        total = query.count()
        total_pages = max(1, math.ceil(total / page_size_value))
        resolved_page_number = min(page_number_value, total_pages)
        offset = (resolved_page_number - 1) * page_size_value
        items = (
            query.order_by(desc(TestSuiteExecutionEntity.started_at), desc(TestSuiteExecutionEntity.id))
            .offset(offset)
            .limit(page_size_value)
            .all()
        )
        return items, total, resolved_page_number
