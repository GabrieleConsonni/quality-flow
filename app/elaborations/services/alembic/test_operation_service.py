from sqlalchemy.orm import Session, InstrumentedAttribute

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.test_operation_entity import TestOperationEntity
from _alembic.services.base_id_service import BaseIdEntityService


class TestOperationService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return TestOperationEntity

    def get_all_by_test(self, session: Session, suite_test_id: str) -> list[TestOperationEntity]:
        suite_id_attr: InstrumentedAttribute = TestOperationEntity.suite_test_id
        return session.query(TestOperationEntity).filter(suite_id_attr == suite_test_id).order_by(TestOperationEntity.order).all()

    def delete_by_test_id(self, session: Session, test_id: str) -> int:
        suite_id_attr: InstrumentedAttribute = TestOperationEntity.suite_test_id
        query = session.query(TestOperationEntity).filter(suite_id_attr == test_id)
        count = 0
        for op in query.all() :
            session.delete(op)
            count += 1
        session.flush()
        return count