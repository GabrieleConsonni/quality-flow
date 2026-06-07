from brokers.models.connections.elastiqmq.elasticmq_connection_config import ElasticmqConnectionConfig


class SQSElasticmqConnectionConfig(ElasticmqConnectionConfig):
    queueUrl:str
