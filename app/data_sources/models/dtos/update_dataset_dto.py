from pydantic import BaseModel


class UpdateDatasetDto(BaseModel):
    id: str | None = None
    description: str | None = None
    payload: dict
    perimeter: dict | None = None
