from sqlalchemy import JSON, Column, ForeignKey, Numeric, Text

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity


class SuiteItemOperationEntity(Base, BaseIdEntity):
    __tablename__ = "suite_item_commands"

    suite_item_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.suite_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    description = Column(Text, nullable=True)
    command_code = Column(Text, nullable=False)
    command_type = Column(Text, nullable=False, default="action")
    configuration_json = Column(JSON, nullable=False)
    order = Column(Numeric, nullable=False)

    @property
    def operation_type(self) -> str:
        return self.command_code

    @operation_type.setter
    def operation_type(self, value: str):
        self.command_code = value
