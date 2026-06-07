from pydantic import BaseModel

class ConnectionConfig(BaseModel):
    sourceType: str

