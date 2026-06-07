import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from _alembic.models.queue_entity import QueueEntity
from _alembic.services.session_context_manager import managed_session
from brokers.models.connections.elastiqmq.broker_elasticmq_connection_config import BrokerElasticmqConnectionConfig
from brokers.models.dto.configurations.elasticmq_queue_configuration_dto import ElasticmqQueueConfigurationDto
from brokers.models.dto.configurations.queue_configuration_types import convert_queue_configuration_types, \
    QueueConfigurationTypes
from brokers.models.dto.create_queue_dto import CreateQueueDto
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.amazon_broker_connection_service import AmazonBrokerConnectionService

DEFAULT_VISIBILITY_TIMEOUT = 30


class ElasticmqBrokerConnectionService(AmazonBrokerConnectionService):
    def _client(self, config: BrokerElasticmqConnectionConfig) -> BaseClient:
        return boto3.client(
            "sqs",
            region_name="region",
            endpoint_url=config.endpointUrl,
            aws_access_key_id="xxx",
            aws_secret_access_key="yyy",
        )

    def create_queue(self, broker_id: str, config: BrokerElasticmqConnectionConfig, c: CreateQueueDto, tenant_id: str = None) -> dict[
        str, str]:
        sqs: BaseClient = self._client(config)

        cfg: ElasticmqQueueConfigurationDto = c.queueConfiguration

        attributes = self.create_attributes(cfg)

        queue_code = c.code
        if cfg.fifoQueue and not queue_code.endswith(".fifo"):
            queue_code += ".fifo"

        sqs_queue_name = f"{tenant_id}-{queue_code}" if tenant_id else queue_code

        try:
            resp = sqs.create_queue(
                QueueName=sqs_queue_name,
                Attributes=attributes
            )
            queue_url = resp.get("QueueUrl")
            cfg.url=queue_url

        except ClientError as e:
            raise Exception(f"Error creating SQS queue: {e}")

        if c.save_on_db:
            with managed_session() as session:
                entity = QueueEntity()
                entity.broker_id = broker_id
                entity.code = queue_code
                entity.description = c.description
                entity.configuration_json = cfg.model_dump()
                _id = QueueService().insert(session, entity)

                return {
                    "id": _id,
                    "queue_url": queue_url
                }

        return {
            "id": "",
            "queue_url": queue_url
        }


    def create_attributes(self, cfg: ElasticmqQueueConfigurationDto):

        attributes = {
            "VisibilityTimeout": str(cfg.defaultVisibilityTimeout or DEFAULT_VISIBILITY_TIMEOUT),
            "DelaySeconds": str(cfg.delay or 0),
            "ReceiveMessageWaitTimeSeconds": str(cfg.receiveMessageWait or 0),
        }

        if cfg.fifoQueue:
            attributes["FifoQueue"] = "true"
            if cfg.contentBasedDeduplication:
                attributes["ContentBasedDeduplication"] = "true"

        return attributes

    def delete_queue(self, config:BrokerElasticmqConnectionConfig,queue_id: str)->dict[str, str]:
        sqs: BaseClient = self._client(config)
        try:
            with managed_session() as session:
                queue = QueueService().get_by_id(session,queue_id)
                cfg: QueueConfigurationTypes = convert_queue_configuration_types(queue.configuration_json)# to raise exception if not found
                sqs.delete_queue(QueueUrl=cfg.url)
                QueueService().delete_by_id(session, queue_id)
                return {"message": f"Queue {cfg.url} deleted successfully"}
        except ClientError as e:
            raise Exception(f"Error deleting SQS queue: {e}")
