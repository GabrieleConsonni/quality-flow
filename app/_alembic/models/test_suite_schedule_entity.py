from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text, func

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity


class TestSuiteScheduleEntity(Base, BaseIdEntity):
    __tablename__ = "test_suite_schedules"

    test_suite_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.test_suites.id", ondelete="CASCADE"),
        nullable=False,
    )
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    frequency_unit = Column(Text, nullable=False)
    frequency_value = Column(Integer, nullable=False)
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    last_status = Column(Text, nullable=False, default="idle")
    last_execution_id = Column(Text, nullable=True)
    last_error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
