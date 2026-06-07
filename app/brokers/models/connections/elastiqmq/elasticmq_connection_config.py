from brokers.models.connections.connection_config import ConnectionConfig

class ElasticmqConnectionConfig(ConnectionConfig):
    sourceType: str = "elasticmq"