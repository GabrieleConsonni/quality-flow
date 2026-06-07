import time
from datetime import timedelta, datetime

from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.log_entity import LogEntity
from _alembic.services.base_id_service import BaseIdEntityService
from _alembic.services.session_context_manager import managed_session
from logs.models.dtos.log_dto import LogDto
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType


class LogService(BaseIdEntityService):
    def log(self, log_dto:LogDto, tenant_id: str = None)->str:
        with managed_session(tenant_id) as session:
            log_entity = LogEntity()
            log_entity.subject_type = log_dto.subject_type
            log_entity.subject = log_dto.subject
            log_entity.message = log_dto.message
            log_entity.level = log_dto.level
            log_entity.payload = log_dto.payload
            return self.insert(session, log_entity)

    def get_entity_class(self) -> type[BaseIdEntity]:
        return LogEntity

    def logs(self, session: Session, entities: list[LogEntity])->list[str]:
        return super().inserts(session, entities)

    def get_logs(self, session: Session, subject:LogSubjectType=None, level:LogLevel=None, limit:int=100)->list[LogEntity]:
        query = session.query(LogEntity)
        if subject:
            subject_attr: InstrumentedAttribute = LogEntity.subject_type
            query = query.filter(subject_attr == subject.value)
        if level:
            level_attr: InstrumentedAttribute = LogEntity.level
            query = query.filter(level_attr == level.value)
        query = query.order_by(LogEntity.created_at.desc()).limit(limit)
        return query.all()


    def clean_logs(self,session: Session, older_than_days:int=30)->int:
        threshold_dt = datetime.utcnow() - timedelta(days=int(older_than_days))
        created_at_attr: InstrumentedAttribute = LogEntity.created_at
        deleted = session.query(LogEntity).filter(created_at_attr < threshold_dt).delete()
        return deleted