from pydantic import BaseModel


class UpdateQueueDto(BaseModel):
    code: str
    description: str | None = None
