from sqlalchemy import JSON, Column, ForeignKey, Numeric, Text

from _alembic.constants import SCHEMA
from _alembic.models import Base
from _alembic.models.code_desc_entity import CodeDescEntity


class MsApiOperationEntity(Base, CodeDescEntity):
    __tablename__ = "ms_api_commands"
    mock_server_api_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.mock_server_apis.id", ondelete="CASCADE"),
        nullable=False,
    )
    command_code = Column(Text, nullable=False)
    command_type = Column(Text, nullable=False, default="action")
    configuration_json = Column(JSON, nullable=False)
    order = Column(Numeric, nullable=False, default=0)

    @property
    def operation_type(self) -> str:
        return self.command_code

    @operation_type.setter
    def operation_type(self, value: str):
        self.command_code = value
