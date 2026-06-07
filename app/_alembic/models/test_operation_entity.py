from sqlalchemy import JSON, Column, ForeignKey, Numeric, Text

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.legacy_suite_db_names import SUITE_TEST_FK, SUITE_TEST_TABLE, TEST_CFG_COL, TEST_OP_TABLE


class TestOperationEntity(Base,BaseIdEntity):
    __tablename__ = TEST_OP_TABLE
    __test__ = False

    suite_test_id = Column(SUITE_TEST_FK, Text, ForeignKey(f"{SCHEMA}.{SUITE_TEST_TABLE}.id", ondelete="CASCADE"), nullable=False)
    code = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    operation_type = Column(Text, nullable=False)
    configuration_json = Column(TEST_CFG_COL, JSON, nullable=False)
    order = Column(Numeric, nullable=False)
