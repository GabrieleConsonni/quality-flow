from sqlalchemy import Column, Text, JSON

from _alembic.models import Base
from _alembic.models.code_desc_entity import CodeDescEntity


class QueueEntity(Base,CodeDescEntity):
    __tablename__ = "queues"
    code = Column(Text, nullable=False)
    broker_id = Column(Text, nullable=False)
    configuration_json = Column(JSON, nullable=False)



