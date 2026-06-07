from sqlalchemy import Column, Text

from _alembic.models import Base
from _alembic.models.code_desc_entity import CodeDescEntity
from _alembic.models.legacy_suite_db_names import SUITE_TABLE


class SuiteEntity(Base,CodeDescEntity):
    __tablename__ = SUITE_TABLE
    code = Column(Text, nullable=False)
