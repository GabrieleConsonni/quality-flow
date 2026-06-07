from brokers.models.dto.configurations.queue_configuration_dto import QueueConfigurationDto


class AmazonQueueConfigurationDto(QueueConfigurationDto):
    sourceType:str = "amazon-sqs"