from brokers.models.connections.amazon.amazon_connection_config import AmazonConnectionConfig

class SQSAmazonConnectionConfig(AmazonConnectionConfig):
    queueUrl:str
