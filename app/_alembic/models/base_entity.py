import uuid

from sqlalchemy import Column, Text

from _alembic.constants import SCHEMA


class BaseIdEntity():
    __table_args__ = {"schema": SCHEMA}
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))