from abc import ABC, abstractmethod

from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes
from brokers.models.dto.create_queue_dto import CreateQueueDto


class BrokerConnectionService(ABC):
    @abstractmethod
    def create_queue(self, broker_id:str, connection_config:BrokerConnectionConfigTypes, q: CreateQueueDto, tenant_id: str = None) -> dict[str, str]:
        pass

    @abstractmethod
    def delete_queue(self, connection_config:BrokerConnectionConfigTypes, queue_id: str)->dict[str, str]:
        pass
