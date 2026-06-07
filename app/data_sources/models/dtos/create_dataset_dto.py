from pydantic import BaseModel


class CreateDatasetDto(BaseModel):
    description: str | None = None
    payload: dict
    perimeter: dict | None = None
