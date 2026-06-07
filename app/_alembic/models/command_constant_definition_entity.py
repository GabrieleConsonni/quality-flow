from sqlalchemy import Column, DateTime, Numeric, Text

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity


class CommandConstantDefinitionEntity(Base, BaseIdEntity):
    __tablename__ = "command_constant_definitions"
    __table_args__ = {"schema": SCHEMA}

    owner_type = Column(Text, nullable=False)
    suite_id = Column(Text, nullable=True)
    suite_item_id = Column(Text, nullable=True)
    mock_server_api_id = Column(Text, nullable=True)
    mock_server_queue_id = Column(Text, nullable=True)
    command_id = Column(Text, nullable=False)
    command_order = Column(Numeric, nullable=False, default=0)
    section_type = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    context_scope = Column(Text, nullable=False)
    value_type = Column(Text, nullable=False)
    declared_at_order = Column(Numeric, nullable=False, default=0)
    deleted_at_order = Column(Numeric, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
