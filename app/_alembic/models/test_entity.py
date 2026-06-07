from sqlalchemy import Column, Text, JSON

from _alembic.models import Base
from _alembic.models.code_desc_entity import CodeDescEntity
from _alembic.models.legacy_suite_db_names import TEST_CFG_COL, TEST_DEF_TABLE, TEST_KIND_COL


class TestEntity(Base,CodeDescEntity):
    __tablename__ = TEST_DEF_TABLE
    __test__ = False

    code = Column(Text, nullable=False)
    test_type = Column(TEST_KIND_COL, Text, nullable=False)
    configuration_json = Column(TEST_CFG_COL, JSON, nullable=False)
