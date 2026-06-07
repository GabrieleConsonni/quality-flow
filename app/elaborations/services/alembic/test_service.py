from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.test_entity import TestEntity
from _alembic.services.base_id_service import BaseIdEntityService
from sqlalchemy import or_
from sqlalchemy.orm import Session

class TestService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return TestEntity

    def get_filtered_query(self, session: Session, search: str = ""):
        query = session.query(TestEntity)
        search_value = str(search or "").strip()
        if search_value:
            search_pattern = f"%{search_value}%"
            query = query.filter(
                or_(
                    TestEntity.code.ilike(search_pattern),
                    TestEntity.description.ilike(search_pattern),
                )
            )
        return query.order_by(TestEntity.code.asc())
