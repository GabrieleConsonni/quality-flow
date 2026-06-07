from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.suite_item_execution_entity import SuiteItemExecutionEntity
from _alembic.services.base_id_service import BaseIdEntityService


class SuiteItemExecutionService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return SuiteItemExecutionEntity

    def get_all_by_execution_id(
        self,
        session: Session,
        test_suite_execution_id: str,
    ) -> list[SuiteItemExecutionEntity]:
        execution_id_attr: InstrumentedAttribute = SuiteItemExecutionEntity.test_suite_execution_id
        return (
            session.query(SuiteItemExecutionEntity)
            .filter(execution_id_attr == test_suite_execution_id)
            .order_by(SuiteItemExecutionEntity.position, SuiteItemExecutionEntity.started_at)
            .all()
        )
