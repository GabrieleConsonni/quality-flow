from sqlalchemy.orm import Session

from _alembic.models.dataset_entity import DatasetEntity
from _alembic.services.base_id_service import BaseIdEntityService


class DatasetService(BaseIdEntityService):
    def get_entity_class(self) -> type[DatasetEntity]:
        return DatasetEntity

    def get_all_datasets(self, session: Session) -> list[DatasetEntity]:
        return session.query(DatasetEntity).all()
