from pydantic import BaseModel


class JsonPayloadDto(BaseModel):
    description: str | None = None
    payload: dict | list[dict]
