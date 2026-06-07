import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine

from app._alembic.models.queue_entity import QueueEntity
from app._alembic.services.alembic_config_service import url_from_env
from app._alembic.services.session_context_manager import managed_session
from app.brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes
from app.brokers.models.connections.connection_config import ConnectionConfig
from app.brokers.services.alembic.queue_service import QueueService
from app.brokers.services.connections.queue.queue_connection_service import QueueConnectionService, LONG_VISIBILITY_TIMEOUT
from app.brokers.services.elaborations.queue_reader_thread import QueueReaderThread
from app.brokers.services.elaborations.queue_writer_thread import QueueWriterThread
from app.logs.services.alembic.log_service import LogService
from app.sqlalchemy_utils.database_table_reader import DatabaseTableReader, ReadTableConfig


SHORT_TIMEOUT = 20

class QueueReaderConnectionServiceMock(QueueConnectionService):

    msgs: list[dict] = []

    def addMessages(self, messages):
        for msg in messages:
            self.msgs.append(msg)

    def publish_messages(self, broker_connection_config: BrokerConnectionConfigTypes, queue_id: str,
                         messages: list[Any]) -> list[dict[str, Any]]:
        raise NotImplementedError()

    def ack_messages(self, broker_connection_config: BrokerConnectionConfigTypes, queue_id: str, messages: list[Any]) -> list[dict]:
        raise NotImplementedError()

    def test_connection(self, broker_connection_config: BrokerConnectionConfigTypes, queue_id: str) -> tuple[Any, str]:
        return None, "mock_queue_url"

    def receive_messages(self, broker_connection_config: BrokerConnectionConfigTypes, queue_id: str,
                         max_messages: int = 10) -> list[Any]:
        results = []
        for m in self.msgs:
            if time.time() - m['time'] >= SHORT_TIMEOUT:
                m['time'] = time.time()+SHORT_TIMEOUT
                results.append(m)
                if len(results) >= max_messages:
                    return results
        return results


    def change_message_visibility(self, sqs, queue_url: str, messages: list[Any],
                                  visibility_timeout: int = LONG_VISIBILITY_TIMEOUT):
        for msg in messages:
            for m in self.msgs:
                if m['ReceiptHandle'] == msg['ReceiptHandle']:
                    m['time']=time.time()+LONG_VISIBILITY_TIMEOUT

    def get_queue_metrics(self, broker_connection_config: BrokerConnectionConfigTypes, queue_id: str) -> dict[str, Any]:
        return {
            "messages_sent": None,
            "messages_received": None,
            "last_update": None,
        }

class QueueWriterConnectionServiceMock(QueueConnectionService):

    msgs: list[dict] = []

    def publish_messages(self, broker_connection_config: BrokerConnectionConfigTypes, queue_id: str,
                         messages: list[Any]) -> list[dict[str, Any]]:
        self.msgs.extend(messages)
        print(f"Published {len(messages)} messages to queue {queue_id}")
        return [{"MessageId": str(i+1)} for i in range(len(messages))]

    def ack_messages(self, broker_connection_config: BrokerConnectionConfigTypes, queue_id: str, messages: list[Any]) -> list[dict]:
        raise NotImplementedError()

    def test_connection(self, broker_connection_config: BrokerConnectionConfigTypes, queue_id: str) -> tuple[Any, str]:
        raise NotImplementedError()

    def receive_messages(self, broker_connection_config: BrokerConnectionConfigTypes, queue_id: str,
                         max_messages: int = 10) -> list[Any]:
        return self.msgs


    def change_message_visibility(self, sqs, queue_url: str, messages: list[Any],
                                  visibility_timeout: int = LONG_VISIBILITY_TIMEOUT):
        raise NotImplementedError()

    def get_queue_metrics(self, broker_connection_config: BrokerConnectionConfigTypes, queue_id: str) -> dict[str, Any]:
        return {
            "messages_sent": None,
            "messages_received": None,
            "last_update": None,
        }


