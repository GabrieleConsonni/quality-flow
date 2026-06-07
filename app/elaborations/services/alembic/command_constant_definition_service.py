from sqlalchemy.orm import InstrumentedAttribute, Session

from _alembic.models.base_entity import BaseIdEntity
from _alembic.models.command_constant_definition_entity import (
    CommandConstantDefinitionEntity,
)
from _alembic.services.base_id_service import BaseIdEntityService


class CommandConstantDefinitionService(BaseIdEntityService):
    def get_entity_class(self) -> type[BaseIdEntity]:
        return CommandConstantDefinitionEntity

    def get_all_by_suite_id(
        self,
        session: Session,
        suite_id: str,
    ) -> list[CommandConstantDefinitionEntity]:
        suite_id_attr: InstrumentedAttribute = CommandConstantDefinitionEntity.suite_id
        return (
            session.query(CommandConstantDefinitionEntity)
            .filter(suite_id_attr == suite_id)
            .order_by(
                CommandConstantDefinitionEntity.section_type,
                CommandConstantDefinitionEntity.command_order,
                CommandConstantDefinitionEntity.id,
            )
            .all()
        )

    def delete_by_suite_id(self, session: Session, suite_id: str) -> int:
        suite_id_attr: InstrumentedAttribute = CommandConstantDefinitionEntity.suite_id
        query = session.query(CommandConstantDefinitionEntity).filter(suite_id_attr == suite_id)
        count = 0
        for entity in query.all():
            session.delete(entity)
            count += 1
        session.flush()
        return count

    def delete_by_mock_server_api_id(self, session: Session, mock_server_api_id: str) -> int:
        owner_attr: InstrumentedAttribute = CommandConstantDefinitionEntity.mock_server_api_id
        query = session.query(CommandConstantDefinitionEntity).filter(owner_attr == mock_server_api_id)
        count = 0
        for entity in query.all():
            session.delete(entity)
            count += 1
        session.flush()
        return count

    def delete_by_mock_server_queue_id(self, session: Session, mock_server_queue_id: str) -> int:
        owner_attr: InstrumentedAttribute = CommandConstantDefinitionEntity.mock_server_queue_id
        query = session.query(CommandConstantDefinitionEntity).filter(owner_attr == mock_server_queue_id)
        count = 0
        for entity in query.all():
            session.delete(entity)
            count += 1
        session.flush()
        return count
