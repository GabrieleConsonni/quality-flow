from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.services.session_context_manager import managed_session
from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes, \
    convert_to_broker_connection_config
from brokers.models.dto.configurations.queue_configuration_types import convert_queue_configuration_types
from brokers.models.dto.create_queue_dto import CreateQueueDto
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.broker_connection_service_factory import BrokerConnectionServiceFactory
from json_utils.models.enums.json_type import JsonType
from json_utils.services.alembic.json_files_service import JsonFilesService
from services.multitenant.multitenant_service import get_tenants


def init_elasticmq():
    for tenant in get_tenants():
        _init_elasticmq_for_tenant(tenant.tenant_id)


def _init_elasticmq_for_tenant(tenant_id: str):
    with managed_session(tenant_id) as session:
        brokers: list[JsonPayloadEntity] = JsonFilesService().get_all_by_type(session, JsonType.BROKER_CONNECTION)
        for b in brokers:
            try:
                brokers_connection: BrokerConnectionConfigTypes = convert_to_broker_connection_config(b.payload)
                if brokers_connection.sourceType != "elasticmq":
                    continue
                service = BrokerConnectionServiceFactory.get_service(brokers_connection)
                queues = QueueService().get_all_by_broker_id(session, b.id)
                for queue_entity in queues:
                    cfg_dto = convert_queue_configuration_types(queue_entity.configuration_json)
                    result = service.create_queue(b.id, brokers_connection, CreateQueueDto(
                        code=queue_entity.code,
                        description=queue_entity.description,
                        queueConfiguration=cfg_dto,
                        save_on_db=False
                    ), tenant_id=tenant_id)
                    queue_url = result.get("queue_url")
                    if queue_url:
                        cfg_dto.url = queue_url
                        queue_entity.configuration_json = cfg_dto.model_dump()
            except Exception as e:
                print(f"Error initializing ElasticMQ for broker {b.id} (tenant {tenant_id}): {e}")

