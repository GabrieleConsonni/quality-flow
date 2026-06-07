from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.suite_item_entity import SuiteItemEntity
from _alembic.services.base_id_service import BaseIdEntityService
from elaborations.models.enums.suite_item_kind import SuiteItemKind
from elaborations.services.alembic.suite_item_command_service import (
    SuiteItemOperationService,
)


class SuiteItemService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return SuiteItemEntity

    def get_all_by_suite_id(self, session: Session, test_suite_id: str) -> list[SuiteItemEntity]:
        test_suite_id_attr: InstrumentedAttribute = SuiteItemEntity.test_suite_id
        return (
            session.query(SuiteItemEntity)
            .filter(test_suite_id_attr == test_suite_id)
            .order_by(SuiteItemEntity.position, SuiteItemEntity.id)
            .all()
        )

    def get_all_tests_by_suite_id(
        self,
        session: Session,
        test_suite_id: str,
    ) -> list[SuiteItemEntity]:
        return [
            item
            for item in self.get_all_by_suite_id(session, test_suite_id)
            if str(item.kind or "") == SuiteItemKind.TEST.value
        ]

    def get_hook_by_phase(
        self,
        session: Session,
        test_suite_id: str,
        hook_phase: str,
    ) -> SuiteItemEntity | None:
        test_suite_id_attr: InstrumentedAttribute = SuiteItemEntity.test_suite_id
        kind_attr: InstrumentedAttribute = SuiteItemEntity.kind
        hook_phase_attr: InstrumentedAttribute = SuiteItemEntity.hook_phase
        return (
            session.query(SuiteItemEntity)
            .filter(test_suite_id_attr == test_suite_id)
            .filter(kind_attr == SuiteItemKind.HOOK.value)
            .filter(hook_phase_attr == str(hook_phase or "").strip())
            .one_or_none()
        )

    def delete_by_suite_id(self, session: Session, test_suite_id: str) -> int:
        suite_id_attr: InstrumentedAttribute = SuiteItemEntity.test_suite_id
        query = session.query(SuiteItemEntity).filter(suite_id_attr == test_suite_id)
        items = query.all()
        count = 0
        for item in items:
            self.delete_on_cascade(session, item.id)
            session.delete(item)
            count += 1
        session.flush()
        return count

    def delete_on_cascade(self, session: Session, _id: str):
        SuiteItemOperationService().delete_by_suite_item_id(session, _id)

