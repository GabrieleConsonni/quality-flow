from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.mock_server_invocation_entity import MockServerInvocationEntity
from _alembic.services.base_id_service import BaseIdEntityService


class MockServerInvocationService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return MockServerInvocationEntity

    def get_all_by_server_id(
        self,
        session: Session,
        mock_server_id: str,
    ) -> list[MockServerInvocationEntity]:
        server_id_attr: InstrumentedAttribute = MockServerInvocationEntity.mock_server_id
        return (
            session.query(MockServerInvocationEntity)
            .filter(server_id_attr == mock_server_id)
            .order_by(
                MockServerInvocationEntity.created_at.desc(),
                MockServerInvocationEntity.id.desc(),
            )
            .all()
        )
