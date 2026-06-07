from sqlalchemy import Column, DateTime, ForeignKey, Numeric, Text, func

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.base_entity import BaseIdEntity


class SuiteItemOperationExecutionEntity(Base, BaseIdEntity):
    __tablename__ = "suite_item_command_executions"

    test_suite_execution_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.test_suite_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    suite_item_execution_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.suite_item_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    suite_item_id = Column(Text, nullable=True)
    suite_item_command_id = Column(Text, nullable=True)
    command_description = Column(Text, nullable=True)
    command_order = Column(Numeric, nullable=False, default=0)
    status = Column(Text, nullable=False, default="running")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=func.now())
    finished_at = Column(DateTime, nullable=True)

    @property
    def suite_item_operation_id(self) -> str | None:
        return self.suite_item_command_id

    @suite_item_operation_id.setter
    def suite_item_operation_id(self, value: str | None):
        self.suite_item_command_id = value

    @property
    def operation_description(self) -> str | None:
        return self.command_description

    @operation_description.setter
    def operation_description(self, value: str | None):
        self.command_description = value

    @property
    def operation_order(self) -> int:
        return self.command_order

    @operation_order.setter
    def operation_order(self, value: int):
        self.command_order = value
