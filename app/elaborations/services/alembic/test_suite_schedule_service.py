from datetime import UTC, datetime, timedelta

from sqlalchemy import asc
from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.test_suite_execution_entity import TestSuiteExecutionEntity
from _alembic.models.test_suite_schedule_entity import TestSuiteScheduleEntity
from _alembic.services.base_id_service import BaseIdEntityService
from elaborations.models.enums.schedule_frequency_unit import ScheduleFrequencyUnit
from exceptions.app_exception import QualityFlowAppException


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def compute_next_run_at(
    *,
    active: bool,
    frequency_unit: str,
    frequency_value: int,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    now: datetime | None = None,
    reference_time: datetime | None = None,
) -> datetime | None:
    if not active:
        return None

    current_time = now or utc_now()
    normalized_unit = str(frequency_unit or "").strip().lower()
    normalized_value = int(frequency_value or 0)
    if normalized_value <= 0:
        raise QualityFlowAppException("frequency_value must be greater than zero.")

    if start_at and end_at and start_at >= end_at:
        raise QualityFlowAppException("start_at must be earlier than end_at.")

    if normalized_unit == ScheduleFrequencyUnit.MINUTES.value:
        delta = timedelta(minutes=normalized_value)
    elif normalized_unit == ScheduleFrequencyUnit.HOURS.value:
        delta = timedelta(hours=normalized_value)
    elif normalized_unit == ScheduleFrequencyUnit.DAYS.value:
        delta = timedelta(days=normalized_value)
    else:
        raise QualityFlowAppException(f"Unsupported frequency unit '{frequency_unit}'.")

    if reference_time is None and start_at and start_at > current_time:
        candidate = start_at
    else:
        base_time = reference_time or current_time
        candidate = base_time + delta
        if start_at and candidate < start_at:
            candidate = start_at

    if end_at and candidate > end_at:
        return None

    return candidate


class TestSuiteScheduleService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return TestSuiteScheduleEntity

    def update_fields(self, session: Session, _id: str, **kwargs) -> TestSuiteScheduleEntity | None:
        entity = self.get_by_id(session, _id)
        if not entity:
            return None
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        session.flush()
        return entity

    def get_all_ordered(
        self,
        session: Session,
        test_suite_id: str | None = None,
    ) -> list[TestSuiteScheduleEntity]:
        query = session.query(TestSuiteScheduleEntity)
        normalized_suite_id = str(test_suite_id or "").strip()
        if normalized_suite_id:
            suite_id_attr: InstrumentedAttribute = TestSuiteScheduleEntity.test_suite_id
            query = query.filter(suite_id_attr == normalized_suite_id)
        return (
            query.order_by(
                asc(TestSuiteScheduleEntity.test_suite_id),
                asc(TestSuiteScheduleEntity.description),
                asc(TestSuiteScheduleEntity.id),
            )
            .all()
        )

    def get_due_schedules(
        self,
        session: Session,
        *,
        now: datetime | None = None,
    ) -> list[TestSuiteScheduleEntity]:
        current_time = now or utc_now()
        return (
            session.query(TestSuiteScheduleEntity)
            .filter(TestSuiteScheduleEntity.active.is_(True))
            .filter(TestSuiteScheduleEntity.next_run_at.is_not(None))
            .filter(TestSuiteScheduleEntity.next_run_at <= current_time)
            .order_by(asc(TestSuiteScheduleEntity.next_run_at), asc(TestSuiteScheduleEntity.id))
            .all()
        )

    def get_running_schedules(self, session: Session) -> list[TestSuiteScheduleEntity]:
        return (
            session.query(TestSuiteScheduleEntity)
            .filter(TestSuiteScheduleEntity.last_status == "running")
            .filter(TestSuiteScheduleEntity.last_execution_id.is_not(None))
            .order_by(asc(TestSuiteScheduleEntity.updated_at), asc(TestSuiteScheduleEntity.id))
            .all()
        )

    def has_running_execution(self, session: Session, test_suite_id: str) -> bool:
        return (
            session.query(TestSuiteExecutionEntity)
            .filter(TestSuiteExecutionEntity.test_suite_id == test_suite_id)
            .filter(TestSuiteExecutionEntity.status == "running")
            .first()
            is not None
        )
