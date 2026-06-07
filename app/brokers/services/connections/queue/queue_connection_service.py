from abc import ABC, abstractmethod
from typing import Any

from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes

LONG_VISIBILITY_TIMEOUT = 180

class QueueConnectionService(ABC):

    @abstractmethod
    def test_connection(self, broker_connection_config:BrokerConnectionConfigTypes,queue_id:str) -> tuple[Any, str]:
        pass

    @abstractmethod
    def publish_messages(
            self,
            broker_connection_config:BrokerConnectionConfigTypes,
            queue_id:str,
            messages: list[Any]) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def receive_messages(
            self,
            broker_connection_config:BrokerConnectionConfigTypes,
            queue_id:str,
            max_messages: int = 10,
    ) -> list[Any]:
        pass

    @abstractmethod
    def change_message_visibility(self,
                                  sqs,
                                  queue_url:str,
                                  messages: list[Any],
                                  visibility_timeout: int = LONG_VISIBILITY_TIMEOUT):
        pass

    @abstractmethod
    def ack_messages(
            self,
            broker_connection_config:BrokerConnectionConfigTypes,
            queue_id:str,
            messages: list[Any]
    ) -> list[dict]:
        pass

    @abstractmethod
    def get_queue_metrics(
            self,
            broker_connection_config:BrokerConnectionConfigTypes,
            queue_id: str,
    ) -> dict[str, Any]:
        pass

