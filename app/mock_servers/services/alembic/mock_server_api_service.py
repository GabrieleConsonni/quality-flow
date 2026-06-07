from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.mock_server_api_entity import MockServerApiEntity
from _alembic.services.base_id_service import BaseIdEntityService
from mock_servers.services.alembic.ms_api_command_service import MsApiOperationService


class MockServerApiService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return MockServerApiEntity

    def get_all_by_server_id(
        self,
        session: Session,
        mock_server_id: str,
    ) -> list[MockServerApiEntity]:
        server_id_attr: InstrumentedAttribute = MockServerApiEntity.mock_server_id
        return (
            session.query(MockServerApiEntity)
            .filter(server_id_attr == mock_server_id)
            .order_by(MockServerApiEntity.order)
            .all()
        )

    def delete_by_server_id(self, session: Session, mock_server_id: str) -> int:
        server_id_attr: InstrumentedAttribute = MockServerApiEntity.mock_server_id
        query = session.query(MockServerApiEntity).filter(server_id_attr == mock_server_id)
        count = 0
        for api_entry in query.all():
            self.delete_on_cascade(session, api_entry.id)
            session.delete(api_entry)
            count += 1
        session.flush()
        return count

    def delete_on_cascade(self, session: Session, _id: str):
        MsApiOperationService().delete_by_api_id(session, _id)

