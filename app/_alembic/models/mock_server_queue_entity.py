from sqlalchemy import JSON, Column, ForeignKey, Numeric, Text

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.code_desc_entity import CodeDescEntity


class MockServerQueueEntity(Base, CodeDescEntity):
    __tablename__ = "mock_server_queues"
    mock_server_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.mock_servers.id", ondelete="CASCADE"),
        nullable=False,
    )
    queue_id = Column(Text, ForeignKey(f"{SCHEMA}.queues.id"), nullable=False)
    configuration_json = Column(JSON, nullable=False)
    order = Column(Numeric, nullable=False, default=0)
