from sqlalchemy import JSON, Column, ForeignKey, Numeric, Text

from _alembic.constants import SCHEMA
from _alembic.models.base import Base
from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.legacy_suite_db_names import (
    SUITE_FK,
    SUITE_TABLE,
    SUITE_TEST_TABLE,
    TEST_CFG_COL,
    TEST_KIND_COL,
)
from elaborations.models.enums.on_failure import OnFailure


class SuiteTestEntity(Base,BaseIdEntity):
    __tablename__ = SUITE_TEST_TABLE
    suite_id = Column(SUITE_FK, Text, ForeignKey(f"{SCHEMA}.{SUITE_TABLE}.id", ondelete="CASCADE"), nullable=False)
    code = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    test_type = Column(TEST_KIND_COL, Text, nullable=False)
    configuration_json = Column(TEST_CFG_COL, JSON, nullable=False)
    order = Column(Numeric, nullable=False, default=0)
    on_failure = Column(Text, nullable=False, default=OnFailure.ABORT.value)
