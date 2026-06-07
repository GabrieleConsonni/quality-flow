from brokers.models.dto.configurations.amazon_queue_configuration_dto import AmazonQueueConfigurationDto
from brokers.models.dto.configurations.elasticmq_queue_configuration_dto import ElasticmqQueueConfigurationDto

QueueConfigurationTypes = AmazonQueueConfigurationDto | ElasticmqQueueConfigurationDto

def convert_queue_configuration_types(data: dict) -> QueueConfigurationTypes:
    source_type = data.get("sourceType")
    if source_type == "amazon-sqs":
        return AmazonQueueConfigurationDto(**data)
    elif source_type == "elasticmq":
        return ElasticmqQueueConfigurationDto(**data)
    else:
        raise ValueError(f"Unsupported sourceType: {source_type}")