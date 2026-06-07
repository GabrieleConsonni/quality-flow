from pydantic import BaseModel

class CreateJsonPayloadDto(BaseModel):
    description:str| None = None
    payload: dict | list[dict]
