from pydantic import BaseModel, ConfigDict, Field


class DatabaseSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(..., min_length=1)
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    user: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
