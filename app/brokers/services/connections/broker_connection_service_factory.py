from brokers.models.connections.amazon.broker_amazon_connection_config import BrokerAmazonConnectionConfig
from brokers.models.connections.connection_config import ConnectionConfig
from brokers.models.connections.elastiqmq.broker_elasticmq_connection_config import BrokerElasticmqConnectionConfig
from brokers.services.connections.amazon_broker_connection_service import AmazonBrokerConnectionService
from brokers.services.connections.broker_connection_service import BrokerConnectionService
from brokers.services.connections.elasticmq_broker_connection_service import ElasticmqBrokerConnectionService


class BrokerConnectionServiceFactory:

    _CONNECTOR_MAPPING: dict[type[ConnectionConfig], type[BrokerConnectionService]] = {
        BrokerAmazonConnectionConfig:AmazonBrokerConnectionService,
        BrokerElasticmqConnectionConfig: ElasticmqBrokerConnectionService
    }

    @classmethod
    def get_service(cls, config: ConnectionConfig) -> BrokerConnectionService:

        config_type = type(config)
        service_class = cls._CONNECTOR_MAPPING.get(config_type)

        if service_class is None:
            supported_types = list(cls._CONNECTOR_MAPPING.keys())
            raise ValueError(
                f"Unsupported connector type: {config_type}. "
                f"Supported types: {supported_types}"
            )

        return service_class()
