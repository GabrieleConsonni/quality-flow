from sqlalchemy.orm import Session, InstrumentedAttribute

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.suite_test_entity import SuiteTestEntity
from _alembic.services.base_id_service import BaseIdEntityService
from elaborations.services.alembic.test_operation_service import TestOperationService


class SuiteTestService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return SuiteTestEntity

    def get_all_by_suite_id(self,session:Session,suite_id:str)->list[SuiteTestEntity]:
        suite_id_attr: InstrumentedAttribute = SuiteTestEntity.suite_id
        return session.query(SuiteTestEntity).filter(suite_id_attr==suite_id).order_by(SuiteTestEntity.order).all()

    def delete_by_suite_id(self, session:Session, suite_id:str)->int:
        suite_id_attr: InstrumentedAttribute = SuiteTestEntity.suite_id
        query = session.query(SuiteTestEntity).filter(suite_id_attr == suite_id)
        tests = query.all()
        count = 0
        for test in tests :
            self.delete_on_cascade(session,test.id)
            session.delete(test)
            count += 1
        session.flush()
        return count

    def delete_on_cascade(self, session: Session, _id: str):
        TestOperationService().delete_by_test_id(session,_id)

