from sqlalchemy import Column, DateTime, JSON, func

from _alembic.models import Base
from _alembic.models.code_desc_entity import CodeDescEntity


class DatasetEntity(Base, CodeDescEntity):
    __tablename__ = "datasets"

    configuration_json = Column(JSON, nullable=False)
    perimeter = Column(JSON, nullable=True)
    created_date = Column(DateTime, nullable=False, default=func.now())
    modified_date = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
