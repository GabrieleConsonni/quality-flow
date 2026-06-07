from sqlalchemy.orm import Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.test_suite_entity import TestSuiteEntity
from _alembic.services.base_id_service import BaseIdEntityService
from elaborations.services.alembic.suite_item_service import SuiteItemService


class TestSuiteService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return TestSuiteEntity

    def delete_on_cascade(self, session: Session, _id: str):
        SuiteItemService().delete_by_suite_id(session, _id)
