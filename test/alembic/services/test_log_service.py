from app._alembic.models.log_entity import LogEntity
from app._alembic.services.session_context_manager import managed_session

from app.logs.models.enums.log_level import LogLevel
from app.logs.models.enums.log_subject_type import LogSubjectType
from app.logs.services.alembic.log_service import LogService

def test_log_service(alembic_container):
    ids: list[str] = []
    baseline_count = _get_logs_count()

    ids.append(_verify_log(LogEntity(
        subject_type=LogSubjectType.SERVICE.value,
        subject="suite_id",
        level=LogLevel.INFO.value,
        message="Test log message 1",
        payload={"key": "value"}
    )))

    ids.extend(_verify_logs(
        [
            LogEntity(
                subject_type=LogSubjectType.SERVICE.value,
                subject="suite_id",
                level=LogLevel.INFO.value,
                message="Test log message 2",
                payload={"key": "value"}
            ),
            LogEntity(
                subject_type=LogSubjectType.SERVICE.value,
                subject="suite_id",
                level=LogLevel.INFO.value,
                message="Test log messagw 3",
                payload={"key": "value"}
            )
        ]
    ))

    _verify_get_logs(expected_count=baseline_count + 3)

    _verify_clean_logs(3)


def _verify_log(entity: LogEntity) -> str:
    with managed_session() as session:
        service = LogService()

        inserted_id = service.insert(session, entity)

        retrieved_entity = service.get_by_id(session, inserted_id)

        assert retrieved_entity is not None
        assert retrieved_entity.subject_type == LogSubjectType.SERVICE.value
        assert retrieved_entity.subject == "suite_id"
        assert retrieved_entity.level == LogLevel.INFO.value
        assert retrieved_entity.message == "Test log message 1"
        assert retrieved_entity.payload == {"key": "value"}

        return inserted_id


def _verify_logs(log_entities: list[LogEntity]) -> list[str]:
    with managed_session() as session:
        service = LogService()

        inserted_ids = service.logs(session, log_entities)

        assert len(inserted_ids) == len(log_entities)

        return inserted_ids


def _verify_get_logs(expected_count: int):
    with managed_session() as session:
        service = LogService()

        entities = service.get_logs(session)

        assert len(entities) == expected_count


def _verify_clean_logs(expected_deleted_count: int = 0):
    with managed_session() as session:
        service = LogService()
        deleted = service.clean_logs(session, 0)
        assert deleted >= expected_deleted_count


def _get_logs_count() -> int:
    with managed_session() as session:
        return len(LogService().get_logs(session))
