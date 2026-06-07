from sqlalchemy import Column, DateTime, ForeignKey, Numeric, Text, func

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.legacy_suite_db_names import (
    SUITE_RUN_FK,
    SUITE_RUN_TABLE,
    SUITE_TEST_FK,
    SUITE_TEST_RUN_TABLE,
    TEST_CODE_COL,
    TEST_DESC_COL,
    TEST_ORDER_COL,
)


class SuiteTestExecutionEntity(Base, BaseIdEntity):
    __tablename__ = SUITE_TEST_RUN_TABLE
    suite_execution_id = Column(
        SUITE_RUN_FK,
        Text,
        ForeignKey(f"{SCHEMA}.{SUITE_RUN_TABLE}.id", ondelete="CASCADE"),
        nullable=False,
    )
    suite_test_id = Column(SUITE_TEST_FK, Text, nullable=True)
    test_description = Column(TEST_DESC_COL, Text, nullable=True)
    test_order = Column(TEST_ORDER_COL, Numeric, nullable=False, default=0)
    status = Column(Text, nullable=False, default="running")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=func.now())
    finished_at = Column(DateTime, nullable=True)
