from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.test_operation_execution_entity import TestOperationExecutionEntity
from _alembic.services.base_id_service import BaseIdEntityService


class TestOperationExecutionService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return TestOperationExecutionEntity

    def get_all_by_test_execution_id(
        self,
        session: Session,
        suite_test_execution_id: str,
    ) -> list[TestOperationExecutionEntity]:
        suite_test_execution_id_attr: InstrumentedAttribute = (
            TestOperationExecutionEntity.suite_test_execution_id
        )
        return (
            session.query(TestOperationExecutionEntity)
            .filter(suite_test_execution_id_attr == suite_test_execution_id)
            .order_by(
                TestOperationExecutionEntity.operation_order,
                TestOperationExecutionEntity.started_at,
                TestOperationExecutionEntity.id,
            )
            .all()
        )
