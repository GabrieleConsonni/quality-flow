from sqlalchemy import Column, Text, func, JSON, DateTime

from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType


class LogEntity(Base,BaseIdEntity):
    __tablename__ = "logs"
    subject_type = Column(Text, nullable=False, default=LogSubjectType.SERVICE.value)
    subject = Column(Text, nullable=False)
    level = Column(Text, nullable=False, default=LogLevel.INFO.value)
    message = Column(Text, nullable=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())