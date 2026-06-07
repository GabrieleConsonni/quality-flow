from abc import abstractmethod, ABC
from data_sources.models.database_connection_config_types import DatabaseConnectionConfigTypes


class SQLAlchemyEngineFactory(ABC):
    @abstractmethod
    def create_engine(self,connection_cfg: DatabaseConnectionConfigTypes):
        pass