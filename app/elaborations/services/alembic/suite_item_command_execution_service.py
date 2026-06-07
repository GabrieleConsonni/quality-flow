from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.suite_item_command_execution_entity import (
    SuiteItemOperationExecutionEntity,
)
from _alembic.services.base_id_service import BaseIdEntityService


class SuiteItemOperationExecutionService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return SuiteItemOperationExecutionEntity

    def get_all_by_item_execution_id(
        self,
        session: Session,
        suite_item_execution_id: str,
    ) -> list[SuiteItemOperationExecutionEntity]:
        item_execution_id_attr: InstrumentedAttribute = (
            SuiteItemOperationExecutionEntity.suite_item_execution_id
        )
        return (
            session.query(SuiteItemOperationExecutionEntity)
            .filter(item_execution_id_attr == suite_item_execution_id)
            .order_by(SuiteItemOperationExecutionEntity.command_order)
            .all()
        )

