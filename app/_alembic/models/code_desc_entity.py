from sqlalchemy import Column, Text

from _alembic.models.base_entity import BaseIdEntity


class CodeDescEntity(BaseIdEntity):
    description = Column(Text, nullable=True )
