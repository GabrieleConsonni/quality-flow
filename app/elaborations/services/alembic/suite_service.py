from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.suite_entity import SuiteEntity
from _alembic.services.base_id_service import BaseIdEntityService
from elaborations.services.alembic.suite_test_service import SuiteTestService


class SuiteService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return SuiteEntity

    def get_by_code(self, session: Session, code: str) -> SuiteEntity | None:
        normalized_code = str(code or "").strip()
        if not normalized_code:
            return None
        code_attr: InstrumentedAttribute = SuiteEntity.code
        return session.query(SuiteEntity).filter(code_attr == normalized_code).one_or_none()

    def delete_on_cascade(self, session:Session, _id):
        SuiteTestService().delete_by_suite_id(session,_id)

