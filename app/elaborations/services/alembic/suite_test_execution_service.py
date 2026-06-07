from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.suite_test_execution_entity import SuiteTestExecutionEntity
from _alembic.services.base_id_service import BaseIdEntityService


class SuiteTestExecutionService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return SuiteTestExecutionEntity

    def get_all_by_execution_id(
        self,
        session: Session,
        suite_execution_id: str,
    ) -> list[SuiteTestExecutionEntity]:
        suite_execution_id_attr: InstrumentedAttribute = (
            SuiteTestExecutionEntity.suite_execution_id
        )
        return (
            session.query(SuiteTestExecutionEntity)
            .filter(suite_execution_id_attr == suite_execution_id)
            .order_by(
                SuiteTestExecutionEntity.test_order,
                SuiteTestExecutionEntity.started_at,
                SuiteTestExecutionEntity.id,
            )
            .all()
        )
