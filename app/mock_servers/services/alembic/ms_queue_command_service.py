from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.ms_queue_command_entity import MsQueueOperationEntity
from _alembic.services.base_id_service import BaseIdEntityService


class MsQueueOperationService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return MsQueueOperationEntity

    def get_all_by_queue_binding_id(
        self,
        session: Session,
        mock_server_queue_id: str,
    ) -> list[MsQueueOperationEntity]:
        queue_id_attr: InstrumentedAttribute = MsQueueOperationEntity.mock_server_queue_id
        return (
            session.query(MsQueueOperationEntity)
            .filter(queue_id_attr == mock_server_queue_id)
            .order_by(MsQueueOperationEntity.order)
            .all()
        )

    def delete_by_queue_binding_id(self, session: Session, mock_server_queue_id: str) -> int:
        queue_id_attr: InstrumentedAttribute = MsQueueOperationEntity.mock_server_queue_id
        query = session.query(MsQueueOperationEntity).filter(
            queue_id_attr == mock_server_queue_id
        )
        count = 0
        for operation in query.all():
            session.delete(operation)
            count += 1
        session.flush()
        return count

