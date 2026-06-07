from pydantic import BaseModel

from brokers.models.dto.configurations.queue_configuration_types import QueueConfigurationTypes


class CreateQueueDto(BaseModel):
    code: str
    description: str | None = None
    queueConfiguration: QueueConfigurationTypes
    save_on_db:bool=True
