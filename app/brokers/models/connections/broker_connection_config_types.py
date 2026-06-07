from brokers.models.connections.amazon.broker_amazon_connection_config import BrokerAmazonConnectionConfig
from brokers.models.connections.elastiqmq.broker_elasticmq_connection_config import BrokerElasticmqConnectionConfig

BrokerConnectionConfigTypes = BrokerAmazonConnectionConfig | BrokerElasticmqConnectionConfig

def convert_to_broker_connection_config(data: dict) -> BrokerConnectionConfigTypes:
    source_type = data.get("sourceType")
    if source_type == "amazon-sqs":
        return BrokerAmazonConnectionConfig(**data)
    elif source_type == "elasticmq":
        return BrokerElasticmqConnectionConfig(**data)
    else:
        raise ValueError(f"Unsupported sourceType: {source_type}")