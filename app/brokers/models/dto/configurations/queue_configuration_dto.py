from pydantic import BaseModel

class QueueConfigurationDto(BaseModel):
    sourceType: str
    url: str | None = None
    defaultVisibilityTimeout: int = 30
    receiveMessageWait: int = 0