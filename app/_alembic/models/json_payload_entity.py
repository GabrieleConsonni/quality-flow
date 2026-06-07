from sqlalchemy import Column, Text, DateTime, func, JSON

from _alembic.models import Base
from _alembic.models.code_desc_entity import CodeDescEntity


class JsonPayloadEntity(Base,CodeDescEntity):
    __tablename__ = "json_payloads"
    json_type = Column(Text, nullable=False )
    payload = Column(JSON, nullable=False )
    created_date = Column(DateTime, nullable=False, default=func.now())
    modified_date = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())