from fastapi import APIRouter, Depends

from _alembic.models.queue_entity import QueueEntity
from _alembic.services.session_context_manager import managed_session
from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes
from brokers.models.dto.configurations.queue_configuration_types import convert_queue_configuration_types
from brokers.models.dto.create_queue_dto import CreateQueueDto
from brokers.models.dto.find_all_messages_dto import FindAllMessagesDto
from brokers.models.dto.queue_messages_dto import QueueMessagesDto
from brokers.models.dto.update_queue_dto import UpdateQueueDto
from brokers.services.alembic.broker_connection_service import load_broker_connection
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.broker_connection_service_factory import BrokerConnectionServiceFactory
from brokers.services.connections.queue.queue_connection_service_factory import QueueConnectionServiceFactory
from brokers.services.elaborations.async_queue_service import AsyncQueueService
from exceptions.app_exception import QualityFlowAppException
router = APIRouter(prefix="/broker")


def _queue_stats(connection_config: BrokerConnectionConfigTypes, queue_id: str) -> dict:
    try:
        service = QueueConnectionServiceFactory.get_service(connection_config)
        return service.get_queue_metrics(connection_config, queue_id)
    except Exception:
        return {
            "messages_sent": None,
            "messages_received": None,
            "last_update": None,
        }


@router.get("/{broker_id}/queue")
async def find_all_queues_api(broker_id: str) -> list[dict]:
    with managed_session() as session:
        queues: list[QueueEntity] = QueueService().get_all_by_broker_id(session, broker_id)
        connection_config = load_broker_connection(broker_id)
        results: list[dict] = []
        for queue in queues:
            cfg = convert_queue_configuration_types(queue.configuration_json)
            stats = _queue_stats(connection_config, queue.id)
            results.append(
                {
                    "id": queue.id,
                    "code": queue.code,
                    "description": queue.description,
                    "configurationQueue": cfg.model_dump(),
                    "messages_sent": stats.get("messages_sent"),
                    "messages_received": stats.get("messages_received"),
                    "last_update": stats.get("last_update"),
                }
            )
        return results


@router.get("/{broker_id}/queue/{queue_id}")
async def find_queue_api(broker_id: str, queue_id: str):
    with managed_session() as session:
        queue_entity: QueueEntity | None = QueueService().get_by_id(session, queue_id)
        if queue_entity is None:
            raise QualityFlowAppException(f"Queue with name '{queue_id}' not found")
        cfg = convert_queue_configuration_types(queue_entity.configuration_json)
        return {
            "id": queue_entity.id,
            "code": queue_entity.code,
            "description": queue_entity.description,
            "configurationQueue": cfg.model_dump()
        }


@router.post("/{broker_id}/queue")
async def insert_queue_api(broker_id: str, c: CreateQueueDto):
    try:
        from config.user_context_config import get_current_user_ctx
        tenant_id = get_current_user_ctx().tenant_id
        connection_config: BrokerConnectionConfigTypes = load_broker_connection(broker_id)
        service = BrokerConnectionServiceFactory.get_service(connection_config)
        return service.create_queue(broker_id, connection_config, c, tenant_id=tenant_id)
    except Exception as e:
        raise QualityFlowAppException(str(e))


@router.delete("/{broker_id}/queue/{queue_id}")
async def delete_queue_api(broker_id: str, queue_id: str):
    try:
        connection_config: BrokerConnectionConfigTypes = load_broker_connection(broker_id)
        service = BrokerConnectionServiceFactory.get_service(connection_config)
        return service.delete_queue(connection_config, queue_id)
    except Exception as e:
        raise  QualityFlowAppException(f"Could not delete queue '{queue_id}': {str(e)}")


@router.put("/{broker_id}/queue/{queue_id}")
async def update_queue_api(broker_id: str, queue_id: str, d: UpdateQueueDto):
    with managed_session() as session:
        queue_entity: QueueEntity | None = QueueService().get_by_id(session, queue_id)
        if queue_entity is None:
            raise QualityFlowAppException(f"Queue with id '{queue_id}' not found")
        if str(queue_entity.broker_id) != str(broker_id):
            raise QualityFlowAppException(
                f"Queue '{queue_id}' does not belong to broker '{broker_id}'"
            )
        updated_queue: QueueEntity | None = QueueService().update(
            session,
            queue_id,
            code=d.code,
            description=d.description,
        )
        if updated_queue is None:
            raise QualityFlowAppException(f"Queue with id '{queue_id}' not found")
        return {
            "id": updated_queue.id,
            "code": updated_queue.code,
            "description": updated_queue.description,
        }


@router.post("/{broker_id}/queue/{queue_id}/messages")
async def publish_messages_api(broker_id: str, queue_id: str, p: QueueMessagesDto):
    connection_config: BrokerConnectionConfigTypes = load_broker_connection(broker_id)
    service = QueueConnectionServiceFactory.get_service(connection_config)
    return service.publish_messages(connection_config, queue_id=queue_id, messages=p.messages)


@router.get("/{broker_id}/queue/{queue_id}/test")
async def test_queue_connection_api(broker_id: str, queue_id: str):
    connection_config: BrokerConnectionConfigTypes = load_broker_connection(broker_id)
    if connection_config is None:
        raise QualityFlowAppException(f"Connection {broker_id} not found")
    service = QueueConnectionServiceFactory.get_service(connection_config)
    if not service.test_connection(connection_config, queue_id):
        return {"message": f"Connection is not valid"}
    return {"message": f"Connection is valid"}


@router.get("/{broker_id}/queue/{queue_id}/messages")
async def receive_messages_api(
    broker_id: str,
    queue_id: str,
    f: FindAllMessagesDto = Depends(),
):
    connection_config: BrokerConnectionConfigTypes = load_broker_connection(broker_id)
    service = QueueConnectionServiceFactory.get_service(connection_config)
    msgs = service.receive_messages(connection_config, queue_id=queue_id, max_messages=f.count)
    return msgs


@router.put("/{broker_id}/queue/{queue_id}/messages")
async def ack_messages_api(broker_id: str, 
                           queue_id: str, 
                           d: QueueMessagesDto):
    connection_config: BrokerConnectionConfigTypes = load_broker_connection(broker_id)
    service = QueueConnectionServiceFactory.get_service(connection_config)
    return service.ack_messages(connection_config, queue_id=queue_id, messages=d.messages)

@router.get("/{broker_id}/queue/{queue_id}/start-messages")
async def start_receive_messages_api(broker_id: str, queue_id: str):
    return AsyncQueueService.start_receiving_messages(broker_id, queue_id)


@router.get("/{broker_id}/queue/{queue_id}/stop-messages")
async def stop_receive_messages_api(broker_id: str, queue_id: str):
    return AsyncQueueService.stop_receiving_messages(queue_id)

@router.get("/{broker_id}/queue/{queue_id}/publish-from-table/{export_table_name}")
async def publish_messages_from_table_api(broker_id: str, queue_id: str, export_table_name: str):
    return AsyncQueueService.publish_from_table(broker_id, queue_id, export_table_name)