def test_queue_service(alembic_container):

    service = QueueService()

    with managed_session() as session:
        entity= QueueEntity()
        entity.code='sales',
        entity.broker_id='avon',
        entity.configuration_json={
                "sourceType": "amazon-sqs",
                "url":"https://sqs.us-east-1.amazonaws.com/123456789012/sales"
        }
        queue_id = service.insert(session, entity)

    mock_service = QueueReaderConnectionServiceMock()

    thread = QueueReaderThread(queue_id, mock_service, ConnectionConfig(sourceType="amazon-sqs"))

    thread.start()

    mock_messages = [
        {"MessageId": "1", "Body": {"order_id": "1001", "amount": 250}, "ReceiptHandle": "rh1"},
        {"MessageId": "2", "Body": {"order_id": "1002", "amount": 180}, "ReceiptHandle": "rh2"},
        {"MessageId": "3", "Body": {"order_id": "1003", "amount": 320}, "ReceiptHandle": "rh3"},
        {"MessageId": "4", "Body": {"order_id": "1004", "amount": 90}, "ReceiptHandle": "rh4"},
        {"MessageId": "5", "Body": {"order_id": "1005", "amount": 540}, "ReceiptHandle": "rh5"},
        {"MessageId": "6", "Body": {"order_id": "1006", "amount": 120}, "ReceiptHandle": "rh6"},
        {"MessageId": "7", "Body": {"order_id": "1007", "amount": 760}, "ReceiptHandle": "rh7"},
        {"MessageId": "8", "Body": {"order_id": "1008", "amount": 200}, "ReceiptHandle": "rh8"},
        {"MessageId": "9", "Body": {"order_id": "1009", "amount": 640}, "ReceiptHandle": "rh9"},
        {"MessageId": "10", "Body": {"order_id": "1010", "amount": 150}, "ReceiptHandle": "rh10"},
        {"MessageId": "11", "Body": {"order_id": "1011", "amount": 330}, "ReceiptHandle": "rh11"},
        {"MessageId": "12", "Body": {"order_id": "1012", "amount": 410}, "ReceiptHandle": "rh12"},
        {"MessageId": "13", "Body": {"order_id": "1013", "amount": 95}, "ReceiptHandle": "rh13"},
        {"MessageId": "14", "Body": {"order_id": "1014", "amount": 285}, "ReceiptHandle": "rh14"},
        {"MessageId": "15", "Body": {"order_id": "1015", "amount": 720}, "ReceiptHandle": "rh15"},
        {"MessageId": "16", "Body": {"order_id": "1016", "amount": 50}, "ReceiptHandle": "rh16"},
        {"MessageId": "17", "Body": {"order_id": "1017", "amount": 870}, "ReceiptHandle": "rh17"},
        {"MessageId": "18", "Body": {"order_id": "1018", "amount": 140}, "ReceiptHandle": "rh18"},
        {"MessageId": "19", "Body": {"order_id": "1019", "amount": 260}, "ReceiptHandle": "rh19"},
        {"MessageId": "20", "Body": {"order_id": "1020", "amount": 310}, "ReceiptHandle": "rh20"},
        {"MessageId": "21", "Body": {"order_id": "1021", "amount": 480}, "ReceiptHandle": "rh21"},
        {"MessageId": "22", "Body": {"order_id": "1022", "amount": 175}, "ReceiptHandle": "rh22"},
        {"MessageId": "23", "Body": {"order_id": "1023", "amount": 620}, "ReceiptHandle": "rh23"},
        {"MessageId": "24", "Body": {"order_id": "1024", "amount": 215}, "ReceiptHandle": "rh24"},
        {"MessageId": "25", "Body": {"order_id": "1025", "amount": 555}, "ReceiptHandle": "rh25"},
        {"MessageId": "26", "Body": {"order_id": "1026", "amount": 305}, "ReceiptHandle": "rh26"},
        {"MessageId": "27", "Body": {"order_id": "1027", "amount": 440}, "ReceiptHandle": "rh27"},
        {"MessageId": "28", "Body": {"order_id": "1028", "amount": 85}, "ReceiptHandle": "rh28"},
        {"MessageId": "29", "Body": {"order_id": "1029", "amount": 700}, "ReceiptHandle": "rh29"},
        {"MessageId": "30", "Body": {"order_id": "1030", "amount": 195}, "ReceiptHandle": "rh30"},
    ]

    for msg in mock_messages:
        msg['time'] = time.time()

    mock_service.addMessages(mock_messages)

    thread.join(timeout=60)

    with managed_session() as session:
        logs = LogService().get_logs(session)
        for log in logs:
            print(f"Log: {log.message}")

    engine = create_engine(url_from_env())
    rows = DatabaseTableReader.read_full_table(engine, ReadTableConfig("sales_export", order_by=["id"]))

    assert len(rows) == 30
    for i, row in enumerate(rows):
        print(f"Row {i+1}: {row}")

    queue_writer_connection_service_mock = QueueWriterConnectionServiceMock()
    writer_thread = QueueWriterThread("sales_export", queue_id, queue_writer_connection_service_mock, ConnectionConfig(sourceType="amazon-sqs"))
        
    writer_thread.start()
    writer_thread.join(timeout=30)
    assert len(queue_writer_connection_service_mock.msgs) == 30






