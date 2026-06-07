from pydantic import BaseModel

class FindAllMessagesDto(BaseModel):
    count: int