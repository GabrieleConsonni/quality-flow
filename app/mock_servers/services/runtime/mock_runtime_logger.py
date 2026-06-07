from logs.models.dtos.log_dto import LogDto
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType
from logs.services.alembic.log_service import LogService


def log_mock_server_event(
    subject: str,
    message: str,
    *,
    level: LogLevel = LogLevel.INFO,
    payload: dict | list[dict] | None = None,
):
    LogService().log(
        LogDto(
            subject_type=LogSubjectType.MOCK_SERVER,
            subject=subject,
            message=message,
            level=level,
            payload=payload,
        )
    )
