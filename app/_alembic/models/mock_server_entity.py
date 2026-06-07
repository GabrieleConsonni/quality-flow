from sqlalchemy import Boolean, Column, JSON, Text

from _alembic.models import Base
from _alembic.models.code_desc_entity import CodeDescEntity


class MockServerEntity(Base, CodeDescEntity):
    __tablename__ = "mock_servers"
    endpoint = Column(Text, nullable=False, unique=True)
    configuration_json = Column(JSON, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
