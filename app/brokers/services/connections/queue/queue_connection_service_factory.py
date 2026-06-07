from brokers.models.connections.amazon.broker_amazon_connection_config import BrokerAmazonConnectionConfig
from brokers.models.connections.amazon.sqs_amazon_connection_config import SQSAmazonConnectionConfig
from brokers.models.connections.connection_config import ConnectionConfig
from brokers.models.connections.elastiqmq.broker_elasticmq_connection_config import BrokerElasticmqConnectionConfig
from brokers.models.connections.elastiqmq.sqs_elasticmq_connection_config import SQSElasticmqConnectionConfig
from brokers.services.connections.queue.amazon_sqs_connection_service import AmazonSQSConnectionService
from brokers.services.connections.queue.elasticmq_sqs_connection_service import ElasticmqSQSConnectionService
from brokers.services.connections.queue.queue_connection_service import QueueConnectionService


class QueueConnectionServiceFactory:

    _CONNECTOR_MAPPING: dict[type[ConnectionConfig], type[QueueConnectionService]] = {
        SQSAmazonConnectionConfig: AmazonSQSConnectionService,
        BrokerAmazonConnectionConfig:AmazonSQSConnectionService,
        BrokerElasticmqConnectionConfig: ElasticmqSQSConnectionService,
        SQSElasticmqConnectionConfig:ElasticmqSQSConnectionService
    }

    @classmethod
    def get_service(cls, config: ConnectionConfig) -> QueueConnectionService:

        config_type = type(config)
        service_class = cls._CONNECTOR_MAPPING.get(config_type)

        if service_class is None:
            supported_types = list(cls._CONNECTOR_MAPPING.keys())
            raise ValueError(
                f"Unsupported connector type: {config_type}. "
                f"Supported types: {supported_types}"
            )

        return service_class()
