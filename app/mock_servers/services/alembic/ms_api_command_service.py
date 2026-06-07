from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.ms_api_command_entity import MsApiOperationEntity
from _alembic.services.base_id_service import BaseIdEntityService


class MsApiOperationService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return MsApiOperationEntity

    def get_all_by_api_id(
        self,
        session: Session,
        mock_server_api_id: str,
    ) -> list[MsApiOperationEntity]:
        api_id_attr: InstrumentedAttribute = MsApiOperationEntity.mock_server_api_id
        return (
            session.query(MsApiOperationEntity)
            .filter(api_id_attr == mock_server_api_id)
            .order_by(MsApiOperationEntity.order)
            .all()
        )

    def delete_by_api_id(self, session: Session, mock_server_api_id: str) -> int:
        api_id_attr: InstrumentedAttribute = MsApiOperationEntity.mock_server_api_id
        query = session.query(MsApiOperationEntity).filter(api_id_attr == mock_server_api_id)
        count = 0
        for operation in query.all():
            session.delete(operation)
            count += 1
        session.flush()
        return count

