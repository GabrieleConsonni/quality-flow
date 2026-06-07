import boto3
from botocore.client import BaseClient

from _alembic.models.queue_entity import QueueEntity
from _alembic.services.session_context_manager import managed_session
from brokers.models.connections.amazon.broker_amazon_connection_config import BrokerAmazonConnectionConfig
from brokers.models.dto.configurations.amazon_queue_configuration_dto import AmazonQueueConfigurationDto
from brokers.models.dto.configurations.queue_configuration_types import QueueConfigurationTypes, \
    convert_queue_configuration_types
from brokers.models.dto.create_queue_dto import CreateQueueDto
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.broker_connection_service import BrokerConnectionService
from brokers.services.connections.queue.amazon_sqs_connection_service import AmazonSQSConnectionService


class AmazonBrokerConnectionService(BrokerConnectionService):
    def _client(self, config: BrokerAmazonConnectionConfig)->BaseClient:
        return boto3.client(
            "sqs",
            region_name=config.region,
            endpoint_url=config.endpointUrl,
            aws_access_key_id=config.accessKeyId,
            aws_secret_access_key=config.secretsAccessKey,
        )

    def create_queue(self, broker_id:str, config:BrokerAmazonConnectionConfig, c: CreateQueueDto, tenant_id: str = None):
        cfg:AmazonQueueConfigurationDto = c.queueConfiguration
        queue_url = f"{config.endpointUrl}/{c.code}"
        cfg.url = queue_url
        AmazonSQSConnectionService().test_url_connection(config, queue_url)
        with managed_session() as session:
            entity = QueueEntity()
            entity.broker_id = broker_id
            entity.code = c.code
            entity.description = c.description
            entity.configuration_json = cfg.model_dump()
            _id = QueueService().insert(session, entity)

    def delete_queue(self, config:BrokerAmazonConnectionConfig,queue_id: str):
        with managed_session() as session:
            queue = QueueService().get_by_id(session, queue_id)
            cfg: QueueConfigurationTypes = convert_queue_configuration_types(queue.configuration_json)
            QueueService().delete_by_id(session, queue_id)
            return {"message": f"Queue {cfg.queue_url} deleted successfully"}

