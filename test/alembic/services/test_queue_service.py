from app._alembic.models.queue_entity import QueueEntity
from app._alembic.services.session_context_manager import managed_session
from app.brokers.services.alembic.queue_service import QueueService


def test_queue_service(alembic_container):
    inserted_queues : list[str] = []

    service = QueueService()

    with managed_session() as session:
        inserted_queues.append(service.insert(session, QueueEntity(
            code='queue_1',
            broker_id='broker_123',
            configuration_json={"key": "value1"}
        )))
        inserted_queues.append(service.insert(session, QueueEntity(
            code='queue_2',
            broker_id='broker_123',
            configuration_json={"key": "value2"}
        )))
        inserted_queues.append(service.insert(session, QueueEntity(
            code='queue_3',
            broker_id='broker_789',
            configuration_json={"key": "value3"}
        )))

    with managed_session() as session:
        queues = service.get_all_by_broker_id(session, 'broker_123')
        assert len(queues) == 2

    with managed_session() as session:
        deleted = service.delete_by_broker_id(session, 'broker_123')
        assert 2 == deleted

    with managed_session() as session:
        deleted = service.delete_by_broker_id(session, 'broker_789')
        assert 1 == deleted



