from _alembic.models import Base
from _alembic.models.code_desc_entity import CodeDescEntity


class TestSuiteEntity(Base, CodeDescEntity):
    __test__ = False

    __tablename__ = "test_suites"
