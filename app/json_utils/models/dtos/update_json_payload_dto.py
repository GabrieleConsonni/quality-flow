from pydantic import BaseModel

class UpdateJsonPayloadDto(BaseModel):
    id:str|None = None
    description:str| None = None
    payload: dict | list[dict]
