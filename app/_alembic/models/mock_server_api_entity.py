from sqlalchemy import JSON, Column, ForeignKey, Numeric, Text

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.code_desc_entity import CodeDescEntity


class MockServerApiEntity(Base, CodeDescEntity):
    __tablename__ = "mock_server_apis"
    mock_server_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.mock_servers.id", ondelete="CASCADE"),
        nullable=False,
    )
    method = Column(Text, nullable=False)
    path = Column(Text, nullable=False)
    configuration_json = Column(JSON, nullable=False)
    order = Column(Numeric, nullable=False, default=0)
