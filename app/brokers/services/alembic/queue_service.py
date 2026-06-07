from sqlalchemy.orm import Session, InstrumentedAttribute

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.queue_entity import QueueEntity
from _alembic.services.base_id_service import BaseIdEntityService


class QueueService(BaseIdEntityService):

    def get_entity_class(self) -> type[BaseIdEntity]:
        return QueueEntity

    def get_all_by_broker_id(self, session:Session, broker_id:str)->list[QueueEntity]:
        broker_id_attr: InstrumentedAttribute = QueueEntity.broker_id
        return session.query(QueueEntity).filter(broker_id_attr==broker_id).all()

    def delete_by_broker_id(self, session:Session,broker_id:str)->int:
        broker_id_attr: InstrumentedAttribute = QueueEntity.broker_id
        deleted = session.query(QueueEntity).filter(broker_id_attr==broker_id).delete()
        return deleted