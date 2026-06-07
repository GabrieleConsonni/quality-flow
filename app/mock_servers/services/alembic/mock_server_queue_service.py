from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.mock_server_queue_entity import MockServerQueueEntity
from _alembic.services.base_id_service import BaseIdEntityService
from mock_servers.services.alembic.ms_queue_command_service import (
    MsQueueOperationService,
)


class MockServerQueueService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return MockServerQueueEntity

    def get_all_by_server_id(
        self,
        session: Session,
        mock_server_id: str,
    ) -> list[MockServerQueueEntity]:
        server_id_attr: InstrumentedAttribute = MockServerQueueEntity.mock_server_id
        return (
            session.query(MockServerQueueEntity)
            .filter(server_id_attr == mock_server_id)
            .order_by(MockServerQueueEntity.order)
            .all()
        )

    def delete_by_server_id(self, session: Session, mock_server_id: str) -> int:
        server_id_attr: InstrumentedAttribute = MockServerQueueEntity.mock_server_id
        query = session.query(MockServerQueueEntity).filter(server_id_attr == mock_server_id)
        count = 0
        for queue_entry in query.all():
            self.delete_on_cascade(session, queue_entry.id)
            session.delete(queue_entry)
            count += 1
        session.flush()
        return count

    def delete_on_cascade(self, session: Session, _id: str):
        MsQueueOperationService().delete_by_queue_binding_id(session, _id)

