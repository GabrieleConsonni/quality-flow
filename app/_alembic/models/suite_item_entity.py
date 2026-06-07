from sqlalchemy import JSON, Boolean, Column, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB

from _alembic.constants import SCHEMA
from _alembic.models.base import Base
from _alembic.models.base_entity import BaseIdEntity
from elaborations.models.enums.on_failure import OnFailure
from elaborations.models.enums.suite_item_kind import SuiteItemKind
from elaborations.models.enums.suite_item_role import SuiteItemRole
from elaborations.models.enums.template_kind import TemplateKind


class SuiteItemEntity(Base, BaseIdEntity):
    __tablename__ = "suite_items"

    test_suite_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.test_suites.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind = Column(Text, nullable=False, default=SuiteItemKind.TEST.value)
    hook_phase = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    sources_json = Column(JSON, nullable=False, default=list)
    position = Column(Numeric, nullable=False, default=0)
    on_failure = Column(Text, nullable=False, default=OnFailure.ABORT.value)

    role = Column(Text, nullable=False, default=SuiteItemRole.TEST.value)
    template_kind = Column(Text, nullable=False, default=TemplateKind.CUSTOM.value)
    template_config = Column(JSONB, nullable=True)
    data_driven = Column(Boolean, nullable=False, default=False)
    dataset_id = Column(
        Text,
        ForeignKey(f"{SCHEMA}.json_payloads.id", ondelete="SET NULL"),
        nullable=True,
    )
