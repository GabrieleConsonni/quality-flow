from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.mock_server_entity import MockServerEntity
from _alembic.services.base_id_service import BaseIdEntityService
from mock_servers.services.alembic.mock_server_api_service import MockServerApiService
from mock_servers.services.alembic.mock_server_queue_service import MockServerQueueService


class MockServerService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return MockServerEntity

    def get_all_ordered(self, session: Session) -> list[MockServerEntity]:
        return (
            session.query(MockServerEntity)
            .order_by(MockServerEntity.description.asc(), MockServerEntity.id.asc())
            .all()
        )

    def get_all_active(self, session: Session) -> list[MockServerEntity]:
        is_active_attr: InstrumentedAttribute = MockServerEntity.is_active
        return (
            session.query(MockServerEntity)
            .filter(is_active_attr == True)  # noqa: E712
            .order_by(MockServerEntity.description.asc(), MockServerEntity.id.asc())
            .all()
        )

    def get_by_endpoint(self, session: Session, endpoint: str) -> MockServerEntity | None:
        endpoint_value = str(endpoint or "").strip().lower()
        endpoint_attr: InstrumentedAttribute = MockServerEntity.endpoint
        return (
            session.query(MockServerEntity)
            .filter(endpoint_attr == endpoint_value)
            .one_or_none()
        )

    def delete_on_cascade(self, session: Session, _id: str):
        MockServerApiService().delete_by_server_id(session, _id)
        MockServerQueueService().delete_by_server_id(session, _id)
