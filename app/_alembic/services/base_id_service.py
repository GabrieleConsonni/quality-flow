from abc import abstractmethod
from typing import Optional

from sqlalchemy.orm import Session, InstrumentedAttribute

from _alembic.models.base_id_entity_types import BaseIdEntityTypes
from _alembic.services.update_entity import update_entity


class BaseIdEntityService:

    @abstractmethod
    def get_entity_class(self) -> BaseIdEntityTypes:
        pass

    def insert(self, session: Session, entity: BaseIdEntityTypes) -> str:
        session.add(entity)
        session.flush()
        session.refresh(entity)
        return entity.id

    def inserts(self, session: Session, entities: list[BaseIdEntityTypes]) -> list[str]:
        for entity in entities:
            session.add(entity)
        session.flush()
        for entity in entities:
            session.refresh(entity)
        return [entity.id for entity in entities]

    def update(self, session: Session, _id: str, **kwargs) -> BaseIdEntityTypes | None:
        id_attr: InstrumentedAttribute = self.get_entity_class().id
        db_entity: Optional[BaseIdEntityTypes] = (
            session.query(self.get_entity_class()).filter(id_attr == _id).one_or_none()
        )
        if not db_entity:
            return None
        update_entity(db_entity, **kwargs)
        session.flush()
        return db_entity


    def get_by_id(self, session: Session, _id: str) -> BaseIdEntityTypes | None:
        id_attr: InstrumentedAttribute = self.get_entity_class().id
        db_entity: Optional[BaseIdEntityTypes] = (
            session.query(self.get_entity_class()).filter(id_attr == _id).one_or_none()
        )
        return db_entity

    def get_all(self,session:Session)->list[BaseIdEntityTypes]:
        return session.query(self.get_entity_class()).all()

    def delete_by_id(self, session: Session, _id: str) -> int:
        entity = session.get(self.get_entity_class(), _id)
        if not entity:
            return 0
        self.delete_on_cascade(session, _id)
        session.delete(entity)
        session.flush()
        return 1

    def delete_on_cascade(self,session: Session,_id:str):
        pass