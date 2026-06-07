from brokers.models.dto.configurations.queue_configuration_dto import QueueConfigurationDto


class ElasticmqQueueConfigurationDto(QueueConfigurationDto):
    sourceType:str = "elasticmq"
    fifoQueue: bool = False
    contentBasedDeduplication: bool = False
    delay: int = 0