from brokers.models.connections.connection_config import ConnectionConfig

class AmazonConnectionConfig(ConnectionConfig):
    sourceType: str = "amazon-sqs"
    region:str
    secretsAccessKey:str
    accessKeyId:str