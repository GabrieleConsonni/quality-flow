from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.suite_item_command_entity import SuiteItemOperationEntity
from _alembic.services.base_id_service import BaseIdEntityService


class SuiteItemOperationService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return SuiteItemOperationEntity

    def get_all_by_suite_item_id(
        self,
        session: Session,
        suite_item_id: str,
    ) -> list[SuiteItemOperationEntity]:
        suite_item_id_attr: InstrumentedAttribute = SuiteItemOperationEntity.suite_item_id
        return (
            session.query(SuiteItemOperationEntity)
            .filter(suite_item_id_attr == suite_item_id)
            .order_by(SuiteItemOperationEntity.order)
            .all()
        )

    def delete_by_suite_item_id(self, session: Session, suite_item_id: str) -> int:
        suite_item_id_attr: InstrumentedAttribute = SuiteItemOperationEntity.suite_item_id
        query = session.query(SuiteItemOperationEntity).filter(suite_item_id_attr == suite_item_id)
        count = 0
        for operation in query.all():
            session.delete(operation)
            count += 1
        session.flush()
        return count

