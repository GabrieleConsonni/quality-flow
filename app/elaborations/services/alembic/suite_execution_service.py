from sqlalchemy import desc
from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.suite_execution_entity import SuiteExecutionEntity
from _alembic.services.base_id_service import BaseIdEntityService


class SuiteExecutionService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return SuiteExecutionEntity

    def get_all_ordered(self, session: Session, limit: int = 50) -> list[SuiteExecutionEntity]:
        query = session.query(SuiteExecutionEntity).order_by(
            desc(SuiteExecutionEntity.started_at),
            desc(SuiteExecutionEntity.id),
        )
        if limit and limit > 0:
            query = query.limit(limit)
        return query.all()

    def get_all_by_suite_id(
        self,
        session: Session,
        suite_id: str,
        limit: int = 50,
    ) -> list[SuiteExecutionEntity]:
        suite_id_attr: InstrumentedAttribute = SuiteExecutionEntity.suite_id
        query = (
            session.query(SuiteExecutionEntity)
            .filter(suite_id_attr == suite_id)
            .order_by(
                desc(SuiteExecutionEntity.started_at),
                desc(SuiteExecutionEntity.id),
            )
        )
        if limit and limit > 0:
            query = query.limit(limit)
        return query.all()
