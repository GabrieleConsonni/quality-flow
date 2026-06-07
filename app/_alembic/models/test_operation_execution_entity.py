from sqlalchemy import Column, DateTime, ForeignKey, Numeric, Text, func

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.legacy_suite_db_names import (
    OP_LINK_COL,
    SUITE_RUN_FK,
    SUITE_RUN_TABLE,
    SUITE_TEST_FK,
    SUITE_TEST_RUN_FK,
    SUITE_TEST_RUN_TABLE,
    TEST_OP_RUN_TABLE,
)


class TestOperationExecutionEntity(Base, BaseIdEntity):
    __tablename__ = TEST_OP_RUN_TABLE
    __test__ = False

    suite_execution_id = Column(
        SUITE_RUN_FK,
        Text,
        ForeignKey(f"{SCHEMA}.{SUITE_RUN_TABLE}.id", ondelete="CASCADE"),
        nullable=False,
    )
    suite_test_execution_id = Column(
        SUITE_TEST_RUN_FK,
        Text,
        ForeignKey(f"{SCHEMA}.{SUITE_TEST_RUN_TABLE}.id", ondelete="CASCADE"),
        nullable=False,
    )
    suite_test_id = Column(SUITE_TEST_FK, Text, nullable=True)
    test_operation_id = Column(OP_LINK_COL, Text, nullable=True)
    operation_description = Column(Text, nullable=True)
    operation_order = Column(Numeric, nullable=False, default=0)
    status = Column(Text, nullable=False, default="running")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=func.now())
    finished_at = Column(DateTime, nullable=True)
