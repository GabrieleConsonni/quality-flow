from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Text, func

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.legacy_suite_db_names import (
    SUITE_CODE_COL,
    SUITE_DESC_COL,
    SUITE_FK,
    SUITE_RUN_TABLE,
    SUITE_TABLE,
    TARGET_TEST_CODE_COL,
    TARGET_TEST_ID_COL,
)


class SuiteExecutionEntity(Base, BaseIdEntity):
    __tablename__ = SUITE_RUN_TABLE
    suite_id = Column(SUITE_FK, Text, ForeignKey(f"{SCHEMA}.{SUITE_TABLE}.id", ondelete="CASCADE"), nullable=False)
    suite_description = Column(SUITE_DESC_COL, Text, nullable=True)
    status = Column(Text, nullable=False, default="running")
    invocation_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.mock_server_invocations.id", ondelete="SET NULL"),
        nullable=True,
    )
    vars_init_json = Column(JSON, nullable=False, default=dict)
    result_json = Column(JSON, nullable=True)
    include_previous = Column(Boolean, nullable=False, default=False)
    requested_test_id = Column(TARGET_TEST_ID_COL, Text, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=func.now())
    finished_at = Column(DateTime, nullable=True)
