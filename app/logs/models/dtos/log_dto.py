from pydantic import BaseModel

from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType

class LogDto(BaseModel):
    id: str | None = None
    subject_type: LogSubjectType = LogSubjectType.SERVICE
    subject:str
    level: LogLevel = LogLevel.INFO
    message: str
    payload: dict | list[dict] | None = None
    created_at: str | None = None